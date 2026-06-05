from __future__ import annotations

from datetime import datetime, timezone

from aiogram.types import User as TelegramUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEventType, AuditLog, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self.session.scalar(select(User).where(User.telegram_id == telegram_id))

    async def upsert_from_telegram(self, tg_user: TelegramUser, *, admin_ids: set[int] | None = None) -> User:
        user = await self.get_by_telegram_id(tg_user.id)
        is_new = user is None
        if user is None:
            user = User(telegram_id=tg_user.id)
            self.session.add(user)

        user.username = tg_user.username
        user.first_name = tg_user.first_name
        user.last_name = tg_user.last_name
        user.language_code = tg_user.language_code
        user.is_bot = tg_user.is_bot
        user.last_active_at = datetime.now(timezone.utc)
        if admin_ids and tg_user.id in admin_ids:
            user.is_admin = True

        await self.session.flush()
        if is_new:
            self.session.add(
                AuditLog(
                    event_type=AuditEventType.USER_REGISTERED,
                    user_id=user.id,
                    payload={"telegram_id": tg_user.id},
                )
            )
        return user

