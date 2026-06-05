from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ComplaintReason
from app.services.complaint_service import ComplaintService
from app.services.limit_service import LimitService
from tests.factories import create_city, create_profile


async def test_complaints_auto_hide_profile_after_threshold(session: AsyncSession, settings) -> None:
    settings.complaint_auto_hide_threshold = 2
    city = await create_city(session)
    target = await create_profile(session, telegram_id=100, city=city)
    first_reporter = await create_profile(session, telegram_id=1, city=city)
    second_reporter = await create_profile(session, telegram_id=2, city=city)
    service = ComplaintService(session, settings, LimitService(session, settings))

    await service.create(first_reporter.id, target.id, ComplaintReason.SPAM)
    assert not target.is_hidden

    await service.create(second_reporter.id, target.id, ComplaintReason.FAKE)
    assert target.is_hidden
