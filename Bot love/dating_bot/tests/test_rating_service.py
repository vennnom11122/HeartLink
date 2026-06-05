from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Like, LikeSource, Match, Rating
from app.services.limit_service import LimitService
from app.services.rating_service import RatingService
from tests.factories import create_city, create_profile


async def test_rating_is_upserted_and_recalculates_average(session: AsyncSession, settings) -> None:
    city = await create_city(session)
    sender = await create_profile(session, telegram_id=1, city=city)
    target = await create_profile(session, telegram_id=2, city=city)

    service = RatingService(session, LimitService(session, settings))
    first = await service.rate_profile(sender.id, target.id, 8)
    second = await service.rate_profile(sender.id, target.id, 6)

    ratings_count = await session.scalar(select(Rating).where(Rating.from_profile_id == sender.id))
    assert ratings_count is not None
    assert first.rating_count == 1
    assert second.rating_count == 1
    assert str(second.rating_avg) == "6.00"


async def test_mutual_high_rating_creates_match(session: AsyncSession, settings) -> None:
    city = await create_city(session)
    first = await create_profile(session, telegram_id=1, city=city)
    second = await create_profile(session, telegram_id=2, city=city)

    service = RatingService(session, LimitService(session, settings))
    result_one = await service.rate_profile(first.id, second.id, 8)
    result_two = await service.rate_profile(second.id, first.id, 9)

    assert result_one.match_result is not None
    assert not result_one.match_result.is_mutual
    assert result_two.match_result is not None
    assert result_two.match_result.created
    assert await session.scalar(select(Like).where(Like.from_profile_id == first.id)) is not None
    assert await session.scalar(select(Match)) is not None


async def test_lowering_high_rating_removes_rating_like_and_deactivates_match(
    session: AsyncSession,
    settings,
) -> None:
    city = await create_city(session)
    first = await create_profile(session, telegram_id=1, city=city)
    second = await create_profile(session, telegram_id=2, city=city)

    service = RatingService(session, LimitService(session, settings))
    await service.rate_profile(first.id, second.id, 8)
    await service.rate_profile(second.id, first.id, 9)
    await service.rate_profile(first.id, second.id, 4)

    stale_like = await session.scalar(
        select(Like).where(
            Like.from_profile_id == first.id,
            Like.to_profile_id == second.id,
            Like.source == LikeSource.RATING,
        )
    )
    match = await session.scalar(select(Match))

    assert stale_like is None
    assert match is not None
    assert not match.is_active
