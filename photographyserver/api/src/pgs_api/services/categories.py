from typing import Sequence

from fastapi import Depends

from pgs_api.models import Photo
from pgs_api.repositories.categories import CategoriesRepository
from pgs_api.types.category import CategoryStats


class CategoriesService:
    def __init__(self, photos_repository: CategoriesRepository = Depends(CategoriesRepository)) -> None:
        self.__repository = photos_repository

    async def list_categories(self) -> Sequence[CategoryStats]:
        """Get all available photo categories with counts and latest photo timestamp."""
        return await self.__repository.get_categories_with_stats()

    async def get_photos_in_category(self, category: str) -> Sequence[Photo] | None:
        """Get all photos in a specific category."""
        photos = await self.__repository.get_photos_by_category(category)

        if not photos:
            return None

        return [Photo.model_validate(photo) for photo in photos]
