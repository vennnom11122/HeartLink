from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Photo, PhotoModerationStatus


class PhotoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count_for_profile(self, profile_id: int) -> int:
        return int(await self.session.scalar(select(func.count(Photo.id)).where(Photo.profile_id == profile_id)) or 0)

    async def approved_count_for_profile(self, profile_id: int) -> int:
        return int(
            await self.session.scalar(
                select(func.count(Photo.id)).where(
                    Photo.profile_id == profile_id,
                    Photo.moderation_status == PhotoModerationStatus.APPROVED,
                    Photo.is_approved.is_(True),
                )
            )
            or 0
        )

    async def add_photo(self, profile_id: int, telegram_file_id: str, file_unique_id: str) -> Photo:
        count = await self.count_for_profile(profile_id)
        photo = Photo(
            profile_id=profile_id,
            telegram_file_id=telegram_file_id,
            file_unique_id=file_unique_id,
            position=count + 1,
            is_main=count == 0,
        )
        self.session.add(photo)
        await self.session.flush()
        return photo

    async def list_for_profile(self, profile_id: int) -> list[Photo]:
        return list(
            (
                await self.session.scalars(
                    select(Photo).where(Photo.profile_id == profile_id).order_by(Photo.position.asc())
                )
            ).all()
        )

    async def set_main(self, profile_id: int, photo_id: int) -> Photo:
        photo = await self.session.scalar(
            select(Photo).where(Photo.id == photo_id, Photo.profile_id == profile_id)
        )
        if photo is None:
            raise ValueError("Фото не найдено.")
        await self.session.execute(update(Photo).where(Photo.profile_id == profile_id).values(is_main=False))
        await self.session.execute(
            update(Photo).where(Photo.profile_id == profile_id, Photo.id == photo_id).values(is_main=True)
        )
        await self.session.flush()
        return photo

    async def delete_photo(self, profile_id: int, photo_id: int) -> None:
        photo = await self.session.scalar(
            select(Photo).where(Photo.id == photo_id, Photo.profile_id == profile_id)
        )
        if photo is None:
            raise ValueError("Фото не найдено.")

        was_main = photo.is_main
        await self.session.delete(photo)
        await self.session.flush()

        remaining = await self.list_for_profile(profile_id)
        for index, item in enumerate(remaining, start=1):
            item.position = index

        if remaining and (was_main or not any(item.is_main for item in remaining)):
            remaining[0].is_main = True
        await self.session.flush()

    async def pending(self, *, limit: int = 10) -> list[Photo]:
        return list(
            (
                await self.session.scalars(
                    select(Photo)
                    .where(Photo.moderation_status == PhotoModerationStatus.PENDING)
                    .order_by(Photo.created_at.asc())
                    .limit(limit)
                )
            ).all()
        )
