"""Tests for file system watcher functionality."""

from datetime import datetime, timezone
from pathlib import Path
from queue import Queue
from unittest.mock import patch

import pytest
from watchdog.events import FileCreatedEvent, FileDeletedEvent, FileModifiedEvent

from pgs_sync.sync_types import FileEvent, FileEventType
from pgs_sync.watcher import PhotoDirectoryEventHandler, PhotoDirectoryWatcher


class TestPhotoDirectoryEventHandler:
    """Test the PhotoDirectoryEventHandler class."""

    @pytest.fixture
    def event_handler(self, event_queue: Queue[FileEvent]) -> PhotoDirectoryEventHandler:
        """Create a PhotoDirectoryEventHandler for testing."""
        return PhotoDirectoryEventHandler(event_queue)

    @pytest.mark.unit
    def test_on_created_supported_file(self, event_handler: PhotoDirectoryEventHandler, event_queue: Queue):
        """Test handling of file creation events for supported files."""
        # Create a mock file creation event
        mock_event = FileCreatedEvent("/test/photos/landscapes/sunset.jpg")

        with patch.object(event_handler, "_is_supported_file", return_value=True):
            event_handler.on_created(mock_event)

        # Check that event was queued
        assert not event_queue.empty()
        file_event = event_queue.get()

        assert file_event.event_type == FileEventType.CREATED
        assert str(file_event.file_path) == "/test/photos/landscapes/sunset.jpg"
        assert file_event.category == "landscapes"
        assert isinstance(file_event.timestamp, datetime)

    @pytest.mark.unit
    def test_on_created_unsupported_file(self, event_handler: PhotoDirectoryEventHandler, event_queue: Queue):
        """Test that unsupported files are ignored."""
        mock_event = FileCreatedEvent("/test/photos/landscapes/document.txt")

        with patch.object(event_handler, "_is_supported_file", return_value=False):
            event_handler.on_created(mock_event)

        # Event queue should be empty
        assert event_queue.empty()

    @pytest.mark.unit
    def test_on_created_directory_event(self, event_handler: PhotoDirectoryEventHandler, event_queue: Queue):
        """Test that directory events are ignored."""
        mock_event = FileCreatedEvent("/test/photos/new_category")
        mock_event.is_directory = True

        event_handler.on_created(mock_event)

        # Event queue should be empty
        assert event_queue.empty()

    @pytest.mark.unit
    def test_on_modified_supported_file(self, event_handler: PhotoDirectoryEventHandler, event_queue: Queue):
        """Test handling of file modification events."""
        mock_event = FileModifiedEvent("/test/photos/portraits/person.jpg")

        with patch.object(event_handler, "_is_supported_file", return_value=True):
            event_handler.on_modified(mock_event)

        assert not event_queue.empty()
        file_event = event_queue.get()

        assert file_event.event_type == FileEventType.MODIFIED
        assert str(file_event.file_path) == "/test/photos/portraits/person.jpg"
        assert file_event.category == "portraits"

    @pytest.mark.unit
    def test_on_deleted_supported_file(self, event_handler: PhotoDirectoryEventHandler, event_queue: Queue):
        """Test handling of file deletion events."""
        mock_event = FileDeletedEvent("/test/photos/events/party.jpg")

        with patch.object(event_handler, "_is_supported_file", return_value=True):
            event_handler.on_deleted(mock_event)

        assert not event_queue.empty()
        file_event = event_queue.get()

        assert file_event.event_type == FileEventType.DELETED
        assert str(file_event.file_path) == "/test/photos/events/party.jpg"
        assert file_event.category == "events"

    @pytest.mark.unit
    def test_is_supported_file(self, event_handler: PhotoDirectoryEventHandler, mock_config):
        """Test the _is_supported_file method."""
        with patch("pgs_sync.watcher.sync_config", mock_config):
            # Test supported extension
            assert event_handler._is_supported_file("/test/image.jpg")
            assert event_handler._is_supported_file("/test/image.jpeg")
            assert event_handler._is_supported_file("/test/image.png")

            # Test unsupported extension
            assert not event_handler._is_supported_file("/test/document.txt")
            assert not event_handler._is_supported_file("/test/video.mp4")

    @pytest.mark.unit
    def test_extract_category_from_path(self, event_handler: PhotoDirectoryEventHandler, mock_config):
        """Test category extraction from file paths."""
        with patch("pgs_sync.watcher.sync_config", mock_config):
            # Test normal category extraction
            category = event_handler._extract_category_from_path(Path("/test/photos/landscapes/sunset.jpg"))
            assert category == "landscapes"

            category = event_handler._extract_category_from_path(Path("/test/photos/portraits/person.jpg"))
            assert category == "portraits"

    @pytest.mark.unit
    def test_extract_category_outside_base_path(self, event_handler: PhotoDirectoryEventHandler, mock_config):
        """Test category extraction for files outside base path."""
        with patch("pgs_sync.watcher.sync_config", mock_config):
            # File outside the configured photos base path
            category = event_handler._extract_category_from_path(Path("/other/location/image.jpg"))
            assert category == "location"  # Should use parent directory name

    @pytest.mark.unit
    def test_extract_category_no_parent(self, event_handler: PhotoDirectoryEventHandler, mock_config):
        """Test category extraction when there's no clear parent directory."""
        with patch("pgs_sync.watcher.sync_config", mock_config):
            # Root-level file
            category = event_handler._extract_category_from_path(Path("/image.jpg"))
            assert category == "uncategorized"

    @pytest.mark.unit
    def test_queue_event_exception_handling(self, event_handler: PhotoDirectoryEventHandler, event_queue: Queue):
        """Test that exceptions in _queue_event are handled gracefully."""
        with patch.object(event_handler, "_extract_category_from_path", side_effect=Exception("Test error")):
            # Should not raise exception
            event_handler._queue_event(FileEventType.CREATED, "/test/image.jpg")

        # Queue should remain empty due to error
        assert event_queue.empty()

    @pytest.mark.unit
    def test_timestamp_timezone(self, event_handler: PhotoDirectoryEventHandler, event_queue: Queue):
        """Test that event timestamps are in UTC."""
        mock_event = FileCreatedEvent("/test/photos/landscapes/sunset.jpg")

        with patch.object(event_handler, "_is_supported_file", return_value=True):
            event_handler.on_created(mock_event)

        file_event = event_queue.get()
        assert file_event.timestamp.tzinfo == timezone.utc

    @pytest.mark.unit
    def test_multiple_events_queued(self, event_handler: PhotoDirectoryEventHandler, event_queue: Queue):
        """Test that multiple events are queued correctly."""
        events = [
            FileCreatedEvent("/test/photos/landscapes/sunset.jpg"),
            FileModifiedEvent("/test/photos/portraits/person.jpg"),
            FileDeletedEvent("/test/photos/events/party.jpg"),
        ]

        with patch.object(event_handler, "_is_supported_file", return_value=True):
            for event in events:
                if isinstance(event, FileCreatedEvent):
                    event_handler.on_created(event)
                elif isinstance(event, FileModifiedEvent):
                    event_handler.on_modified(event)
                elif isinstance(event, FileDeletedEvent):
                    event_handler.on_deleted(event)

        # All events should be queued
        assert event_queue.qsize() == 3

        # Check event types are correct
        event_types = []
        while not event_queue.empty():
            file_event = event_queue.get()
            event_types.append(file_event.event_type)

        assert FileEventType.CREATED in event_types
        assert FileEventType.MODIFIED in event_types
        assert FileEventType.DELETED in event_types


