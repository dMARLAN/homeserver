"""Integration tests for the sync worker components."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from pgs_sync.config import SyncConfig
from pgs_sync.health import HealthMonitor
from pgs_sync.sync_engine import SyncEngine
from pgs_sync.sync_types import FileEvent, FileEventType, ImageMetadata
from pgs_sync.utils import extract_image_metadata, generate_title_from_filename
from pgs_sync.watcher import PhotoDirectoryEventHandler, PhotoDirectoryWatcher


@pytest.fixture
def temp_photos_structure():
    """Create a temporary photos directory with realistic structure."""
    with tempfile.TemporaryDirectory() as temp_dir:
        photos_path = Path(temp_dir) / "photos"
        photos_path.mkdir()

        # Create category directories
        categories = ["landscapes", "portraits", "events", "nature"]
        for category in categories:
            (photos_path / category).mkdir()

        yield photos_path


@pytest.fixture
def integration_config(temp_photos_structure):
    """Create a config for integration testing."""
    return SyncConfig(
        photos_base_path=temp_photos_structure,
        supported_extensions={".jpg", ".jpeg", ".png", ".gif"},
        initial_sync_on_startup=False,
        event_debounce_delay=0.1,  # Fast for testing
        max_batch_size=5,
        retry_attempts=2,
        retry_delay=0.1,
    )


class TestFileSystemEventSimulation:
    """Test file system event simulation and processing."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_file_creation(self, temp_photos_structure, integration_config):
        """Test complete flow from file creation to database update."""
        # Create event queue and components
        event_queue = Queue()

        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)

        def mock_session_factory():
            # Create an async context manager that returns the mock session
            async_context = AsyncMock()
            async_context.__aenter__ = AsyncMock(return_value=mock_session)
            async_context.__aexit__ = AsyncMock(return_value=None)
            return async_context

        # Create components
        sync_engine = SyncEngine(mock_session_factory)
        event_handler = PhotoDirectoryEventHandler(event_queue)

        # Create a test image file
        image_path = temp_photos_structure / "landscapes" / "sunset.jpg"
        test_image = Image.new("RGB", (800, 600), color="orange")
        test_image.save(image_path, "JPEG")

        # Simulate file creation event
        with (
            patch.object(sync_engine, "config", integration_config),
            patch.object(sync_engine, "_get_photo_by_path", return_value=None),
        ):
            # Queue the event
            event_handler._queue_event(FileEventType.CREATED, str(image_path))

            # Get event from the queue
            assert not event_queue.empty()
            file_event = event_queue.get()

            # Verify event details
            assert file_event.event_type == FileEventType.CREATED
            assert file_event.file_path == image_path
            assert file_event.category == "landscapes"

            # Process the event
            await sync_engine.process_file_event(file_event)

            # Verify database interaction
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_batch_event_processing(self, temp_photos_structure, integration_config):
        """Test processing multiple events in a batch."""
        event_queue = Queue()

        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)

        def mock_session_factory():
            # Create an async context manager that returns the mock session
            async_context = AsyncMock()
            async_context.__aenter__ = AsyncMock(return_value=mock_session)
            async_context.__aexit__ = AsyncMock(return_value=None)
            return async_context

        sync_engine = SyncEngine(mock_session_factory)
        event_handler = PhotoDirectoryEventHandler(event_queue)

        # Create multiple test files
        image_files = []
        for i, category in enumerate(["landscapes", "portraits", "nature"]):
            image_path = temp_photos_structure / category / f"image_{i}.jpg"
            test_image = Image.new("RGB", (400, 300), color="blue")
            test_image.save(image_path, "JPEG")
            image_files.append(image_path)

        with (
            patch.object(sync_engine, "config", integration_config),
            patch.object(sync_engine, "_get_photo_by_path", return_value=None),
        ):
            # Queue multiple events
            events = []
            for image_path in image_files:
                event_handler._queue_event(FileEventType.CREATED, str(image_path))
                events.append(event_queue.get())

            # Process batch
            await sync_engine.process_event_batch(events)

            # Should add all photos and commit once
            assert mock_session.add.call_count == len(image_files)
            mock_session.commit.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_file_modification_workflow(self, temp_photos_structure, integration_config):
        """Test complete workflow for file modification events."""
        event_queue = Queue()

        # Mock database session with existing photo
        mock_session = AsyncMock(spec=AsyncSession)

        def mock_session_factory():
            # Create an async context manager that returns the mock session
            async_context = AsyncMock()
            async_context.__aenter__ = AsyncMock(return_value=mock_session)
            async_context.__aexit__ = AsyncMock(return_value=None)
            return async_context

        # Create existing photo mock
        from pgs_db.models.photos import PLPhoto

        existing_photo = PLPhoto(
            filename="modified_image.jpg",
            file_path=str(temp_photos_structure / "portraits" / "modified_image.jpg"),
            category="portraits",
            title="Old Title",
            file_size=1000,
            width=200,
            height=200,
            file_modified_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
        )

        sync_engine = SyncEngine(mock_session_factory)
        event_handler = PhotoDirectoryEventHandler(event_queue)

        # Create and modify image file
        image_path = temp_photos_structure / "portraits" / "modified_image.jpg"
        test_image = Image.new("RGB", (400, 300), color="green")
        test_image.save(image_path, "JPEG")

        with (
            patch.object(sync_engine, "config", integration_config),
            patch.object(sync_engine, "_get_photo_by_path", return_value=existing_photo),
        ):

            # Queue modification event
            event_handler._queue_event(FileEventType.MODIFIED, str(image_path))
            file_event = event_queue.get()

            # Process modification
            await sync_engine.process_file_event(file_event)

            # Verify photo was updated (not added)
            mock_session.add.assert_not_called()
            mock_session.commit.assert_called_once()

            # Check that photo attributes were updated
            assert existing_photo.width == 400
            assert existing_photo.height == 300
            assert existing_photo.file_size > 1000  # New file should be larger

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_file_deletion_workflow(self, temp_photos_structure, integration_config):
        """Test complete workflow for file deletion events."""
        event_queue = Queue()

        # Mock database session
        mock_session = AsyncMock(spec=AsyncSession)

        def mock_session_factory():
            # Create an async context manager that returns the mock session
            async_context = AsyncMock()
            async_context.__aenter__ = AsyncMock(return_value=mock_session)
            async_context.__aexit__ = AsyncMock(return_value=None)
            return async_context

        # Create existing photo mock
        from pgs_db.models.photos import PLPhoto

        existing_photo = PLPhoto(
            filename="deleted_image.jpg",
            file_path=str(temp_photos_structure / "events" / "deleted_image.jpg"),
            category="events",
            title="To Be Deleted",
            file_size=1000,
            width=200,
            height=200,
            file_modified_at=datetime.now(timezone.utc),
        )

        sync_engine = SyncEngine(mock_session_factory)
        event_handler = PhotoDirectoryEventHandler(event_queue)

        with (
            patch.object(sync_engine, "config", integration_config),
            patch.object(sync_engine, "_get_photo_by_path", return_value=existing_photo),
        ):

            # Queue deletion event
            image_path = temp_photos_structure / "events" / "deleted_image.jpg"
            event_handler._queue_event(FileEventType.DELETED, str(image_path))
            file_event = event_queue.get()

            # Process deletion
            await sync_engine.process_file_event(file_event)

            # Verify photo was deleted
            mock_session.delete.assert_called_once_with(existing_photo)
            mock_session.commit.assert_called_once()


