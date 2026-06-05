from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import AuditEventType, AuditLog, Complaint, ComplaintReason, ComplaintStatus, Profile
from app.services.limit_service import DailyAction, LimitService


class ComplaintService:
    def __init__(self, session: AsyncSession, settings: Settings, limit_service: LimitService) -> None:
        self.session = session
        self.settings = settings
        self.limit_service = limit_service

    async def create(
        self,
        from_profile_id: int,
        to_profile_id: int,
        reason: ComplaintReason,
        *,
        comment: str | None = None,
    ) -> Complaint:
        if from_profile_id == to_profile_id:
            raise ValueError("Нельзя пожаловаться на свою анкету.")
        await self.limit_service.increment(from_profile_id, DailyAction.COMPLAINT)

        complaint = Complaint(
            from_profile_id=from_profile_id,
            to_profile_id=to_profile_id,
            reason=reason,
            comment=(comment or "").strip()[:500] or None,
        )
        self.session.add(complaint)
        self.session.add(
            AuditLog(
                event_type=AuditEventType.COMPLAINT_CREATED,
                profile_id=from_profile_id,
                payload={"to_profile_id": to_profile_id, "reason": reason.value},
            )
        )
        await self.session.flush()
        await self._auto_hide_if_needed(to_profile_id)
        return complaint

    async def _auto_hide_if_needed(self, profile_id: int) -> None:
        count = int(
            await self.session.scalar(
                select(func.count(Complaint.id)).where(
                    Complaint.to_profile_id == profile_id,
                    Complaint.status.in_([ComplaintStatus.NEW, ComplaintStatus.IN_PROGRESS]),
                )
            )
            or 0
        )
        if count >= self.settings.complaint_auto_hide_threshold:
            profile = await self.session.get(Profile, profile_id)
            if profile is not None:
                profile.is_hidden = True
                await self.session.flush()

