from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import AuditEventType, AuditLog, Block, LikeSource, Valentine, ValentineStatus
from app.services.limit_service import DailyAction, LimitService
from app.services.match_service import MatchResult, MatchService
from app.utils.validators import validate_valentine_message


class ValentineService:
    def __init__(self, session: AsyncSession, settings: Settings, limit_service: LimitService) -> None:
        self.session = session
        self.settings = settings
        self.limit_service = limit_service
        self.match_service = MatchService(session)

    async def send(
        self,
        from_profile_id: int,
        to_profile_id: int,
        *,
        message: str | None = None,
        is_anonymous: bool = False,
    ) -> Valentine:
        if from_profile_id == to_profile_id:
            raise ValueError("Нельзя отправить валентинку самому себе.")
        if await self._has_block_between(from_profile_id, to_profile_id):
            raise ValueError("Нельзя отправить валентинку заблокированному пользователю.")
        ok, error = validate_valentine_message(message or "")
        if not ok:
            raise ValueError(error or "Некорректное сообщение.")

        await self.limit_service.increment(from_profile_id, DailyAction.VALENTINE)

        valentine = Valentine(
            from_profile_id=from_profile_id,
            to_profile_id=to_profile_id,
            message=(message or "").strip() or None,
            is_anonymous=is_anonymous,
        )
        self.session.add(valentine)
        self.session.add(
            AuditLog(
                event_type=AuditEventType.VALENTINE_SENT,
                profile_id=from_profile_id,
                payload={"to_profile_id": to_profile_id, "is_anonymous": is_anonymous},
            )
        )
        await self.session.flush()
        return valentine

    async def open(self, valentine_id: int, opener_profile_id: int) -> Valentine:
        valentine = await self.session.get(Valentine, valentine_id)
        if valentine is None or valentine.to_profile_id != opener_profile_id:
            raise ValueError("Валентинка не найдена.")
        if valentine.status == ValentineStatus.EXPIRED:
            raise ValueError("Срок действия валентинки истёк.")
        if valentine.status == ValentineStatus.SENT:
            valentine.status = ValentineStatus.VIEWED
            valentine.opened_at = datetime.now(timezone.utc)
        await self.session.flush()
        return valentine

    async def accept(self, valentine_id: int, accepter_profile_id: int) -> MatchResult:
        valentine = await self.open(valentine_id, accepter_profile_id)
        if valentine.status not in (ValentineStatus.VIEWED, ValentineStatus.SENT):
            raise ValueError("Эту валентинку уже обработали.")

        valentine.status = ValentineStatus.ACCEPTED
        await self.match_service.ensure_like(valentine.from_profile_id, valentine.to_profile_id, LikeSource.VALENTINE)
        result = await self.match_service.ensure_like(
            valentine.to_profile_id,
            valentine.from_profile_id,
            LikeSource.DIRECT_LIKE,
        )
        await self.session.flush()
        return result

    async def reject(self, valentine_id: int, profile_id: int) -> Valentine:
        valentine = await self.open(valentine_id, profile_id)
        if valentine.status not in (ValentineStatus.VIEWED, ValentineStatus.SENT):
            raise ValueError("Эту валентинку уже обработали.")
        valentine.status = ValentineStatus.REJECTED
        await self.session.flush()
        return valentine

    async def expire_old(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.settings.valentine_ttl_days)
        result = await self.session.execute(
            update(Valentine)
            .where(Valentine.status.in_([ValentineStatus.SENT, ValentineStatus.VIEWED]), Valentine.created_at < cutoff)
            .values(status=ValentineStatus.EXPIRED)
        )
        await self.session.flush()
        return int(result.rowcount or 0)

    async def pending_for_profile(self, profile_id: int) -> list[Valentine]:
        return list(
            (
                await self.session.scalars(
                    select(Valentine)
                    .where(
                        Valentine.to_profile_id == profile_id,
                        Valentine.status.in_([ValentineStatus.SENT, ValentineStatus.VIEWED]),
                    )
                    .order_by(Valentine.created_at.desc())
                )
            ).all()
        )

    async def _has_block_between(self, profile_a_id: int, profile_b_id: int) -> bool:
        block_id = await self.session.scalar(
            select(Block.id).where(
                or_(
                    and_(Block.blocker_profile_id == profile_a_id, Block.blocked_profile_id == profile_b_id),
                    and_(Block.blocker_profile_id == profile_b_id, Block.blocked_profile_id == profile_a_id),
                )
            )
        )
        return block_id is not None
