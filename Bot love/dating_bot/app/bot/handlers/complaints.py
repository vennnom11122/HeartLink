from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import complaint_reason_keyboard
from app.config import Settings
from app.db.models import ComplaintReason, User
from app.db.repositories.profiles import ProfileRepository
from app.services.block_service import BlockService
from app.services.complaint_service import ComplaintService
from app.services.limit_service import LimitExceededError, LimitService

router = Router()


@router.callback_query(F.data.startswith("complaint:"))
async def complaint_start(callback: CallbackQuery) -> None:
    profile_id = int(callback.data.split(":", 1)[1])
    await callback.message.answer("Выбери причину жалобы:", reply_markup=complaint_reason_keyboard(profile_id))
    await callback.answer()


@router.callback_query(F.data.startswith("complaint_reason:"))
async def complaint_reason(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
    current_user: User,
) -> None:
    _, raw_profile_id, raw_reason = callback.data.split(":")
    viewer = await ProfileRepository(session).get_by_user_id(current_user.id)
    if viewer is None:
        await callback.message.answer("Сначала создай анкету.")
        await callback.answer()
        return
    try:
        await ComplaintService(session, settings, LimitService(session, settings)).create(
            viewer.id,
            int(raw_profile_id),
            ComplaintReason(raw_reason),
        )
    except (ValueError, LimitExceededError) as exc:
        await callback.message.answer(str(exc))
        await callback.answer()
        return
    await callback.message.answer("Жалоба отправлена на модерацию.")
    await callback.answer()


@router.callback_query(F.data.startswith("block:"))
async def block_profile(callback: CallbackQuery, session: AsyncSession, current_user: User) -> None:
    blocked_profile_id = int(callback.data.split(":", 1)[1])
    viewer = await ProfileRepository(session).get_by_user_id(current_user.id)
    if viewer is None:
        await callback.message.answer("Сначала создай анкету.")
    else:
        await BlockService(session).block(viewer.id, blocked_profile_id)
        await callback.message.answer("Пользователь заблокирован. Вы больше не увидите друг друга в поиске.")
    await callback.answer()

