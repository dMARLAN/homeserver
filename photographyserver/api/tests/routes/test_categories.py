from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from pgs_api.routes.categories import list_categories, list_photos_in_category
from pgs_api.services.categories import CategoriesService
from pgs_api.types.category import CategoryStats
from pgs_api.models import Photo


class TestListCategories:
    @pytest.mark.asyncio
    async def test_list_categories_success(self) -> None:
        expected_categories = [
            CategoryStats(name="nature", photo_count=5, latest_photo="2024-01-01T00:00:00"),
            CategoryStats(name="portraits", photo_count=3, latest_photo="2024-01-02T00:00:00"),
        ]

        mock_service = Mock(spec=CategoriesService)
        mock_service.list_categories = AsyncMock(return_value=expected_categories)

        result = await list_categories(categories_service=mock_service)

        assert result == expected_categories
        mock_service.list_categories.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_categories_empty(self) -> None:
        mock_service = Mock(spec=CategoriesService)
        mock_service.list_categories = AsyncMock(return_value=[])

        result = await list_categories(categories_service=mock_service)

        assert result == []
        mock_service.list_categories.assert_called_once()


class TestListPhotosInCategory:
    @pytest.mark.asyncio
    async def test_list_photos_in_category_success(self) -> None:
        category = "nature"
        expected_photos = [
            Photo(
                id="photo1",
                filename="sunset.jpg",
                file_path=Path("/photos/nature/sunset.jpg"),
                category="nature",
                title="Beautiful Sunset",
                file_size=2621440,
                width=1920,
                height=1080,
                created_at=datetime(2024, 1, 1),
                updated_at=datetime(2024, 1, 1),
                file_modified_at=datetime(2024, 1, 1),
            )
        ]

        mock_service = Mock(spec=CategoriesService)
        mock_service.get_photos_in_category = AsyncMock(return_value=expected_photos)

        result = await list_photos_in_category(category, categories_service=mock_service)

        assert result == expected_photos
        mock_service.get_photos_in_category.assert_called_once_with(category)

    @pytest.mark.asyncio
    async def test_list_photos_in_category_not_found(self) -> None:
        category = "nonexistent"

        mock_service = Mock(spec=CategoriesService)
        mock_service.get_photos_in_category = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await list_photos_in_category(category, categories_service=mock_service)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == f"Category '{category}' not found or empty"
        mock_service.get_photos_in_category.assert_called_once_with(category)

    @pytest.mark.asyncio
    async def test_list_photos_in_category_empty(self) -> None:
        category = "empty_category"

        mock_service = Mock(spec=CategoriesService)
        mock_service.get_photos_in_category = AsyncMock(return_value=[])

        with pytest.raises(HTTPException) as exc_info:
            await list_photos_in_category(category, categories_service=mock_service)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == f"Category '{category}' not found or empty"
        mock_service.get_photos_in_category.assert_called_once_with(category)
