from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.responses import FileResponse

from pgs_api.routes.photos import serve_photo_file_info
from pgs_api.services.photos import PhotosService, PhotoFileInfo


class TestServePhotoFile:
    @pytest.mark.asyncio
    async def test_serve_photo_file_success(self) -> None:
        photo_id = "photo123"
        test_path = Path("/photos/test.jpg")
        photo_file_info = PhotoFileInfo(
            file_path=test_path,
            media_type="image/jpeg",
            filename="test.jpg",
        )

        mock_service = Mock(spec=PhotosService)
        mock_service.get_photo_file_info = AsyncMock(return_value=photo_file_info)

        # Mock the file existence check
        with patch("pathlib.Path.exists", return_value=True):
            result = await serve_photo_file_info(photo_id, photo_service=mock_service)

            assert isinstance(result, FileResponse)
            mock_service.get_photo_file_info.assert_called_once_with(photo_id)

    @pytest.mark.asyncio
    async def test_serve_photo_file_photo_not_found(self) -> None:
        photo_id = "nonexistent"

        mock_service = Mock(spec=PhotosService)
        mock_service.get_photo_file_info = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await serve_photo_file_info(photo_id, photo_service=mock_service)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Photo not found"
        mock_service.get_photo_file_info.assert_called_once_with(photo_id)

    @pytest.mark.asyncio
    async def test_serve_photo_file_file_not_on_disk(self) -> None:
        photo_id = "photo123"
        test_path = Path("/photos/nonexistent.jpg")
        photo_file_info = PhotoFileInfo(
            file_path=test_path,
            media_type="image/jpeg",
            filename="nonexistent.jpg",
        )

        mock_service = Mock(spec=PhotosService)
        mock_service.get_photo_file_info = AsyncMock(return_value=photo_file_info)

        # Mock the file existence check to return False
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await serve_photo_file_info(photo_id, photo_service=mock_service)

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Photo file not found on disk"
            mock_service.get_photo_file_info.assert_called_once_with(photo_id)