class TestPhotoDirectoryWatcher:
    """Test the PhotoDirectoryWatcher class."""

    @pytest.fixture
    def watcher(self, temp_photos_dir: Path, event_queue: Queue[FileEvent]) -> PhotoDirectoryWatcher:
        """Create a PhotoDirectoryWatcher for testing."""
        return PhotoDirectoryWatcher(temp_photos_dir, event_queue)

    @pytest.mark.unit
    def test_initialization(self, watcher: PhotoDirectoryWatcher, temp_photos_dir: Path, event_queue: Queue):
        """Test that watcher is initialized correctly."""
        assert watcher.photos_path == temp_photos_dir
        assert watcher.event_queue is event_queue
        assert watcher.observer is not None
        assert watcher.event_handler is not None
        assert isinstance(watcher.event_handler, PhotoDirectoryEventHandler)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_start_watching(self, watcher: PhotoDirectoryWatcher):
        """Test starting the file system watcher."""
        with (
            patch.object(watcher.observer, "schedule") as mock_schedule,
            patch.object(watcher.observer, "start") as mock_start,
        ):

            await watcher.start_watching()

            # Observer should be scheduled and started
            mock_schedule.assert_called_once_with(watcher.event_handler, str(watcher.photos_path), recursive=True)
            mock_start.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_stop_watching(self, watcher: PhotoDirectoryWatcher):
        """Test stopping the file system watcher."""
        with patch.object(watcher.observer, "stop") as mock_stop, patch.object(watcher.observer, "join") as mock_join:

            await watcher.stop_watching()

            # Observer should be stopped and joined
            mock_stop.assert_called_once()
            mock_join.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_watcher_lifecycle(self, watcher: PhotoDirectoryWatcher):
        """Test complete watcher lifecycle (start then stop)."""
        with (
            patch.object(watcher.observer, "schedule"),
            patch.object(watcher.observer, "start"),
            patch.object(watcher.observer, "stop"),
            patch.object(watcher.observer, "join"),
        ):

            # Should be able to start and stop without errors
            await watcher.start_watching()
            await watcher.stop_watching()

    @pytest.mark.unit
    def test_event_handler_connection(self, watcher: PhotoDirectoryWatcher, event_queue: Queue):
        """Test that event handler is connected to the same queue."""
        assert watcher.event_handler.event_queue is event_queue

    @pytest.mark.unit
    def test_photos_path_validation(self, event_queue: Queue):
        """Test behavior with different photos path types."""
        # Test with a Path object
        path = Path("/test/photos")
        watcher = PhotoDirectoryWatcher(path, event_queue)
        assert watcher.photos_path == path

        # Test path is stored as-is (not converted)
        assert isinstance(watcher.photos_path, Path)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_observer_configuration(self, watcher: PhotoDirectoryWatcher):
        """Test that observer is configured correctly for recursive watching."""
        with patch.object(watcher.observer, "schedule") as mock_schedule:
            await watcher.start_watching()

            # Verify recursive=True is passed
            args, kwargs = mock_schedule.call_args
            assert args[0] is watcher.event_handler
            assert args[1] == str(watcher.photos_path)
            assert kwargs.get("recursive") is True
