from typing import Sequence

from fastapi import APIRouter, HTTPException, Depends
from starlette.status import HTTP_200_OK

from pgs_api.models import Photo
from pgs_api.services.categories import CategoriesService
from pgs_api.types.category import CategoryStats

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=Sequence[CategoryStats], status_code=HTTP_200_OK)
async def list_categories(
    categories_service: CategoriesService = Depends(CategoriesService),
) -> Sequence[CategoryStats]:
    """List all available photo categories."""
    return await categories_service.list_categories()


@router.get("/{category}", response_model=Sequence[Photo], status_code=HTTP_200_OK)
async def list_photos_in_category(
    category: str,
    categories_service: CategoriesService = Depends(CategoriesService),
) -> Sequence[Photo]:
    """List all photos in a specific category."""
    photos = await categories_service.get_photos_in_category(category)

    if not photos:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found or empty")

    return photos