class TestHealthMonitoringIntegration:
    """Test integration of health monitoring with other components."""

    @pytest.mark.integration
    def test_health_monitor_basic_functionality(self):
        """Test basic health monitor functionality."""
        # Create health monitor
        health_monitor = HealthMonitor()

        # Test health check
        from fastapi.testclient import TestClient

        client = TestClient(health_monitor.get_app())

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery scenarios."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_database_error_recovery(self, integration_config):
        """Test recovery from database errors."""
        # Mock database session that fails first, then succeeds
        call_count = 0

        def mock_session_factory():
            nonlocal call_count
            call_count += 1
            session = AsyncMock(spec=AsyncSession)

            if call_count == 1:
                # First attempt fails
                session.commit.side_effect = Exception("Database connection lost")
            else:
                # Subsequent attempts succeed
                session.commit.side_effect = None

            # Create an async context manager that returns the mock session
            async_context = AsyncMock()
            async_context.__aenter__ = AsyncMock(return_value=session)
            async_context.__aexit__ = AsyncMock(return_value=None)
            return async_context

        sync_engine = SyncEngine(mock_session_factory)

        # Create test event
        event = FileEvent(
            event_type=FileEventType.CREATED,
            file_path=Path("/test/image.jpg"),
            category="test",
            timestamp=datetime.now(timezone.utc),
        )

        with (
            patch.object(sync_engine, "config", integration_config),
            patch.object(sync_engine, "_is_supported_file", return_value=True),
            patch.object(sync_engine, "_get_photo_by_path", return_value=None),
            patch("pathlib.Path.exists", return_value=True),
            patch("pgs_sync.sync_engine.extract_image_metadata") as mock_extract,
        ):
            mock_extract.return_value = ImageMetadata(
                file_size=1024, width=800, height=600, file_modified_at=datetime.now(timezone.utc)
            )

            # First attempt should fail
            with pytest.raises(Exception, match="Database connection lost"):
                await sync_engine.process_file_event(event)

            # Second attempt should succeed
            await sync_engine.process_file_event(event)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_file_system_error_handling(self, temp_photos_structure, integration_config):
        """Test handling of file system errors."""
        event_queue = Queue()

        mock_session = AsyncMock(spec=AsyncSession)

        def mock_session_factory():
            # Create an async context manager that returns the mock session
            async_context = AsyncMock()
            async_context.__aenter__ = AsyncMock(return_value=mock_session)
            async_context.__aexit__ = AsyncMock(return_value=None)
            return async_context

        sync_engine = SyncEngine(mock_session_factory)
        event_handler = PhotoDirectoryEventHandler(event_queue)

        with patch.object(sync_engine, "config", integration_config):
            # Test event for non-existent file
            non_existent_path = temp_photos_structure / "landscapes" / "missing.jpg"
            event_handler._queue_event(FileEventType.CREATED, str(non_existent_path))
            file_event = event_queue.get()

            # Should handle gracefully without crashing
            await sync_engine.process_file_event(file_event)

            # Session should not be modified for non-existent file
            mock_session.add.assert_not_called()

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_high_volume_event_processing(self, temp_photos_structure, integration_config):
        """Test processing high volume of events (load testing)."""
        event_queue = Queue()

        mock_session = AsyncMock(spec=AsyncSession)

        def mock_session_factory():
            # Create an async context manager that returns the mock session
            async_context = AsyncMock()
            async_context.__aenter__ = AsyncMock(return_value=mock_session)
            async_context.__aexit__ = AsyncMock(return_value=None)
            return async_context

        sync_engine = SyncEngine(mock_session_factory)
        event_handler = PhotoDirectoryEventHandler(event_queue)

        # Create many test files
        num_files = 50
        image_files = []

        for i in range(num_files):
            category = ["landscapes", "portraits", "nature"][i % 3]
            image_path = temp_photos_structure / category / f"bulk_image_{i}.jpg"
            test_image = Image.new("RGB", (100, 100), color="red")
            test_image.save(image_path, "JPEG")
            image_files.append(image_path)

        with (
            patch.object(sync_engine, "config", integration_config),
            patch.object(sync_engine, "_get_photo_by_path", return_value=None),
            patch("pathlib.Path.exists", return_value=True),
            patch("pgs_sync.sync_engine.extract_image_metadata") as mock_extract,
        ):
            mock_extract.return_value = ImageMetadata(
                file_size=1024, width=100, height=100, file_modified_at=datetime.now(timezone.utc)
            )

            # Queue all events
            events = []
            for image_path in image_files:
                event_handler._queue_event(FileEventType.CREATED, str(image_path))
                events.append(event_queue.get())

            # Process in batches
            batch_size = 10
            for i in range(0, len(events), batch_size):
                batch = events[i : i + batch_size]
                await sync_engine.process_event_batch(batch)

            # Verify all events were processed
            assert mock_session.add.call_count == num_files


