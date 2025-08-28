from unittest.mock import AsyncMock, Mock

import pytest

from pgs_api.repositories.categories import CategoriesRepository
from pgs_api.services.categories import CategoriesService
from pgs_api.types.category import CategoryStats
from pgs_api.models import Photo


class TestCategoriesService:
    @pytest.mark.asyncio
    async def test_list_categories_success(self) -> None:
        mock_categories = [
            CategoryStats(name="nature", photo_count=5, latest_photo="2024-01-01T00:00:00"),
            CategoryStats(name="portraits", photo_count=3, latest_photo="2024-01-02T00:00:00"),
            CategoryStats(name="street", photo_count=2, latest_photo="2024-01-03T00:00:00"),
        ]

        mock_repository = Mock(spec=CategoriesRepository)
        mock_repository.get_categories_with_stats = AsyncMock(return_value=mock_categories)

        service = CategoriesService(photos_repository=mock_repository)
        result = await service.list_categories()

        assert len(result) == 3
        assert result[0].name == "nature"
        assert result[0].photo_count == 5
        assert result[0].latest_photo == "2024-01-01T00:00:00"
        assert result[1].name == "portraits"
        assert result[1].photo_count == 3
        assert result[1].latest_photo == "2024-01-02T00:00:00"
        assert result[2].name == "street"
        assert result[2].photo_count == 2
        assert result[2].latest_photo == "2024-01-03T00:00:00"
        mock_repository.get_categories_with_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_categories_empty(self) -> None:
        mock_repository = Mock(spec=CategoriesRepository)
        mock_repository.get_categories_with_stats = AsyncMock(return_value=[])

        service = CategoriesService(photos_repository=mock_repository)
        result = await service.list_categories()

        assert result == []
        mock_repository.get_categories_with_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_photos_in_category_success(self) -> None:
        category = "nature"
        mock_db_photo = Mock()
        mock_db_photo.id = "photo1"
        mock_db_photo.filename = "sunset.jpg"
        mock_db_photo.file_path = "/photos/nature/sunset.jpg"
        mock_db_photo.category = "nature"
        mock_db_photo.title = "Beautiful Sunset"
        mock_db_photo.file_size = 2621440
        mock_db_photo.width = 1920
        mock_db_photo.height = 1080
        mock_db_photo.created_at = "2024-01-01T00:00:00"
        mock_db_photo.updated_at = "2024-01-01T00:00:00"
        mock_db_photo.file_modified_at = "2024-01-01T00:00:00"

        mock_repository = Mock(spec=CategoriesRepository)
        mock_repository.get_photos_by_category = AsyncMock(return_value=[mock_db_photo])

        service = CategoriesService(photos_repository=mock_repository)
        result = await service.get_photos_in_category(category)

        assert result is not None
        assert len(result) == 1
        photo = result[0]
        assert isinstance(photo, Photo)
        assert photo.id == "photo1"
        assert photo.filename == "sunset.jpg"
        assert photo.category == "nature"

        mock_repository.get_photos_by_category.assert_called_once_with(category)

    @pytest.mark.asyncio
    async def test_get_photos_in_category_not_found(self) -> None:
        category = "nonexistent"

        mock_repository = Mock(spec=CategoriesRepository)
        mock_repository.get_photos_by_category = AsyncMock(return_value=[])

        service = CategoriesService(photos_repository=mock_repository)
        result = await service.get_photos_in_category(category)

        assert result is None
        mock_repository.get_photos_by_category.assert_called_once_with(category)

    @pytest.mark.asyncio
    async def test_get_photos_in_category_empty_list(self) -> None:
        category = "empty"

        mock_repository = Mock(spec=CategoriesRepository)
        mock_repository.get_photos_by_category = AsyncMock(return_value=None)

        service = CategoriesService(photos_repository=mock_repository)
        result = await service.get_photos_in_category(category)

        assert result is None
        mock_repository.get_photos_by_category.assert_called_once_with(category)

    @pytest.mark.asyncio
    async def test_get_photos_in_category_multiple_photos(self) -> None:
        category = "nature"

        mock_db_photo1 = Mock()
        mock_db_photo1.id = "photo1"
        mock_db_photo1.filename = "sunset.jpg"
        mock_db_photo1.file_path = "/photos/nature/sunset.jpg"
        mock_db_photo1.category = "nature"
        mock_db_photo1.title = "Sunset"
        mock_db_photo1.file_size = 2621440
        mock_db_photo1.width = 1920
        mock_db_photo1.height = 1080
        mock_db_photo1.created_at = "2024-01-01T00:00:00"
        mock_db_photo1.updated_at = "2024-01-01T00:00:00"
        mock_db_photo1.file_modified_at = "2024-01-01T00:00:00"

        mock_db_photo2 = Mock()
        mock_db_photo2.id = "photo2"
        mock_db_photo2.filename = "tree.jpg"
        mock_db_photo2.file_path = "/photos/nature/tree.jpg"
        mock_db_photo2.category = "nature"
        mock_db_photo2.title = "Old Tree"
        mock_db_photo2.file_size = 3355443
        mock_db_photo2.width = 1080
        mock_db_photo2.height = 1920
        mock_db_photo2.created_at = "2024-01-02T00:00:00"
        mock_db_photo2.updated_at = "2024-01-02T00:00:00"
        mock_db_photo2.file_modified_at = "2024-01-02T00:00:00"

        mock_repository = Mock(spec=CategoriesRepository)
        mock_repository.get_photos_by_category = AsyncMock(return_value=[mock_db_photo1, mock_db_photo2])

        service = CategoriesService(photos_repository=mock_repository)
        result = await service.get_photos_in_category(category)

        assert result is not None
        assert len(result) == 2
        assert result[0].id == "photo1"
        assert result[0].filename == "sunset.jpg"
        assert result[1].id == "photo2"
        assert result[1].filename == "tree.jpg"

        mock_repository.get_photos_by_category.assert_called_once_with(category)
