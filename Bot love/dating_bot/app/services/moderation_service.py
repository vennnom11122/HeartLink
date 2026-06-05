from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import AuditEventType, AuditLog, Photo, PhotoModerationStatus, Profile, User


class ModerationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def approve_photo(self, photo_id: int) -> Photo:
        photo = await self.session.get(Photo, photo_id)
        if photo is None:
            raise ValueError("Фото не найдено.")
        photo.moderation_status = PhotoModerationStatus.APPROVED
        photo.is_approved = True
        await self.session.flush()
        return photo

    async def reject_photo(self, photo_id: int) -> Photo:
        photo = await self.session.get(Photo, photo_id)
        if photo is None:
            raise ValueError("Фото не найдено.")
        photo.moderation_status = PhotoModerationStatus.REJECTED
        photo.is_approved = False
        await self.session.flush()
        return photo

    async def ban_photo_owner(self, photo_id: int, reason: str | None = None) -> User:
        photo = await self.session.get(Photo, photo_id)
        if photo is None:
            raise ValueError("Фото не найдено.")
        profile = await self.session.get(Profile, photo.profile_id)
        if profile is None:
            raise ValueError("Анкета не найдена.")
        return await self.ban_user(profile.user_id, reason or "photo moderation")

    async def ban_user(self, user_id: int, reason: str | None = None) -> User:
        user = await self.session.scalar(
            select(User).where(User.id == user_id).options(selectinload(User.profile))
        )
        if user is None:
            raise ValueError("Пользователь не найден.")
        user.is_banned = True
        user.ban_reason = reason
        if user.profile is not None:
            user.profile.is_hidden = True
        self.session.add(
            AuditLog(
                event_type=AuditEventType.USER_BANNED,
                user_id=user.id,
                profile_id=user.profile.id if user.profile else None,
                payload={"reason": reason},
            )
        )
        await self.session.flush()
        return user

    async def unban_user(self, user_id: int) -> User:
        user = await self.session.get(User, user_id)
        if user is None:
            raise ValueError("Пользователь не найден.")
        user.is_banned = False
        user.ban_reason = None
        await self.session.flush()
        return user
