from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryStats:
    """Category information with photo count and latest photo timestamp."""

    name: str
    photo_count: int
    latest_photo: str | None
