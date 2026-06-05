from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEventType, AuditLog, LikeSource, Profile, Rating
from app.services.limit_service import DailyAction, LimitService
from app.services.match_service import MatchResult, MatchService
from app.utils.constants import LIKE_SCORE_MIN


@dataclass(frozen=True)
class RatingResult:
    rating: Rating
    rating_avg: Decimal
    rating_count: int
    match_result: MatchResult | None


class RatingService:
    def __init__(self, session: AsyncSession, limit_service: LimitService) -> None:
        self.session = session
        self.limit_service = limit_service
        self.match_service = MatchService(session)

    async def rate_profile(self, from_profile_id: int, to_profile_id: int, score: int) -> RatingResult:
        if from_profile_id == to_profile_id:
            raise ValueError("Нельзя оценивать свою анкету.")
        if not 1 <= score <= 10:
            raise ValueError("Оценка должна быть от 1 до 10.")

        await self.limit_service.increment(from_profile_id, DailyAction.RATING)

        rating = await self.session.scalar(
            select(Rating).where(
                Rating.from_profile_id == from_profile_id,
                Rating.to_profile_id == to_profile_id,
            )
        )
        is_new = rating is None
        previous_score = rating.score if rating is not None else None
        if rating is None:
            rating = Rating(from_profile_id=from_profile_id, to_profile_id=to_profile_id, score=score)
            self.session.add(rating)
        else:
            rating.score = score

        await self.session.flush()
        rating_avg, rating_count = await self.recalculate_profile_rating(to_profile_id)

        match_result: MatchResult | None = None
        if score >= LIKE_SCORE_MIN:
            match_result = await self.match_service.ensure_like(from_profile_id, to_profile_id, LikeSource.RATING)
            if previous_score is None or previous_score < LIKE_SCORE_MIN:
                await self.limit_service.increment(from_profile_id, DailyAction.LIKE)
        elif previous_score is not None and previous_score >= LIKE_SCORE_MIN:
            await self.match_service.remove_like(from_profile_id, to_profile_id, LikeSource.RATING)

        self.session.add(
            AuditLog(
                event_type=AuditEventType.RATING_CREATED,
                profile_id=from_profile_id,
                payload={
                    "to_profile_id": to_profile_id,
                    "score": score,
                    "is_new": is_new,
                    "rating_avg": str(rating_avg),
                    "rating_count": rating_count,
                },
            )
        )
        await self.session.flush()
        return RatingResult(rating=rating, rating_avg=rating_avg, rating_count=rating_count, match_result=match_result)

    async def recalculate_profile_rating(self, profile_id: int) -> tuple[Decimal, int]:
        row = await self.session.execute(
            select(func.avg(Rating.score), func.count(Rating.id)).where(Rating.to_profile_id == profile_id)
        )
        avg_value, count_value = row.one()
        rating_count = int(count_value or 0)
        rating_avg = Decimal("0.00")
        if avg_value is not None:
            rating_avg = Decimal(str(avg_value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        profile = await self.session.get(Profile, profile_id)
        if profile is None:
            raise ValueError("Анкета не найдена.")
        profile.rating_avg = rating_avg
        profile.rating_count = rating_count
        await self.session.flush()
        return rating_avg, rating_count
