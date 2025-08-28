from dataclasses import dataclass
from pathlib import Path
from typing import Final

from fastapi import Depends

from pgs_api.models import Photo
from pgs_api.repositories.photos import PhotosRepository


@dataclass(frozen=True)
class PhotoFileInfo:
    """Photo file information for serving the file."""

    file_path: Path
    media_type: str
    filename: str


class PhotosService:
    __MEDIA_TYPE_MAP: Final[dict[str, str]] = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
    }

    def __init__(self, photos_repository: PhotosRepository = Depends(PhotosRepository)) -> None:
        self.__repository = photos_repository

    async def get_photo_file_info(self, photo_id: str) -> PhotoFileInfo | None:
        """Get photo file information for serving the file."""
        if photo := await self.__repository.get_photo_by_id(photo_id):
            photo = Photo.model_validate(photo)

            if not photo.file_path or str(photo.file_path) == ".":
                return None

            file_extension = Path(photo.filename).suffix.lower()
            return PhotoFileInfo(
                file_path=photo.file_path,
                media_type=self.__MEDIA_TYPE_MAP.get(file_extension, "application/octet-stream"),
                filename=photo.filename,
            )
        return None
