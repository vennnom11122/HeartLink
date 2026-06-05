from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Match, Profile, Rating, User
from app.db.repositories.profiles import ProfileRepository

router = Router()


@router.message(Command("matches"))
async def matches_command(message: Message, session: AsyncSession, current_user: User) -> None:
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if profile is None:
        await message.answer("Сначала создай анкету через /start.")
        return
    matches = list(
        (
            await session.scalars(
                select(Match)
                .where(or_(Match.profile1_id == profile.id, Match.profile2_id == profile.id), Match.is_active.is_(True))
                .order_by(Match.created_at.desc())
                .limit(10)
            )
        ).all()
    )
    if not matches:
        await message.answer("Матчей пока нет. Всё впереди.")
        return

    other_ids = [match.profile2_id if match.profile1_id == profile.id else match.profile1_id for match in matches]
    others = list(
        (
            await session.scalars(
                select(Profile).where(Profile.id.in_(other_ids)).options(selectinload(Profile.user), selectinload(Profile.city))
            )
        ).all()
    )
    lines = ["Твои взаимные симпатии:"]
    for other in others:
        contact = f"@{other.user.username}" if other.user.username else "username скрыт, можно писать через бота"
        lines.append(f"• {other.display_name}, {other.age}, {other.city.name} — {contact}")
    await message.answer("\n".join(lines))


@router.message(F.text == "Кто меня оценил")
async def who_rated_me(message: Message, session: AsyncSession, current_user: User) -> None:
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if profile is None:
        await message.answer("Сначала создай анкету через /start.")
        return
    ratings = list(
        (
            await session.scalars(
                select(Rating)
                .where(Rating.to_profile_id == profile.id)
                .order_by(Rating.updated_at.desc())
                .limit(10)
            )
        ).all()
    )
    if not ratings:
        await message.answer("Тебя пока никто не оценил.")
        return
    high = len([rating for rating in ratings if rating.score >= 7])
    await message.answer(
        f"Последние оценки: {len(ratings)}\n"
        f"Симпатий среди них: {high}\n\n"
        "Имена пользователей раскрываются после взаимной симпатии."
    )

