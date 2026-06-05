from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Match


class MatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_pair(self, profile_a_id: int, profile_b_id: int) -> Match | None:
        first, second = sorted((profile_a_id, profile_b_id))
        return await self.session.scalar(
            select(Match).where(Match.profile1_id == first, Match.profile2_id == second)
        )

