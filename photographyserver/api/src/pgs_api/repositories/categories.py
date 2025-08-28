from typing import Sequence

from fastapi import Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from pgs_api.types.category import CategoryStats
from pgs_db.database import db_manager
from pgs_db.models.photos import PLPhoto


class CategoriesRepository:
    def __init__(self, session: AsyncSession = Depends(db_manager.get_session)) -> None:
        self.__session = session

    async def get_categories_with_stats(self) -> Sequence[CategoryStats]:
        """Get all categories with photo counts and latest photo timestamp."""
        result = await self.__session.execute(
            select(
                PLPhoto.category,
                func.count(PLPhoto.id).label("photo_count"),
                func.max(PLPhoto.created_at).label("latest_photo"),
            )
            .group_by(PLPhoto.category)
            .order_by(PLPhoto.category)
        )

        return [
            CategoryStats(
                name=row[0],
                photo_count=row[1],
                latest_photo=row[2].isoformat() if row[2] else None,
            )
            for row in result.all()
        ]

    async def get_photos_by_category(self, category: str) -> Sequence[PLPhoto]:
        """Get all photos in a specific category."""
        result = await self.__session.execute(
            select(PLPhoto).where(PLPhoto.category == category).order_by(PLPhoto.created_at.desc())
        )
        return result.scalars().all()
