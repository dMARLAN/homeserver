"""Tests for sync engine functionality."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pgs_db.models.photos import PLPhoto
from pgs_sync.sync_engine import SyncEngine
from pgs_sync.sync_types import FileEvent, FileEventType, ImageMetadata, SyncStats


class TestSyncEngine:
    """Test the SyncEngine class."""

    @pytest.fixture
    def sync_engine(self, mock_db_session_factory) -> SyncEngine:
        """Create a SyncEngine for testing."""
        return SyncEngine(mock_db_session_factory)

    @pytest.mark.unit
    def test_initialization(self, sync_engine: SyncEngine, mock_db_session_factory):
        """Test that SyncEngine is initialized correctly."""
        assert sync_engine.db_session_factory is mock_db_session_factory
        assert sync_engine.config is not None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_file_event_created(self, sync_engine: SyncEngine, mock_db_session: AsyncMock):
        """Test processing a file creation event."""
        # Create a file event
        event = FileEvent(
            event_type=FileEventType.CREATED,
            file_path=Path("/test/photos/landscapes/sunset.jpg"),
            category="landscapes",
            timestamp=datetime.now(timezone.utc),
        )

        # Mock dependencies
        with (
            patch.object(sync_engine, "_is_supported_file", return_value=True),
            patch.object(sync_engine, "_handle_file_created", new_callable=AsyncMock) as mock_handle,
        ):

            await sync_engine.process_file_event(event)

            # Verify the correct handler was called
            mock_handle.assert_called_once_with(mock_db_session, event)
            mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_file_event_unsupported(self, sync_engine: SyncEngine, mock_db_session: AsyncMock):
        """Test that unsupported files are skipped."""
        event = FileEvent(
            event_type=FileEventType.CREATED,
            file_path=Path("/test/photos/landscapes/document.txt"),
            category="landscapes",
            timestamp=datetime.now(timezone.utc),
        )

        with patch.object(sync_engine, "_is_supported_file", return_value=False):
            await sync_engine.process_file_event(event)

            # Session should not be used for unsupported files
            mock_db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_file_event_exception_handling(self, sync_engine: SyncEngine, mock_db_session: AsyncMock):
        """Test exception handling in process_file_event."""
        event = FileEvent(
            event_type=FileEventType.CREATED,
            file_path=Path("/test/photos/landscapes/sunset.jpg"),
            category="landscapes",
            timestamp=datetime.now(timezone.utc),
        )

        # Mock an exception in the handler
        with (
            patch.object(sync_engine, "_is_supported_file", return_value=True),
            patch.object(sync_engine, "_handle_file_created", side_effect=Exception("Database error")),
        ):

            with pytest.raises(Exception, match="Database error"):
                await sync_engine.process_file_event(event)

            # Session should be rolled back on error
            mock_db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_event_batch(self, sync_engine: SyncEngine, mock_db_session: AsyncMock):
        """Test processing a batch of events."""
        events = [
            FileEvent(
                event_type=FileEventType.CREATED,
                file_path=Path("/test/photos/landscapes/sunset.jpg"),
                category="landscapes",
                timestamp=datetime.now(timezone.utc),
            ),
            FileEvent(
                event_type=FileEventType.MODIFIED,
                file_path=Path("/test/photos/portraits/person.jpg"),
                category="portraits",
                timestamp=datetime.now(timezone.utc),
            ),
        ]

        with (
            patch.object(sync_engine, "_is_supported_file", return_value=True),
            patch.object(sync_engine, "_handle_file_created", new_callable=AsyncMock),
            patch.object(sync_engine, "_handle_file_modified", new_callable=AsyncMock),
        ):

            await sync_engine.process_event_batch(events)

            # Session should be committed once for the batch
            mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_event_batch_empty(self, sync_engine: SyncEngine, mock_db_session: AsyncMock):
        """Test processing an empty batch."""
        with patch.object(sync_engine, "_is_supported_file", return_value=False):
            await sync_engine.process_event_batch([])

            # Should not interact with a database for empty batch
            mock_db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_handle_file_created_new_file(self, sync_engine: SyncEngine, mock_db_session: AsyncMock):
        """Test handling creation of a new file."""
        event = FileEvent(
            event_type=FileEventType.CREATED,
            file_path=Path("/test/photos/landscapes/sunset.jpg"),
            category="landscapes",
            timestamp=datetime.now(timezone.utc),
        )

        # Mock file exists and metadata extraction
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch.object(sync_engine, "_get_photo_by_path", return_value=None),
            patch("pgs_sync.sync_engine.extract_image_metadata") as mock_extract,
            patch("pgs_sync.sync_engine.generate_title_from_filename", return_value="Beautiful Sunset"),
        ):

            mock_extract.return_value = ImageMetadata(
                file_size=1024000, width=1920, height=1080, file_modified_at=datetime.now(timezone.utc)
            )

            await sync_engine._handle_file_created(mock_db_session, event)

            # Should add a new photo to session
            mock_db_session.add.assert_called_once()
            added_photo = mock_db_session.add.call_args[0][0]
            assert isinstance(added_photo, PLPhoto)
            assert added_photo.filename == "sunset.jpg"
            assert added_photo.category == "landscapes"
            assert added_photo.title == "Beautiful Sunset"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_handle_file_created_file_not_exists(self, sync_engine: SyncEngine, mock_db_session: AsyncMock):
        """Test handling creation event when file doesn't exist."""
        event = FileEvent(
            event_type=FileEventType.CREATED,
            file_path=Path("/test/photos/landscapes/sunset.jpg"),
            category="landscapes",
            timestamp=datetime.now(timezone.utc),
        )

        with patch("pathlib.Path.exists", return_value=False):
            await sync_engine._handle_file_created(mock_db_session, event)

            # Should not add anything to session
            mock_db_session.add.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_handle_file_created_already_exists(self, sync_engine: SyncEngine, mock_db_session: AsyncMock):
        """Test handling creation event when a photo already exists in a database."""
        event = FileEvent(
            event_type=FileEventType.CREATED,
            file_path=Path("/test/photos/landscapes/sunset.jpg"),
            category="landscapes",
            timestamp=datetime.now(timezone.utc),
        )

        existing_photo = PLPhoto(
            filename="sunset.jpg",
            file_path="/test/photos/landscapes/sunset.jpg",
            category="landscapes",
            title="Existing Sunset",
            file_size=1024000,
            width=1920,
            height=1080,
            file_modified_at=datetime.now(timezone.utc),
        )

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch.object(sync_engine, "_get_photo_by_path", return_value=existing_photo),
        ):

            await sync_engine._handle_file_created(mock_db_session, event)

            # Should not add duplicate
            mock_db_session.add.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_handle_file_modified(self, sync_engine: SyncEngine, mock_db_session: AsyncMock):
        """Test handling file modification event."""
        event = FileEvent(
            event_type=FileEventType.MODIFIED,
            file_path=Path("/test/photos/landscapes/beautiful_sunset.jpg"),
            category="landscapes",
            timestamp=datetime.now(timezone.utc),
        )

        # Create an existing photo with old timestamp
        old_timestamp = datetime(2023, 1, 1, tzinfo=timezone.utc)
        new_timestamp = datetime.now(timezone.utc)

        existing_photo = PLPhoto(
            filename="sunset.jpg",
            file_path="/test/photos/landscapes/sunset.jpg",
            category="landscapes",
            title="Sunset",  # Use the auto-generated title so it gets updated
            file_size=512000,
            width=1280,
            height=720,
            file_modified_at=old_timestamp,
        )

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch.object(sync_engine, "_get_photo_by_path", return_value=existing_photo),
            patch("pgs_sync.sync_engine.extract_image_metadata") as mock_extract,
            patch(
                "pgs_sync.sync_engine.generate_title_from_filename",
                side_effect=lambda name: "Sunset" if name == "sunset.jpg" else "Beautiful Sunset",
            ),
        ):

            mock_extract.return_value = ImageMetadata(
                file_size=1024000, width=1920, height=1080, file_modified_at=new_timestamp
            )

            await sync_engine._handle_file_modified(mock_db_session, event)

            # Photo should be updated
            assert existing_photo.file_size == 1024000
            assert existing_photo.width == 1920
            assert existing_photo.height == 1080
            assert existing_photo.file_modified_at == new_timestamp
            assert existing_photo.title == "Beautiful Sunset"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_handle_file_modified_no_change(self, sync_engine: SyncEngine, mock_db_session: AsyncMock):
        """Test handling modification event when a file hasn't changed."""
        event = FileEvent(
            event_type=FileEventType.MODIFIED,
            file_path=Path("/test/photos/landscapes/sunset.jpg"),
            category="landscapes",
            timestamp=datetime.now(timezone.utc),
        )

        timestamp = datetime.now(timezone.utc)
        existing_photo = PLPhoto(
            filename="sunset.jpg",
            file_path="/test/photos/landscapes/sunset.jpg",
            category="landscapes",
            title="Sunset",
            file_size=1024000,
            width=1920,
            height=1080,
            file_modified_at=timestamp,
        )

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch.object(sync_engine, "_get_photo_by_path", return_value=existing_photo),
            patch("pgs_sync.sync_engine.extract_image_metadata") as mock_extract,
        ):

            # Same modification time
            mock_extract.return_value = ImageMetadata(
                file_size=1024000, width=1920, height=1080, file_modified_at=timestamp
            )

            original_size = existing_photo.file_size
            await sync_engine._handle_file_modified(mock_db_session, event)

            # Photo should not be changed
            assert existing_photo.file_size == original_size

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_handle_file_deleted(self, sync_engine: SyncEngine, mock_db_session: AsyncMock):
        """Test handling file deletion event."""
        event = FileEvent(
            event_type=FileEventType.DELETED,
            file_path=Path("/test/photos/landscapes/sunset.jpg"),
            category="landscapes",
            timestamp=datetime.now(timezone.utc),
        )

        existing_photo = PLPhoto(
            filename="sunset.jpg",
            file_path="/test/photos/landscapes/sunset.jpg",
            category="landscapes",
            title="Sunset",
            file_size=1024000,
            width=1920,
            height=1080,
            file_modified_at=datetime.now(timezone.utc),
        )

        with patch.object(sync_engine, "_get_photo_by_path", return_value=existing_photo):
            await sync_engine._handle_file_deleted(mock_db_session, event)

            # Photo should be deleted from session
            mock_db_session.delete.assert_called_once_with(existing_photo)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_handle_file_deleted_not_found(self, sync_engine: SyncEngine, mock_db_session: AsyncMock):
        """Test handling deletion event when photo not in database."""
        event = FileEvent(
            event_type=FileEventType.DELETED,
            file_path=Path("/test/photos/landscapes/sunset.jpg"),
            category="landscapes",
            timestamp=datetime.now(timezone.utc),
        )

        with patch.object(sync_engine, "_get_photo_by_path", return_value=None):
            await sync_engine._handle_file_deleted(mock_db_session, event)

            # Should not attempt to delete
            mock_db_session.delete.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_perform_initial_sync(self, sync_engine: SyncEngine):
        """Test performing initial sync."""
        with patch.object(sync_engine, "_perform_full_sync", new_callable=AsyncMock) as mock_full_sync:
            mock_stats = SyncStats(files_scanned=100, files_added=10, files_updated=5, files_removed=2, errors=1)
            mock_full_sync.return_value = mock_stats

            result = await sync_engine.perform_initial_sync()

            assert result == mock_stats
            mock_full_sync.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_perform_periodic_sync(self, sync_engine: SyncEngine):
        """Test performing periodic sync."""
        with patch.object(sync_engine, "_perform_full_sync", new_callable=AsyncMock) as mock_full_sync:
            mock_stats = SyncStats(files_scanned=50, files_added=2, files_updated=1, files_removed=0, errors=0)
            mock_full_sync.return_value = mock_stats

            result = await sync_engine.perform_periodic_sync()

            assert result == mock_stats
            mock_full_sync.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_perform_full_sync_directory_not_found(self, sync_engine: SyncEngine, mock_config):
        """Test full sync when photos directory doesn't exist."""
        mock_config.photos_base_path = Path("/nonexistent/photos")

        with patch.object(sync_engine, "config", mock_config):
            with pytest.raises(FileNotFoundError, match="Storage directory not found"):
                await sync_engine._perform_full_sync()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_perform_full_sync_not_directory(self, sync_engine: SyncEngine, mock_config):
        """Test full sync when a photos path is not a directory."""
        # Create a temporary file instead of directory
        with tempfile.NamedTemporaryFile() as temp_file:
            mock_config.photos_base_path = Path(temp_file.name)

            with patch.object(sync_engine, "config", mock_config):
                with pytest.raises(ValueError, match="Storage path is not a directory"):
                    await sync_engine._perform_full_sync()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_photo_by_path(self, sync_engine: SyncEngine, mock_db_session: AsyncMock):
        """Test getting a photo by file path."""
        mock_photo = PLPhoto(
            filename="sunset.jpg",
            file_path="/test/photos/landscapes/sunset.jpg",
            category="landscapes",
            title="Sunset",
            file_size=1024000,
            width=1920,
            height=1080,
            file_modified_at=datetime.now(timezone.utc),
        )

        # Mock the database query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_photo
        mock_db_session.execute.return_value = mock_result

        result = await sync_engine._get_photo_by_path(mock_db_session, "/test/photos/landscapes/sunset.jpg")

        assert result == mock_photo
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_existing_photos_by_path(self, sync_engine: SyncEngine, mock_db_session: AsyncMock):
        """Test getting all existing photos indexed by path."""
        mock_photos = [
            PLPhoto(
                filename="sunset.jpg",
                file_path="/test/photos/landscapes/sunset.jpg",
                category="landscapes",
                title="Sunset",
                file_size=1024000,
                width=1920,
                height=1080,
                file_modified_at=datetime.now(timezone.utc),
            ),
            PLPhoto(
                filename="person.jpg",
                file_path="/test/photos/portraits/person.jpg",
                category="portraits",
                title="Person",
                file_size=512000,
                width=1280,
                height=720,
                file_modified_at=datetime.now(timezone.utc),
            ),
        ]

        # Mock the database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_photos
        mock_db_session.execute.return_value = mock_result

        result = await sync_engine._get_existing_photos_by_path(mock_db_session)

        expected = {
            "/test/photos/landscapes/sunset.jpg": mock_photos[0],
            "/test/photos/portraits/person.jpg": mock_photos[1],
        }
        assert result == expected

    @pytest.mark.unit
    def test_is_supported_file(self, sync_engine: SyncEngine, mock_config):
        """Test checking if a file is supported."""
        with patch.object(sync_engine, "config", mock_config):
            assert sync_engine._is_supported_file(Path("/test/image.jpg"))
            assert sync_engine._is_supported_file(Path("/test/image.png"))
            assert not sync_engine._is_supported_file(Path("/test/document.txt"))

    @pytest.mark.unit
    def test_extract_category_from_path(self, sync_engine: SyncEngine, mock_config):
        """Test extracting category from a file path."""
        with patch.object(sync_engine, "config", mock_config):
            category = sync_engine._extract_category_from_path(Path("/test/photos/landscapes/sunset.jpg"))
            assert category == "landscapes"

            # Test file outside a base path
            category = sync_engine._extract_category_from_path(Path("/other/location/image.jpg"))
            assert category == "uncategorized"
