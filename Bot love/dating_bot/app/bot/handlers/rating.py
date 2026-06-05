from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.search import show_next_profile
from app.config import Settings
from app.db.models import User
from app.db.repositories.profiles import ProfileRepository
from app.services.limit_service import LimitExceededError, LimitService
from app.services.notification_service import NotificationService
from app.services.rating_service import RatingService

router = Router()


@router.callback_query(F.data.startswith("rate:"))
async def rate_profile(callback: CallbackQuery, session: AsyncSession, settings: Settings, current_user: User) -> None:
    _, raw_profile_id, raw_score = callback.data.split(":")
    to_profile_id = int(raw_profile_id)
    score = int(raw_score)

    from_profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if from_profile is None:
        await callback.message.answer("Сначала создай анкету через /start.")
        await callback.answer()
        return

    service = RatingService(session, LimitService(session, settings))
    try:
        result = await service.rate_profile(from_profile.id, to_profile_id, score)
    except (ValueError, LimitExceededError) as exc:
        await callback.message.answer(str(exc))
        await callback.answer()
        return

    await callback.message.answer("Оценка сохранена ⭐")
    if result.match_result and result.match_result.created and result.match_result.match:
        await callback.message.answer("У вас взаимная симпатия! 💘\n\nТеперь можно начать общение.")
        await NotificationService(callback.bot, session).notify_match(result.match_result.match)

    await callback.answer()
    await show_next_profile(callback, session=session, settings=settings, current_user=current_user)

