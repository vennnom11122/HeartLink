from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Profile, SearchSettings, User


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, profile_id: int, *, with_user: bool = False, with_photos: bool = False) -> Profile | None:
        stmt = select(Profile).where(Profile.id == profile_id)
        if with_user:
            stmt = stmt.options(selectinload(Profile.user))
        if with_photos:
            stmt = stmt.options(selectinload(Profile.photos), selectinload(Profile.city))
        return await self.session.scalar(stmt)

    async def get_by_user_id(self, user_id: int, *, with_photos: bool = False) -> Profile | None:
        stmt = select(Profile).where(Profile.user_id == user_id)
        if with_photos:
            stmt = stmt.options(selectinload(Profile.photos), selectinload(Profile.city))
        return await self.session.scalar(stmt)

    async def get_by_telegram_id(self, telegram_id: int, *, with_photos: bool = False) -> Profile | None:
        stmt = select(Profile).join(User).where(User.telegram_id == telegram_id)
        if with_photos:
            stmt = stmt.options(selectinload(Profile.photos), selectinload(Profile.city), selectinload(Profile.user))
        return await self.session.scalar(stmt)

    async def ensure_search_settings(self, profile: Profile) -> SearchSettings:
        settings = await self.session.scalar(select(SearchSettings).where(SearchSettings.profile_id == profile.id))
        if settings is None:
            settings = SearchSettings(
                profile_id=profile.id,
                city_ids=[profile.city_id],
                min_age=profile.min_age_preference,
                max_age=profile.max_age_preference,
                gender_filter=profile.looking_for_gender,
                show_other_cities=False,
            )
            self.session.add(settings)
            await self.session.flush()
        return settings

