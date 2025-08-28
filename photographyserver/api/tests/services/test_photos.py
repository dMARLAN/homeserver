from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from pgs_api.repositories.photos import PhotosRepository
from pgs_api.services.photos import PhotosService, PhotoFileInfo


class TestPhotosService:

    @pytest.mark.asyncio
    async def test_get_photo_file_info_success(self) -> None:
        photo_id = "photo123"
        test_path = "/photos/test.jpg"

        mock_db_photo = Mock()
        mock_db_photo.id = photo_id
        mock_db_photo.filename = "test.jpg"
        mock_db_photo.file_path = test_path
        mock_db_photo.category = "nature"
        mock_db_photo.title = "Test Photo"
        mock_db_photo.file_size = 2621440
        mock_db_photo.width = 1920
        mock_db_photo.height = 1080
        mock_db_photo.created_at = "2024-01-01T00:00:00"
        mock_db_photo.updated_at = "2024-01-01T00:00:00"
        mock_db_photo.file_modified_at = "2024-01-01T00:00:00"

        mock_repository = Mock(spec=PhotosRepository)
        mock_repository.get_photo_by_id = AsyncMock(return_value=mock_db_photo)

        service = PhotosService(photos_repository=mock_repository)
        result = await service.get_photo_file_info(photo_id)

        assert result is not None
        assert isinstance(result, PhotoFileInfo)
        assert result.file_path == Path(test_path)
        assert result.media_type == "image/jpeg"
        assert result.filename == "test.jpg"
        mock_repository.get_photo_by_id.assert_called_once_with(photo_id)

    @pytest.mark.asyncio
    async def test_get_photo_file_info_photo_not_found(self) -> None:
        photo_id = "nonexistent"

        mock_repository = Mock(spec=PhotosRepository)
        mock_repository.get_photo_by_id = AsyncMock(return_value=None)

        service = PhotosService(photos_repository=mock_repository)
        result = await service.get_photo_file_info(photo_id)

        assert result is None
        mock_repository.get_photo_by_id.assert_called_once_with(photo_id)

    @pytest.mark.asyncio
    async def test_get_photo_file_info_file_not_exists(self) -> None:
        photo_id = "photo123"
        test_path = ""

        mock_db_photo = Mock()
        mock_db_photo.id = photo_id
        mock_db_photo.filename = "test.jpg"
        mock_db_photo.file_path = test_path
        mock_db_photo.category = "nature"
        mock_db_photo.title = "Test Photo"
        mock_db_photo.file_size = 2621440
        mock_db_photo.width = 1920
        mock_db_photo.height = 1080
        mock_db_photo.created_at = "2024-01-01T00:00:00"
        mock_db_photo.updated_at = "2024-01-01T00:00:00"
        mock_db_photo.file_modified_at = "2024-01-01T00:00:00"

        mock_repository = Mock(spec=PhotosRepository)
        mock_repository.get_photo_by_id = AsyncMock(return_value=mock_db_photo)

        service = PhotosService(photos_repository=mock_repository)
        result = await service.get_photo_file_info(photo_id)

        assert result is None
        mock_repository.get_photo_by_id.assert_called_once_with(photo_id)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "extension, expected_media_type",
        [
            (".jpg", "image/jpeg"),
            (".jpeg", "image/jpeg"),
            (".png", "image/png"),
            (".webp", "image/webp"),
            (".gif", "image/gif"),
            (".bmp", "image/bmp"),
            (".tiff", "image/tiff"),
            (".tif", "image/tiff"),
            (".JPG", "image/jpeg"),  # Test case-insensitive
            (".PNG", "image/png"),  # Test case-insensitive
            (".xyz", "application/octet-stream"),  # Unknown extension
            ("", "application/octet-stream"),  # Empty extension
        ],
    )
    async def test_get_photo_file_info_different_media_types(self, extension: str, expected_media_type: str) -> None:
        photo_id = f"photo_{extension}"
        test_path = f"/photos/test{extension}"

        mock_db_photo = Mock()
        mock_db_photo.id = photo_id
        mock_db_photo.filename = f"test{extension}"
        mock_db_photo.file_path = test_path
        mock_db_photo.category = "nature"
        mock_db_photo.title = "Test Photo"
        mock_db_photo.file_size = 2621440
        mock_db_photo.width = 1920
        mock_db_photo.height = 1080
        mock_db_photo.created_at = "2024-01-01T00:00:00"
        mock_db_photo.updated_at = "2024-01-01T00:00:00"
        mock_db_photo.file_modified_at = "2024-01-01T00:00:00"

        mock_repository = Mock(spec=PhotosRepository)
        mock_repository.get_photo_by_id = AsyncMock(return_value=mock_db_photo)

        service = PhotosService(photos_repository=mock_repository)
        result = await service.get_photo_file_info(photo_id)

        assert result is not None
        assert result.media_type == expected_media_type