class TestComponentInteraction:
    """Test interactions between different components."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_watcher_to_engine_flow(self, temp_photos_structure):
        """Test flow from watcher detecting event to engine processing it."""
        event_queue = Queue()

        # Create components
        watcher = PhotoDirectoryWatcher(temp_photos_structure, event_queue)

        mock_session = AsyncMock(spec=AsyncSession)

        def mock_session_factory():
            # Create an async context manager that returns the mock session
            async_context = AsyncMock()
            async_context.__aenter__ = AsyncMock(return_value=mock_session)
            async_context.__aexit__ = AsyncMock(return_value=None)
            return async_context

        config = SyncConfig(
            photos_base_path=temp_photos_structure,
            supported_extensions={".jpg"},
            event_debounce_delay=0.1,
        )

        sync_engine = SyncEngine(mock_session_factory)

        # Create test image
        image_path = temp_photos_structure / "landscapes" / "test_flow.jpg"
        test_image = Image.new("RGB", (200, 200), color="purple")
        test_image.save(image_path, "JPEG")

        with (
            patch.object(sync_engine, "config", config),
            patch.object(sync_engine, "_get_photo_by_path", return_value=None),
            patch("pathlib.Path.exists", return_value=True),
            patch("pgs_sync.sync_engine.extract_image_metadata") as mock_extract,
        ):
            mock_extract.return_value = ImageMetadata(
                file_size=1024, width=200, height=200, file_modified_at=datetime.now(timezone.utc)
            )

            # Simulate watcher detecting the file
            watcher.event_handler._queue_event(FileEventType.CREATED, str(image_path))

            # Engine should be able to process the queued event
            assert not event_queue.empty()
            file_event = event_queue.get()

            await sync_engine.process_file_event(file_event)

            # Verify processing occurred
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.integration
    def test_configuration_integration(self, temp_photos_structure):
        """Test that configuration is properly used across components."""
        config = SyncConfig(
            photos_base_path=temp_photos_structure,
            supported_extensions={".jpg", ".png"},
            max_batch_size=5,
            event_debounce_delay=0.5,
        )

        # Test that watcher uses config correctly
        event_queue = Queue()

        with patch("pgs_sync.watcher.sync_config", config):
            event_handler = PhotoDirectoryEventHandler(event_queue)

            # Test supported file detection
            assert event_handler._is_supported_file("/test/image.jpg")
            assert event_handler._is_supported_file("/test/image.png")
            assert not event_handler._is_supported_file("/test/image.gif")

            # Test category extraction
            category = event_handler._extract_category_from_path(temp_photos_structure / "landscapes" / "test.jpg")
            assert category == "landscapes"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_utility_functions_integration(self, temp_photos_structure):
        """Test integration of utility functions with real files."""
        # Create test image with specific properties
        image_path = temp_photos_structure / "portraits" / "IMG_20230615_sunset_beach.jpg"
        test_image = Image.new("RGB", (1920, 1080), color="yellow")
        test_image.save(image_path, "JPEG")

        # Test metadata extraction
        metadata = extract_image_metadata(image_path)
        assert metadata.width == 1920
        assert metadata.height == 1080
        assert metadata.file_size > 0
        assert metadata.file_modified_at is not None

        # Test title generation
        title = generate_title_from_filename(image_path.name)
        # Should remove IMG prefix and timestamp
        assert "IMG" not in title
        assert "2023" not in title
        assert title != ""
        # Should contain the descriptive parts
        assert "Sunset" in title
        assert "Beach" in title
