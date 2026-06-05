from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import rating_keyboard
from app.config import Settings
from app.db.models import PhotoModerationStatus, Profile, User
from app.db.repositories.profiles import ProfileRepository
from app.services.limit_service import LimitExceededError, LimitService
from app.services.profile_service import ProfileService
from app.services.search_service import SearchService

router = Router()


async def _answer(target: Message | CallbackQuery, text: str, **kwargs) -> None:
    message = target.message if isinstance(target, CallbackQuery) else target
    await message.answer(text, **kwargs)


async def show_next_profile(
    target: Message | CallbackQuery,
    *,
    session: AsyncSession,
    settings: Settings,
    current_user: User,
) -> None:
    viewer = await ProfileRepository(session).get_by_user_id(current_user.id)
    if viewer is None:
        await _answer(target, "Сначала создай анкету через /start.")
        return

    limit_service = LimitService(session, settings)
    search_service = SearchService(session, settings, limit_service)
    try:
        candidate = await search_service.get_next_profile_for_viewer(viewer.id)
        if candidate is None:
            await _answer(
                target,
                "Пока нет подходящих анкет 😔\n\nПопробуй изменить город, возраст или настройки поиска.",
            )
            return
        await search_service.record_view(viewer.id, candidate.id)
    except LimitExceededError as exc:
        await _answer(target, str(exc))
        return

    await send_profile_card(target, candidate)


async def send_profile_card(target: Message | CallbackQuery, profile: Profile) -> None:
    message = target.message if isinstance(target, CallbackQuery) else target
    approved_photos = [
        photo
        for photo in profile.photos
        if photo.is_approved and photo.moderation_status == PhotoModerationStatus.APPROVED
    ]
    approved_photos.sort(key=lambda photo: (not photo.is_main, photo.position))
    caption = ProfileService.format_profile(profile)
    if approved_photos:
        await message.answer_photo(
            approved_photos[0].telegram_file_id,
            caption=caption,
            reply_markup=rating_keyboard(profile.id),
        )
    else:
        await message.answer(caption, reply_markup=rating_keyboard(profile.id))


@router.message(Command("search"))
@router.message(F.text == "Смотреть анкеты")
async def search_command(message: Message, session: AsyncSession, settings: Settings, current_user: User) -> None:
    await show_next_profile(message, session=session, settings=settings, current_user=current_user)


@router.callback_query(F.data == "search:next")
async def search_next(callback: CallbackQuery, session: AsyncSession, settings: Settings, current_user: User) -> None:
    await callback.answer()
    await show_next_profile(callback, session=session, settings=settings, current_user=current_user)

