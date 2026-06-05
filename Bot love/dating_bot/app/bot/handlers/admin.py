from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.bot.filters.is_admin import IsAdmin
from app.bot.keyboards.inline import admin_keyboard, photo_moderation_keyboard
from app.db.models import Block, Complaint, Match, Profile, Rating, User, Valentine
from app.db.repositories.photos import PhotoRepository
from app.services.moderation_service import ModerationService

router = Router()


async def _is_staff(current_user: User | None) -> bool:
    return bool(current_user and (current_user.is_admin or current_user.is_moderator))


@router.message(Command("admin"), IsAdmin())
async def admin_panel(message: Message) -> None:
    await message.answer("Админ-панель", reply_markup=admin_keyboard())


@router.message(Command("stats"), IsAdmin())
async def stats_command(message: Message, session: AsyncSession) -> None:
    await message.answer(await _stats_text(session))


@router.callback_query(F.data == "admin:stats")
async def stats_callback(callback: CallbackQuery, session: AsyncSession, current_user: User) -> None:
    if not await _is_staff(current_user):
        await callback.answer("Недоступно", show_alert=True)
        return
    await callback.message.answer(await _stats_text(session))
    await callback.answer()


async def _stats_text(session: AsyncSession) -> str:
    users = await session.scalar(select(func.count(User.id)))
    profiles = await session.scalar(select(func.count(Profile.id)))
    active_profiles = await session.scalar(select(func.count(Profile.id)).where(Profile.is_active.is_(True)))
    ratings = await session.scalar(select(func.count(Rating.id)))
    avg_rating = await session.scalar(select(func.avg(Rating.score)))
    valentines = await session.scalar(select(func.count(Valentine.id)))
    matches = await session.scalar(select(func.count(Match.id)))
    complaints = await session.scalar(select(func.count(Complaint.id)))
    banned = await session.scalar(select(func.count(User.id)).where(User.is_banned.is_(True)))
    blocked_pairs = await session.scalar(select(func.count(Block.id)))
    return (
        "Статистика:\n\n"
        f"Пользователи: {users or 0}\n"
        f"Анкеты: {profiles or 0}\n"
        f"Активные анкеты: {active_profiles or 0}\n"
        f"Оценки: {ratings or 0}\n"
        f"Средняя оценка: {float(avg_rating or 0):.2f}\n"
        f"Валентинки: {valentines or 0}\n"
        f"Матчи: {matches or 0}\n"
        f"Жалобы: {complaints or 0}\n"
        f"Забанено: {banned or 0}\n"
        f"Блокировок между анкетами: {blocked_pairs or 0}"
    )


@router.message(Command("moderation"), IsAdmin())
async def moderation_command(message: Message, session: AsyncSession) -> None:
    await _send_pending_photos(message, session)


@router.callback_query(F.data == "admin:photos")
async def moderation_callback(callback: CallbackQuery, session: AsyncSession, current_user: User) -> None:
    if not await _is_staff(current_user):
        await callback.answer("Недоступно", show_alert=True)
        return
    await _send_pending_photos(callback.message, session)
    await callback.answer()


async def _send_pending_photos(message: Message, session: AsyncSession) -> None:
    photos = await PhotoRepository(session).pending(limit=5)
    if not photos:
        await message.answer("Фото на модерации нет.")
        return
    for photo in photos:
        await message.answer_photo(
            photo.telegram_file_id,
            caption=f"Фото #{photo.id}, анкета #{photo.profile_id}",
            reply_markup=photo_moderation_keyboard(photo.id),
        )


@router.callback_query(F.data.startswith("mod_photo:"))
async def moderate_photo(callback: CallbackQuery, session: AsyncSession, current_user: User) -> None:
    if not await _is_staff(current_user):
        await callback.answer("Недоступно", show_alert=True)
        return
    _, action, raw_photo_id = callback.data.split(":")
    service = ModerationService(session)
    if action == "approve":
        await service.approve_photo(int(raw_photo_id))
        await callback.message.answer("Фото одобрено.")
    elif action == "reject":
        await service.reject_photo(int(raw_photo_id))
        await callback.message.answer("Фото отклонено.")
    elif action == "ban":
        await service.ban_photo_owner(int(raw_photo_id), "photo moderation")
        await callback.message.answer("Пользователь забанен, анкета скрыта.")
    else:
        await callback.message.answer("Неизвестное действие модерации.")
    await callback.answer()


@router.callback_query(F.data == "admin:complaints")
async def complaints_callback(callback: CallbackQuery, session: AsyncSession, current_user: User) -> None:
    if not await _is_staff(current_user):
        await callback.answer("Недоступно", show_alert=True)
        return
    complaints = list(
        (
            await session.scalars(
                select(Complaint).order_by(Complaint.created_at.desc()).limit(10)
            )
        ).all()
    )
    if not complaints:
        await callback.message.answer("Жалоб нет.")
    else:
        lines = ["Последние жалобы:"]
        for complaint in complaints:
            lines.append(f"#{complaint.id}: на анкету {complaint.to_profile_id}, причина {complaint.reason.value}")
        await callback.message.answer("\n".join(lines))
    await callback.answer()


@router.message(Command("ban"), IsAdmin())
async def ban_command(message: Message, session: AsyncSession) -> None:
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Формат: /ban <telegram_id> [причина]")
        return
    try:
        telegram_id = int(parts[1])
    except ValueError:
        await message.answer("telegram_id должен быть числом.")
        return
    reason = parts[2] if len(parts) > 2 else "moderation"
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id).options(selectinload(User.profile)))
    if user is None:
        await message.answer("Пользователь не найден.")
        return
    await ModerationService(session).ban_user(user.id, reason)
    await message.answer("Пользователь забанен.")


@router.message(Command("unban"), IsAdmin())
async def unban_command(message: Message, session: AsyncSession) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Формат: /unban <telegram_id>")
        return
    try:
        telegram_id = int(parts[1])
    except ValueError:
        await message.answer("telegram_id должен быть числом.")
        return
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        await message.answer("Пользователь не найден.")
        return
    await ModerationService(session).unban_user(user.id)
    await message.answer("Пользователь разбанен.")


@router.message(Command("broadcast"), IsAdmin())
async def broadcast_command(message: Message, session: AsyncSession) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Формат: /broadcast <текст>")
        return
    users = list((await session.scalars(select(User).where(User.is_banned.is_(False)))).all())
    sent = 0
    for user in users:
        try:
            await message.bot.send_message(user.telegram_id, parts[1])
            sent += 1
        except Exception:
            continue
    await message.answer(f"Рассылка отправлена: {sent}")
