from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Block, Complaint, ComplaintReason, Gender, LookingForGender
from app.services.limit_service import LimitService
from app.services.search_service import SearchService
from tests.factories import create_city, create_profile


async def test_search_excludes_profiles_with_rating_below_five_after_five_votes(session: AsyncSession, settings) -> None:
    city = await create_city(session)
    viewer = await create_profile(
        session,
        telegram_id=1,
        city=city,
        gender=Gender.MALE,
        looking_for_gender=LookingForGender.FEMALE,
    )
    low_rated = await create_profile(
        session,
        telegram_id=2,
        city=city,
        gender=Gender.FEMALE,
        rating_avg=4.9,
        rating_count=5,
    )
    good = await create_profile(
        session,
        telegram_id=3,
        city=city,
        gender=Gender.FEMALE,
        rating_avg=5.1,
        rating_count=5,
    )

    service = SearchService(session, settings, LimitService(session, settings))
    found = await service.get_next_profile_for_viewer(viewer.id)

    assert found is not None
    assert found.id == good.id
    assert found.id != low_rated.id


async def test_search_allows_new_profiles_before_enough_ratings(session: AsyncSession, settings) -> None:
    city = await create_city(session)
    viewer = await create_profile(session, telegram_id=1, city=city, gender=Gender.MALE)
    new_profile = await create_profile(
        session,
        telegram_id=2,
        city=city,
        gender=Gender.FEMALE,
        rating_avg=3.0,
        rating_count=2,
    )

    service = SearchService(session, settings, LimitService(session, settings))
    found = await service.get_next_profile_for_viewer(viewer.id)

    assert found is not None
    assert found.id == new_profile.id


async def test_search_excludes_blocked_profiles(session: AsyncSession, settings) -> None:
    city = await create_city(session)
    viewer = await create_profile(session, telegram_id=1, city=city, gender=Gender.MALE)
    blocked = await create_profile(session, telegram_id=2, city=city, gender=Gender.FEMALE)
    allowed = await create_profile(session, telegram_id=3, city=city, gender=Gender.FEMALE)
    session.add(Block(blocker_profile_id=viewer.id, blocked_profile_id=blocked.id))
    await session.flush()

    service = SearchService(session, settings, LimitService(session, settings))
    found = await service.get_next_profile_for_viewer(viewer.id)

    assert found is not None
    assert found.id == allowed.id


async def test_search_excludes_open_complaints_from_viewer(session: AsyncSession, settings) -> None:
    city = await create_city(session)
    viewer = await create_profile(session, telegram_id=1, city=city, gender=Gender.MALE)
    reported = await create_profile(session, telegram_id=2, city=city, gender=Gender.FEMALE)
    allowed = await create_profile(session, telegram_id=3, city=city, gender=Gender.FEMALE)
    session.add(
        Complaint(
            from_profile_id=viewer.id,
            to_profile_id=reported.id,
            reason=ComplaintReason.SPAM,
        )
    )
    await session.flush()

    service = SearchService(session, settings, LimitService(session, settings))
    found = await service.get_next_profile_for_viewer(viewer.id)

    assert found is not None
    assert found.id == allowed.id


async def test_search_respects_candidate_age_preferences(session: AsyncSession, settings) -> None:
    city = await create_city(session)
    viewer = await create_profile(session, telegram_id=1, city=city, gender=Gender.MALE, age=40)
    unsuitable = await create_profile(
        session,
        telegram_id=2,
        city=city,
        gender=Gender.FEMALE,
        max_age_preference=35,
    )
    allowed = await create_profile(
        session,
        telegram_id=3,
        city=city,
        gender=Gender.FEMALE,
        max_age_preference=45,
    )

    service = SearchService(session, settings, LimitService(session, settings))
    found = await service.get_next_profile_for_viewer(viewer.id)

    assert found is not None
    assert found.id == allowed.id
    assert found.id != unsuitable.id
