from __future__ import annotations

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Match, Profile, User, Valentine


class NotificationService:
    def __init__(self, bot: Bot, session: AsyncSession) -> None:
        self.bot = bot
        self.session = session

    async def notify_valentine(self, valentine: Valentine) -> None:
        recipient = await self.session.scalar(
            select(Profile).where(Profile.id == valentine.to_profile_id).options(selectinload(Profile.user))
        )
        if recipient is None:
            return
        await self.bot.send_message(
            recipient.user.telegram_id,
            "Вам пришла валентинка 💌\n\nОткрыть?",
        )

    async def notify_match(self, match: Match) -> None:
        profiles = list(
            (
                await self.session.scalars(
                    select(Profile)
                    .where(Profile.id.in_([match.profile1_id, match.profile2_id]))
                    .options(selectinload(Profile.user))
                )
            ).all()
        )
        by_id = {profile.id: profile for profile in profiles}
        p1 = by_id.get(match.profile1_id)
        p2 = by_id.get(match.profile2_id)
        if not p1 or not p2:
            return
        await self._send_match_message(p1.user, p2)
        await self._send_match_message(p2.user, p1)

    async def _send_match_message(self, user: User, other: Profile) -> None:
        contact = f"Telegram: @{other.user.username}" if other.user.username else (
            "У пользователя нет открытого username. Можно написать первое сообщение через бота."
        )
        await self.bot.send_message(
            user.telegram_id,
            f"У вас новая взаимная симпатия 💘\n\n{other.display_name}, {other.age}\n{contact}",
        )

