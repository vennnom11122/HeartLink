from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import age_confirm_keyboard
from app.bot.keyboards.reply import main_menu_keyboard
from app.bot.states.profile_states import ProfileCreation
from app.db.models import User
from app.db.repositories.profiles import ProfileRepository

router = Router()


WELCOME_TEXT = (
    "Привет! Это HeartLink 💘\n\n"
    "Здесь можно знакомиться, смотреть анкеты, ставить оценки, получать взаимные симпатии "
    "и отправлять валентинки.\n\n"
    "Перед началом нужна короткая регистрация: имя, возраст, пол, город, описание и фото.\n\n"
    "HeartLink доступен только пользователям 18+. Подтверди, что тебе уже есть 18 лет."
)


@router.message(CommandStart())
async def start_command(message: Message, session: AsyncSession, current_user: User, state: FSMContext) -> None:
    await state.clear()
    if current_user.is_banned:
        await message.answer(f"Доступ ограничен. Причина: {current_user.ban_reason or 'бан'}")
        return

    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if profile is not None:
        await message.answer("С возвращением в HeartLink! Выбирай, что делаем дальше.", reply_markup=main_menu_keyboard())
        return

    await message.answer(WELCOME_TEXT, reply_markup=age_confirm_keyboard())


@router.callback_query(F.data == "age:no")
async def age_no(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("К сожалению, бот доступен только пользователям старше 18 лет.")
    await callback.answer()


@router.callback_query(F.data == "age:yes")
async def age_yes(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileCreation.name)
    await callback.message.answer(
        "Начнём регистрацию в HeartLink.\n\n"
        "Как тебя зовут? Напиши имя до 50 символов."
    )
    await callback.answer()


@router.message(Command("menu"))
@router.message(F.text == "Назад")
async def menu_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню HeartLink", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "menu")
async def menu_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Главное меню HeartLink", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.message(Command("help"))
@router.message(F.text == "Помощь")
async def help_command(message: Message) -> None:
    await message.answer(
        "HeartLink коротко:\n"
        "• /profile — твоя анкета\n"
        "• /search — смотреть анкеты\n"
        "• /settings — настройки поиска\n"
        "• /valentines — входящие валентинки\n"
        "• /rules — правила"
    )


@router.message(Command("rules"))
async def rules_command(message: Message) -> None:
    await message.answer(
        "Правила простые: только 18+, уважительное общение, без спама, мошенничества, чужих фото и ссылок в анкете. "
        "Контакты открываются только после взаимной симпатии."
    )
