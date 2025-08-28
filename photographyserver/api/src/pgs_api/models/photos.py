from datetime import datetime
from pathlib import Path

from pydantic import field_validator

from pgs_api.models._base import SQLModel


class Photo(SQLModel):
    """Photo model for API responses."""

    id: str

    filename: str
    file_path: Path
    category: str

    title: str | None = None
    file_size: int
    width: int | None = None
    height: int | None = None

    created_at: datetime
    updated_at: datetime
    file_modified_at: datetime

    @classmethod
    @field_validator("file_path", mode="before")
    def _to_path(cls, value: str) -> Path:
        # TODO: Can this be __to_path?
        """Convert file_path string to a Path object."""
        if isinstance(value, Path):
            return value
        return Path(value)
