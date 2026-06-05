from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Block
from app.services.limit_service import LimitService
from app.services.valentine_service import ValentineService
from tests.factories import create_city, create_profile


async def test_valentine_cannot_be_sent_between_blocked_profiles(session: AsyncSession, settings) -> None:
    city = await create_city(session)
    sender = await create_profile(session, telegram_id=1, city=city)
    target = await create_profile(session, telegram_id=2, city=city)
    session.add(Block(blocker_profile_id=target.id, blocked_profile_id=sender.id))
    await session.flush()

    service = ValentineService(session, settings, LimitService(session, settings))

    with pytest.raises(ValueError, match="заблокированному"):
        await service.send(sender.id, target.id, message="Привет")
