from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEventType, AuditLog, Block


class BlockService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def block(self, blocker_profile_id: int, blocked_profile_id: int) -> Block:
        if blocker_profile_id == blocked_profile_id:
            raise ValueError("Нельзя заблокировать самого себя.")
        block = await self.session.scalar(
            select(Block).where(
                Block.blocker_profile_id == blocker_profile_id,
                Block.blocked_profile_id == blocked_profile_id,
            )
        )
        if block is None:
            block = Block(blocker_profile_id=blocker_profile_id, blocked_profile_id=blocked_profile_id)
            self.session.add(block)
            self.session.add(
                AuditLog(
                    event_type=AuditEventType.PROFILE_BLOCKED,
                    profile_id=blocker_profile_id,
                    payload={"blocked_profile_id": blocked_profile_id},
                )
            )
            await self.session.flush()
        return block

