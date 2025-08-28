"""Shared test fixtures and configuration for pgs_sync tests."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from pgs_sync.config import SyncConfig
from pgs_sync.sync_types import FileEvent, FileEventType, ImageMetadata, SyncStats


@pytest.fixture
def mock_config() -> SyncConfig:
    """Create a mock sync configuration for testing."""
    return SyncConfig(
        db_host="test_host",
        db_port=5432,
        db_name="test_db",
        db_user="test_user",
        db_password="test_password",
        photos_base_path=Path("/test/photos"),
        supported_extensions={".jpg", ".jpeg", ".png", ".gif"},
        initial_sync_on_startup=False,
        periodic_sync_interval=3600,
        event_debounce_delay=1.0,
        max_batch_size=10,
        retry_attempts=3,
        retry_delay=1.0,
        health_check_port=8001,
        health_check_host="localhost",
        log_level="DEBUG",
    )


@pytest.fixture
def temp_photos_dir() -> Generator[Path, None, None]:
    """Create a temporary directory structure for testing photos."""
    with tempfile.TemporaryDirectory() as temp_dir:
        photos_path = Path(temp_dir) / "photos"
        photos_path.mkdir()

        # Create some category directories
        (photos_path / "landscapes").mkdir()
        (photos_path / "portraits").mkdir()
        (photos_path / "events").mkdir()

        yield photos_path


@pytest.fixture
def sample_image_file(temp_photos_dir: Path) -> Path:
    """Create a sample image file for testing."""
    image_path = temp_photos_dir / "landscapes" / "test_image.jpg"

    # Create a simple 100x100 RGB image
    image = Image.new("RGB", (100, 100), color="red")
    image.save(image_path, "JPEG")

    return image_path


@pytest.fixture
def sample_file_events() -> list[FileEvent]:
    """Create sample file events for testing."""
    base_path = Path("/test/photos")
    timestamp = datetime.now(timezone.utc)

    return [
        FileEvent(
            event_type=FileEventType.CREATED,
            file_path=base_path / "landscapes" / "sunset.jpg",
            category="landscapes",
            timestamp=timestamp,
        ),
        FileEvent(
            event_type=FileEventType.MODIFIED,
            file_path=base_path / "portraits" / "person.jpg",
            category="portraits",
            timestamp=timestamp,
        ),
        FileEvent(
            event_type=FileEventType.DELETED,
            file_path=base_path / "events" / "party.jpg",
            category="events",
            timestamp=timestamp,
        ),
    ]


@pytest.fixture
def sample_sync_stats() -> SyncStats:
    """Create sample sync statistics for testing."""
    return SyncStats(
        files_scanned=100,
        files_added=10,
        files_updated=5,
        files_removed=2,
        errors=1,
    )


@pytest.fixture
def sample_image_metadata() -> ImageMetadata:
    """Create sample image metadata for testing."""
    return ImageMetadata(
        file_size=1024000,
        width=1920,
        height=1080,
        file_modified_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Create a mock database session for testing."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def mock_db_session_factory(mock_db_session: AsyncMock):
    """Create a mock database session factory for testing."""

    def factory():
        # Create an async context manager that returns the mock session
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_db_session)
        async_context.__aexit__ = AsyncMock(return_value=None)
        return async_context

    return factory


@pytest.fixture
def event_queue() -> Queue[FileEvent]:
    """Create an event queue for testing."""
    return Queue()


@pytest.fixture
def mock_observer() -> MagicMock:
    """Create a mock watchdog observer for testing."""
    observer = MagicMock()
    observer.is_alive.return_value = True
    observer.start = MagicMock()
    observer.stop = MagicMock()
    observer.join = MagicMock()
    observer.schedule = MagicMock()
    return observer


@pytest.fixture
def mock_db_manager() -> MagicMock:
    """Create a mock database manager for testing."""
    db_manager = MagicMock()
    db_manager.health_check = AsyncMock(return_value={"status": "healthy"})
    db_manager.session_factory = MagicMock()
    return db_manager


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    """Clean environment variables before each test."""
    # Clear any existing SYNC_ environment variables
    for key in list(monkeypatch._setattr):
        if key.startswith("SYNC_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def mock_pil_image():
    """Create a mock PIL Image for testing."""
    image = MagicMock()
    image.size = (1920, 1080)
    image.__enter__ = MagicMock(return_value=image)
    image.__exit__ = MagicMock(return_value=None)
    return image


class AsyncContextManagerMock:
    """Helper class for creating async context manager mocks."""

    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def async_context_manager():
    """Factory for creating async context manager mocks."""
    return AsyncContextManagerMock
