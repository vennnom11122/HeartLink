from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Valentine, ValentineStatus


class ValentineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def inbox(self, profile_id: int, *, status: ValentineStatus | None = None) -> list[Valentine]:
        stmt = select(Valentine).where(Valentine.to_profile_id == profile_id)
        if status is not None:
            stmt = stmt.where(Valentine.status == status)
        stmt = stmt.order_by(Valentine.created_at.desc())
        return list((await self.session.scalars(stmt)).all())

