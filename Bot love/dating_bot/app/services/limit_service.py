from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.db.models import DailyLimit, Profile


class LimitExceededError(RuntimeError):
    pass


class DailyAction(str, Enum):
    VIEW = "views_count"
    RATING = "ratings_count"
    VALENTINE = "valentines_count"
    LIKE = "likes_count"
    COMPLAINT = "complaints_count"


@dataclass(frozen=True)
class ActionLimits:
    views: int
    ratings: int
    valentines: int
    complaints: int


class LimitService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def _profile_is_premium(self, profile_id: int) -> bool:
        profile = await self.session.scalar(
            select(Profile).where(Profile.id == profile_id).options(selectinload(Profile.user))
        )
        if profile is None:
            return False
        user = profile.user
        if not user.is_premium:
            return False
        return user.premium_until is None or user.premium_until > datetime.now(timezone.utc)

    async def _limits_for_profile(self, profile_id: int) -> ActionLimits:
        if await self._profile_is_premium(profile_id):
            return ActionLimits(
                views=self.settings.premium_daily_views_limit,
                ratings=self.settings.premium_daily_ratings_limit,
                valentines=self.settings.premium_daily_valentines_limit,
                complaints=self.settings.premium_daily_complaints_limit,
            )
        return ActionLimits(
            views=self.settings.daily_views_limit,
            ratings=self.settings.daily_ratings_limit,
            valentines=self.settings.daily_valentines_limit,
            complaints=self.settings.daily_complaints_limit,
        )

    async def _get_or_create_today(self, profile_id: int) -> DailyLimit:
        today = date.today()
        stmt = (
            select(DailyLimit)
            .where(DailyLimit.profile_id == profile_id, DailyLimit.date == today)
            .with_for_update()
        )
        daily = await self.session.scalar(stmt)
        if daily is None:
            daily = DailyLimit(profile_id=profile_id, date=today)
            self.session.add(daily)
            await self.session.flush()
        return daily

    async def increment(self, profile_id: int, action: DailyAction, *, amount: int = 1) -> DailyLimit:
        daily = await self._get_or_create_today(profile_id)
        limits = await self._limits_for_profile(profile_id)
        current = getattr(daily, action.value)

        max_allowed = {
            DailyAction.VIEW: limits.views,
            DailyAction.RATING: limits.ratings,
            DailyAction.VALENTINE: limits.valentines,
            DailyAction.COMPLAINT: limits.complaints,
            DailyAction.LIKE: limits.ratings,
        }[action]

        if current + amount > max_allowed:
            raise LimitExceededError("Дневной лимит на это действие исчерпан.")

        setattr(daily, action.value, current + amount)
        await self.session.flush()
        return daily

