"""Type definitions for the sync worker."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum, auto
from pathlib import Path


class FileEventType(StrEnum):
    """Types of file system events."""

    CREATED = auto()
    MODIFIED = auto()
    DELETED = auto()
    MOVED = auto()


@dataclass(frozen=True)
class FileEvent:
    """Represents a file system event for processing."""

    event_type: FileEventType
    file_path: Path
    category: str
    timestamp: datetime


@dataclass(frozen=True)
class SyncStats:
    """Statistics for sync operations."""

    files_scanned: int
    files_added: int
    files_updated: int
    files_removed: int
    errors: int


@dataclass(frozen=True)
class ImageMetadata:
    """Container for extracted image metadata."""

    file_size: int
    width: int | None
    height: int | None
    file_modified_at: datetime


@dataclass(frozen=True)
class WorkerStats:
    """Statistics for the sync worker."""

    uptime_seconds: int
    files_processed_today: int
    files_added_today: int
    files_updated_today: int
    files_removed_today: int
    pending_events: int
    processed_events: int
    failed_events: int
    last_sync: datetime | None
    last_full_sync: datetime | None
    average_processing_time_ms: float
