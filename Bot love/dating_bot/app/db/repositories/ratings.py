from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Rating


class RatingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_pair(self, from_profile_id: int, to_profile_id: int) -> Rating | None:
        return await self.session.scalar(
            select(Rating).where(
                Rating.from_profile_id == from_profile_id,
                Rating.to_profile_id == to_profile_id,
            )
        )

