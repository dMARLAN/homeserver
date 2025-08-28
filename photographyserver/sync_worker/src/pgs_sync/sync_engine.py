"""Sync operation logic for processing file events and maintaining database consistency."""

import dataclasses
import logging
from pathlib import Path
from typing import Callable, Final

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore[import-untyped]

from pgs_db.models.photos import PLPhoto
from pgs_sync.config import sync_config
from pgs_sync.sync_types import FileEvent, FileEventType, SyncStats
from pgs_sync.utils import extract_image_metadata, generate_title_from_filename, is_supported_image_file

logger = logging.getLogger(__name__)


class SyncEngine:
    """Handles sync operations between file system and database."""

    __FILE_EVENT_TO_HANDLER_MAP: Final[dict[FileEventType, str]] = {
        FileEventType.CREATED: "_handle_file_created",
        FileEventType.MODIFIED: "_handle_file_modified",
        FileEventType.DELETED: "_handle_file_deleted",
        FileEventType.MOVED: "_handle_file_moved",
    }

    def __init__(self, db_session_factory: Callable[[], AsyncSession]) -> None:
        self.db_session_factory = db_session_factory
        self.config = sync_config

    async def process_file_event(self, file_event: FileEvent) -> None:
        """Process a single file event and update the database accordingly.

        Args:
            file_event: The file system event to process
        """
        logger.debug(f"Processing file event: {file_event.event_type.value} - {file_event.file_path}")

        if not self._is_supported_file(file_event.file_path):
            logger.debug(f"Skipping unsupported file: {file_event.file_path}")
            return

        async with self.db_session_factory() as session:
            try:
                handler_method = getattr(self, self.__FILE_EVENT_TO_HANDLER_MAP[file_event.event_type])
                await handler_method(session, file_event)

                await session.commit()
                logger.debug(f"Successfully processed {file_event.event_type.value} event for {file_event.file_path}")

            except Exception as e:
                logger.error(
                    f"Error processing file event {file_event.event_type.value} for {file_event.file_path}: {e}"
                )
                await session.rollback()
                raise

    async def process_event_batch(self, file_events: list[FileEvent]) -> None:
        """Process a batch of file events efficiently.

        Args:
            file_events: List of file events to process
        """
        logger.info(f"Processing batch of {len(file_events)} events")

        supported_file_events = [event for event in file_events if self._is_supported_file(event.file_path)]

        if not supported_file_events:
            logger.debug("No supported files in event batch")
            return

        async with self.db_session_factory() as session:
            try:
                for event in supported_file_events:
                    try:
                        handler_method = getattr(self, self.__FILE_EVENT_TO_HANDLER_MAP[event.event_type])
                        await handler_method(session, event)
                    except Exception as e:
                        logger.error(f"Error processing event {event.event_type.value} for {event.file_path}: {e}")

                await session.commit()
                logger.info(f"Successfully processed batch of {len(supported_file_events)} events")

            except Exception as e:
                logger.error(f"Error processing event batch: {e}")
                await session.rollback()
                raise

    async def perform_initial_sync(self) -> SyncStats:
        """Perform initial full sync of the photos' directory.

        Returns:
            Statistics from the sync operation
        """
        logger.info("Starting initial sync of photos directory")
        return await self._perform_full_sync()

    async def perform_periodic_sync(self) -> SyncStats:
        """Perform periodic full sync as fallback.

        Returns:
            Statistics from the sync operation
        """
        logger.info("Starting periodic sync")
        return await self._perform_full_sync()

    async def _perform_full_sync(self) -> SyncStats:
        """Perform a full directory scan and sync with a database.

        This is adapted from the original sync_filesystem_to_db function.

        Returns:
            Statistics from the sync operation
        """
        storage_path = self.config.photos_base_path

        if not storage_path.exists():
            raise FileNotFoundError(f"Storage directory not found: {storage_path}")

        if not storage_path.is_dir():
            raise ValueError(f"Storage path is not a directory: {storage_path}")

        logger.info(f"Starting filesystem sync for {storage_path}")

        stats = SyncStats(files_scanned=0, files_added=0, files_updated=0, files_removed=0, errors=0)

        async with self.db_session_factory() as session:
            try:
                existing_photos = await self._get_existing_photos_by_path(session)
                found_file_paths = set()

                for category_dir in storage_path.iterdir():
                    if not category_dir.is_dir():
                        continue

                    category_name = category_dir.name
                    logger.debug(f"Scanning category: {category_name}")

                    # Scan all image files in the category directory
                    for image_file in category_dir.iterdir():
                        if not image_file.is_file() or not self._is_supported_file(image_file):
                            continue

                        file_path_str = str(image_file.resolve())
                        found_file_paths.add(file_path_str)

                        stats = dataclasses.replace(stats, files_scanned=stats.files_scanned + 1)

                        try:
                            existing_photo = existing_photos.get(file_path_str)

                            metadata = extract_image_metadata(image_file)

                            if existing_photo is None:
                                title = generate_title_from_filename(image_file.name)

                                new_photo = PLPhoto(
                                    filename=image_file.name,
                                    file_path=file_path_str,
                                    category=category_name,
                                    title=title,
                                    file_size=metadata.file_size,
                                    width=metadata.width,
                                    height=metadata.height,
                                    file_modified_at=metadata.file_modified_at,
                                )

                                session.add(new_photo)
                                stats = dataclasses.replace(stats, files_added=stats.files_added + 1)
                                logger.debug(f"Added new photo: {image_file.name}")

                            else:
                                # Check if a file was modified since last sync
                                if existing_photo.file_modified_at != metadata.file_modified_at:
                                    # Update an existing photo
                                    existing_photo.filename = image_file.name
                                    existing_photo.category = category_name
                                    existing_photo.file_size = metadata.file_size
                                    existing_photo.width = metadata.width
                                    existing_photo.height = metadata.height
                                    existing_photo.file_modified_at = metadata.file_modified_at

                                    # Regenerate title if it wasn't manually set
                                    if (
                                        not existing_photo.title
                                        or existing_photo.title == generate_title_from_filename(existing_photo.filename)
                                    ):
                                        existing_photo.title = generate_title_from_filename(image_file.name)

                                    stats = dataclasses.replace(stats, files_updated=stats.files_updated + 1)
                                    logger.debug(f"Updated photo: {image_file.name}")

                        except Exception as e:
                            logger.error(f"Error processing {image_file}: {e}")
                            stats = dataclasses.replace(stats, errors=stats.errors + 1)
                            continue

                # Remove database entries for files that no longer exist
                orphaned_photos = [
                    photo for file_path, photo in existing_photos.items() if file_path not in found_file_paths
                ]

                if orphaned_photos:
                    orphaned_ids = [photo.id for photo in orphaned_photos]
                    await session.execute(delete(PLPhoto).where(PLPhoto.id.in_(orphaned_ids)))  # type: ignore[arg-type]
                    stats = dataclasses.replace(stats, files_removed=stats.files_removed + len(orphaned_photos))
                    logger.info(f"Removed {len(orphaned_photos)} orphaned photo records")

                await session.commit()

                logger.info(
                    f"Sync completed: {stats.files_scanned} scanned, "
                    f"{stats.files_added} added, {stats.files_updated} updated, "
                    f"{stats.files_removed} removed, {stats.errors} errors"
                )

                return stats

            except Exception as e:
                logger.error(f"Error during full sync: {e}")
                await session.rollback()
                raise

    async def _handle_file_created(self, session: AsyncSession, event: FileEvent) -> None:
        """Handle file creation event."""
        if not event.file_path.exists():
            logger.warning(f"File no longer exists: {event.file_path}")
            return

        if await self._get_photo_by_path(session, str(event.file_path)):
            logger.debug(f"Photo already exists in database: {event.file_path}")
            return

        metadata = extract_image_metadata(event.file_path)

        session.add(
            PLPhoto(
                filename=event.file_path.name,
                file_path=str(event.file_path.resolve()),
                category=event.category,
                title=generate_title_from_filename(event.file_path.name),
                file_size=metadata.file_size,
                width=metadata.width,
                height=metadata.height,
                file_modified_at=metadata.file_modified_at,
            )
        )
        logger.info(f"Added new photo: {event.file_path.name}")

    async def _handle_file_modified(self, session: AsyncSession, event: FileEvent) -> None:
        """Handle file modification event."""
        if not event.file_path.exists():
            logger.warning(f"File no longer exists: {event.file_path}")
            return

        existing_photo = await self._get_photo_by_path(session, str(event.file_path))
        if not existing_photo:
            logger.debug(f"Photo not in database, treating as new: {event.file_path}")
            await self._handle_file_created(session, event)
            return

        metadata = extract_image_metadata(event.file_path)

        if existing_photo.file_modified_at == metadata.file_modified_at:
            logger.debug(f"File modification time unchanged: {event.file_path}")
            return

        # Check if title should be updated before changing the filename
        should_update_title = not existing_photo.title or existing_photo.title == generate_title_from_filename(
            existing_photo.filename
        )

        existing_photo.filename = event.file_path.name
        existing_photo.category = event.category
        existing_photo.file_size = metadata.file_size
        existing_photo.width = metadata.width
        existing_photo.height = metadata.height
        existing_photo.file_modified_at = metadata.file_modified_at

        if should_update_title:
            existing_photo.title = generate_title_from_filename(event.file_path.name)

        logger.info(f"Updated photo: {event.file_path.name}")

    async def _handle_file_deleted(self, session: AsyncSession, event: FileEvent) -> None:
        """Handle file deletion event."""
        existing_photo = await self._get_photo_by_path(session, str(event.file_path))
        if not existing_photo:
            logger.debug(f"Photo not in database: {event.file_path}")
            return

        await session.delete(existing_photo)
        logger.info(f"Removed photo from database: {event.file_path.name}")

    async def _handle_file_moved(self, session: AsyncSession, event: FileEvent) -> None:
        """Handle file move/rename event."""
        # For move events, we'll treat it as a delete of the old location
        # The file watcher should generate a create event for the new location
        await self._handle_file_deleted(session, event)

    @staticmethod
    async def _get_existing_photos_by_path(session: AsyncSession) -> dict[str, PLPhoto]:
        """Get all existing photos indexed by their file path.

        Args:
            session: Database session

        Returns:
            Dictionary mapping file paths to Photo objects
        """
        result = await session.execute(select(PLPhoto))  # type: ignore[arg-type]
        photos = result.scalars().all()
        return {photo.file_path: photo for photo in photos}

    @staticmethod
    async def _get_photo_by_path(session: AsyncSession, file_path: str) -> PLPhoto | None:
        """Get a photo by its file path.

        Args:
            session: Database session
            file_path: File path to search for

        Returns:
            Photo object if found, None otherwise
        """
        result = await session.execute(select(PLPhoto).where(PLPhoto.file_path == file_path))  # type: ignore[arg-type]
        return result.scalar_one_or_none()

    def _is_supported_file(self, file_path: Path) -> bool:
        """Check if a file is a supported image format."""
        return is_supported_image_file(file_path, self.config.supported_extensions)

    def _extract_category_from_path(self, file_path: Path) -> str:
        """Extract category name from a file path."""
        # Assume photos are organized as /photos/category/image.jpg
        try:
            relative_path = file_path.relative_to(self.config.photos_base_path)
            return relative_path.parts[0] if relative_path.parts else "uncategorized"
        except ValueError:
            # File is outside the photos base path
            return "uncategorized"
