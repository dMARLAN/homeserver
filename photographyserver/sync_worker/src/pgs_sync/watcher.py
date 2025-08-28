"""File system event handling using watchdog."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from pgs_sync.config import sync_config
from pgs_sync.sync_types import FileEvent, FileEventType

logger = logging.getLogger(__name__)


class PhotoDirectoryEventHandler(FileSystemEventHandler):
    """Handler for file system events in the photos directory."""

    def __init__(self, event_queue: Queue[FileEvent]) -> None:
        super().__init__()
        self.event_queue = event_queue

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if not event.is_directory and self._is_supported_file(str(event.src_path)):
            self._queue_event(FileEventType.CREATED, str(event.src_path))

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if not event.is_directory and self._is_supported_file(str(event.src_path)):
            self._queue_event(FileEventType.MODIFIED, str(event.src_path))

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events."""
        if not event.is_directory and self._is_supported_file(str(event.src_path)):
            self._queue_event(FileEventType.DELETED, str(event.src_path))

    @staticmethod
    def _is_supported_file(file_path: str) -> bool:
        """Check if a file is a supported image format."""
        return Path(file_path).suffix.lower() in sync_config.supported_extensions

    def _queue_event(self, event_type: FileEventType, file_path: str) -> None:
        """Queue a file event for processing."""
        try:
            # Convert to a Path object for easier manipulation
            path = Path(file_path)

            # Extract category from file path (photos/category/filename.jpg -> category)
            category = self._extract_category_from_path(path)

            # Create FileEvent object
            file_event = FileEvent(
                event_type=event_type, file_path=path, category=category, timestamp=datetime.now(timezone.utc)
            )

            # Add to queue
            self.event_queue.put(file_event)
            logger.debug(f"Queued file event: {event_type.value} - {file_path} (category: {category})")

        except Exception as e:
            logger.error(f"Error queuing file event {event_type.value} for {file_path}: {e}")

    @staticmethod
    def _extract_category_from_path(file_path: Path) -> str:
        """Extract category name from file path.

        Assumes photos are organized as /photos/category/filename.jpg

        Args:
            file_path: Path to the image file

        Returns:
            Category name, or 'uncategorized' if unable to extract
        """
        try:
            # Try to get a relative path from the photos base path
            relative_path = file_path.relative_to(sync_config.photos_base_path)
            # Return the first directory component as category
            return relative_path.parts[0] if relative_path.parts else "uncategorized"
        except ValueError:
            # File is outside the photos base path, use parent directory name
            return file_path.parent.name if file_path.parent.name else "uncategorized"


class PhotoDirectoryWatcher:
    """Watches the photos directory for file system changes."""

    def __init__(self, photos_path: Path, event_queue: Queue[FileEvent]) -> None:
        self.photos_path = photos_path
        self.event_queue = event_queue
        self.observer = Observer()
        self.event_handler = PhotoDirectoryEventHandler(event_queue)

    async def start_watching(self) -> None:
        """Start watching the photos directory."""
        logger.info(f"Starting file system watcher for {self.photos_path}")
        self.observer.schedule(self.event_handler, str(self.photos_path), recursive=True)
        self.observer.start()

    async def stop_watching(self) -> None:
        """Stop watching the photos directory."""
        logger.info("Stopping file system watcher")
        self.observer.stop()
        self.observer.join()
