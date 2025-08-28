"""Utility functions for image processing and sync operations."""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from pgs_sync.sync_types import ImageMetadata

logger = logging.getLogger(__name__)


def extract_image_metadata(file_path: Path) -> ImageMetadata:
    """Extract basic metadata from an image file.

    Args:
        file_path: Path to the image file

    Returns:
        ImageMetadata with file size, dimensions, and modification time

    Raises:
        OSError: If file cannot be accessed
        Exception: If image cannot be processed
    """
    stat = file_path.stat()
    file_size = stat.st_size
    file_modified_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

    try:
        with Image.open(file_path) as img:
            width, height = img.size
    except Exception as e:
        # Some raw formats may not be supported by Pillow
        # For raw files or unsupported formats, we'll just store None for dimensions
        logger.debug(f"Could not extract dimensions from {file_path}: {e}")
        width, height = None, None

    return ImageMetadata(file_size=file_size, width=width, height=height, file_modified_at=file_modified_at)


def generate_title_from_filename(filename: str) -> str:
    """Generate a human-readable title from a filename.

    Args:
        filename: The original filename (with or without extension)

    Returns:
        A cleaned-up title suitable for display
    """
    name = Path(filename).stem

    # Remove common photo prefixes (case sensitive - uppercase are camera prefixes)
    name = re.sub("^(IMG|DSC|DSCN|P|PIC|PHOTO|IMAGE)[-_]", "", name)

    # Remove timestamp patterns that look like dates (YYYYMMDD, YYYY-MM-DD, etc.)
    # Remove 8-digit date patterns like 20230615
    name = re.sub(r"[-_]?20\d{6}[-_]?", "_", name)
    # Remove hyphen/underscore separated date patterns like 2023-06-15 or 2023_06_15
    name = re.sub(r"[-_]?20\d{2}[-_](0[1-9]|1[0-2])[-_](0[1-9]|[12]\d|3[01])[-_]?", "_", name)

    # Remove time patterns that look like HHMMSS (only valid time ranges)
    name = re.sub(r"[-_]?([01]\d|2[0-3])[-_:]?([0-5]\d)[-_:]?([0-5]\d)[-_]?", "_", name)

    # Remove sequential numbers at start or end (only if clearly separated)
    name = re.sub(r"^[-_]?\d{1,4}[-_]", "", name)
    name = re.sub(r"[-_]\d{1,4}$", "", name)

    # Replace underscores and hyphens with spaces
    name = re.sub(r"[-_]+", " ", name)

    # Clean up multiple spaces
    name = re.sub(r"\s+", " ", name)

    # Capitalize words
    name = name.strip().title()

    # If we ended up with an empty string, use the original stem
    if not name:
        name = Path(filename).stem.replace("_", " ").replace("-", " ").title()

    return name


def is_supported_image_file(file_path: Path, supported_extensions: set[str]) -> bool:
    """Check if a file is a supported image format.

    Args:
        file_path: Path to check
        supported_extensions: Set of supported file extensions

    Returns:
        True if the file extension is supported
    """
    return file_path.suffix.lower() in supported_extensions
