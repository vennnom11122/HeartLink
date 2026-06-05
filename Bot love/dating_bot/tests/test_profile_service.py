from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Photo
from app.services.profile_service import ProfileService
from tests.factories import create_city, create_profile


async def test_delete_main_photo_promotes_next_photo_and_reorders(session: AsyncSession) -> None:
    city = await create_city(session)
    profile = await create_profile(session, telegram_id=1, city=city)
    service = ProfileService(session)
    await service.add_photo(profile.id, "file-2", "unique-2")

    photos_before = list(
        (
            await session.scalars(
                select(Photo).where(Photo.profile_id == profile.id).order_by(Photo.position)
            )
        ).all()
    )
    assert len(photos_before) == 2
    assert photos_before[0].is_main

    await service.delete_photo(profile.id, photos_before[0].id)

    photos_after = list(
        (
            await session.scalars(
                select(Photo).where(Photo.profile_id == profile.id).order_by(Photo.position)
            )
        ).all()
    )
    assert len(photos_after) == 1
    assert photos_after[0].is_main
    assert photos_after[0].position == 1
