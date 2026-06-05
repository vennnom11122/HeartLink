from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.bot.keyboards.inline import valentine_decision_keyboard, valentine_mode_keyboard, valentine_open_keyboard
from app.bot.states.valentine_states import ValentineCreation
from app.config import Settings
from app.db.models import ComplaintReason, Profile, User, Valentine, ValentineStatus
from app.db.repositories.profiles import ProfileRepository
from app.services.complaint_service import ComplaintService
from app.services.limit_service import LimitExceededError, LimitService
from app.services.notification_service import NotificationService
from app.services.profile_service import ProfileService
from app.services.valentine_service import ValentineService
from app.utils.validators import validate_valentine_message

router = Router()


@router.callback_query(F.data.startswith("valentine:"))
async def valentine_start(callback: CallbackQuery, state: FSMContext) -> None:
    target_profile_id = int(callback.data.split(":", 1)[1])
    await state.set_state(ValentineCreation.choose_mode)
    await state.update_data(target_profile_id=target_profile_id)
    await callback.message.answer("Хочешь добавить сообщение к валентинке?", reply_markup=valentine_mode_keyboard())
    await callback.answer()


@router.callback_query(ValentineCreation.choose_mode, F.data == "val_cancel")
async def valentine_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Отменено.")
    await callback.answer()


async def _send_valentine(
    callback_or_message: CallbackQuery | Message,
    *,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
    current_user: User,
    message_text: str | None = None,
    is_anonymous: bool = False,
) -> None:
    data = await state.get_data()
    target_profile_id = int(data["target_profile_id"])
    sender = await ProfileRepository(session).get_by_user_id(current_user.id)
    target = callback_or_message.message if isinstance(callback_or_message, CallbackQuery) else callback_or_message
    if sender is None:
        await target.answer("Сначала создай анкету через /start.")
        return

    service = ValentineService(session, settings, LimitService(session, settings))
    try:
        valentine = await service.send(
            sender.id,
            target_profile_id,
            message=message_text,
            is_anonymous=is_anonymous,
        )
    except (ValueError, LimitExceededError) as exc:
        await target.answer(str(exc))
        return

    await NotificationService(target.bot, session).notify_valentine(valentine)
    await state.clear()
    await target.answer("Валентинка отправлена 💌")


@router.callback_query(ValentineCreation.choose_mode, F.data == "val_no_msg")
async def valentine_without_message(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
    current_user: User,
) -> None:
    await _send_valentine(callback, state=state, session=session, settings=settings, current_user=current_user)
    await callback.answer()


@router.callback_query(ValentineCreation.choose_mode, F.data == "val_anon")
async def valentine_anonymous(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
    current_user: User,
) -> None:
    await _send_valentine(
        callback,
        state=state,
        session=session,
        settings=settings,
        current_user=current_user,
        is_anonymous=True,
    )
    await callback.answer()


@router.callback_query(ValentineCreation.choose_mode, F.data == "val_msg")
async def valentine_message_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ValentineCreation.message)
    await callback.message.answer("Напиши сообщение до 300 символов.")
    await callback.answer()


@router.message(ValentineCreation.message)
async def valentine_message_save(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
    current_user: User,
) -> None:
    ok, error = validate_valentine_message(message.text or "")
    if not ok:
        await message.answer(error or "Сообщение не подходит.")
        return
    await _send_valentine(
        message,
        state=state,
        session=session,
        settings=settings,
        current_user=current_user,
        message_text=(message.text or "").strip(),
    )


@router.message(Command("valentines"))
@router.message(F.text == "Валентинки")
async def valentines_inbox(message: Message, session: AsyncSession, settings: Settings, current_user: User) -> None:
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if profile is None:
        await message.answer("Сначала создай анкету через /start.")
        return

    valentines = await ValentineService(session, settings, LimitService(session, settings)).pending_for_profile(profile.id)
    if not valentines:
        await message.answer("Новых валентинок пока нет.")
        return
    await message.answer(f"У тебя {len(valentines)} валентинок.")
    for valentine in valentines[:5]:
        title = "Вам пришла анонимная валентинка 💌" if valentine.is_anonymous else "Вам пришла валентинка 💌"
        await message.answer(title, reply_markup=valentine_open_keyboard(valentine.id))


@router.callback_query(F.data.startswith("val_open:"))
async def open_valentine(callback: CallbackQuery, session: AsyncSession, settings: Settings, current_user: User) -> None:
    valentine_id = int(callback.data.split(":", 1)[1])
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if profile is None:
        await callback.message.answer("Анкета не найдена.")
        await callback.answer()
        return

    service = ValentineService(session, settings, LimitService(session, settings))
    try:
        valentine = await service.open(valentine_id, profile.id)
    except ValueError as exc:
        await callback.message.answer(str(exc))
        await callback.answer()
        return

    if valentine.is_anonymous:
        text = "Вам пришла анонимная валентинка 💌"
        if valentine.message:
            text += f"\n\nСообщение:\n«{valentine.message}»"
    else:
        sender = await session.scalar(
            select(Profile)
            .where(Profile.id == valentine.from_profile_id)
            .options(selectinload(Profile.city), selectinload(Profile.user))
        )
        if sender is None:
            text = "Валентинка от пользователя, который уже удалил анкету."
        else:
            text = "Валентинка от пользователя:\n\n" + ProfileService.format_profile(sender, include_rating=False)
            if valentine.message:
                text += f"\n\nСообщение:\n«{valentine.message}»"

    await callback.message.answer(text, reply_markup=valentine_decision_keyboard(valentine.id))
    await callback.answer()


@router.callback_query(F.data.startswith("val_accept:"))
async def accept_valentine(callback: CallbackQuery, session: AsyncSession, settings: Settings, current_user: User) -> None:
    valentine_id = int(callback.data.split(":", 1)[1])
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if profile is None:
        await callback.message.answer("Анкета не найдена.")
        await callback.answer()
        return

    try:
        result = await ValentineService(session, settings, LimitService(session, settings)).accept(valentine_id, profile.id)
    except ValueError as exc:
        await callback.message.answer(str(exc))
        await callback.answer()
        return

    await callback.message.answer("Валентинка принята 💘")
    if result.match:
        await NotificationService(callback.bot, session).notify_match(result.match)
    await callback.answer()


@router.callback_query(F.data.startswith("val_reject:"))
async def reject_valentine(callback: CallbackQuery, session: AsyncSession, settings: Settings, current_user: User) -> None:
    valentine_id = int(callback.data.split(":", 1)[1])
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if profile is not None:
        await ValentineService(session, settings, LimitService(session, settings)).reject(valentine_id, profile.id)
    await callback.message.answer("Валентинка отклонена.")
    await callback.answer()


@router.callback_query(F.data.startswith("val_report:"))
async def report_valentine(callback: CallbackQuery, session: AsyncSession, settings: Settings, current_user: User) -> None:
    valentine_id = int(callback.data.split(":", 1)[1])
    viewer = await ProfileRepository(session).get_by_user_id(current_user.id)
    valentine = await session.get(Valentine, valentine_id)
    if viewer is None or valentine is None:
        await callback.message.answer("Не удалось создать жалобу.")
    else:
        await ComplaintService(session, settings, LimitService(session, settings)).create(
            viewer.id,
            valentine.from_profile_id,
            ComplaintReason.SPAM,
            comment="Жалоба на валентинку",
        )
        await callback.message.answer("Жалоба отправлена на модерацию.")
    await callback.answer()

