from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pgs_db.database import db_manager
from pgs_db.models.photos import PLPhoto


class PhotosRepository:
    def __init__(self, session: AsyncSession = Depends(db_manager.get_session)) -> None:
        self.__session = session

    async def get_photo_by_id(self, photo_id: str) -> PLPhoto | None:
        """Get a photo by ID."""
        result = await self.__session.execute(select(PLPhoto).where(PLPhoto.id == photo_id))
        return result.scalar_one_or_none()
