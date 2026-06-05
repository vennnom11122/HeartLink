from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import cities_keyboard, settings_keyboard
from app.bot.states.profile_states import SearchSettingsEdit
from app.db.models import LookingForGender, User
from app.db.repositories.cities import CityRepository
from app.db.repositories.profiles import ProfileRepository
from app.utils.validators import validate_age

router = Router()


async def _settings_text(session: AsyncSession, current_user: User) -> str:
    repo = ProfileRepository(session)
    profile = await repo.get_by_user_id(current_user.id)
    if profile is None:
        return "Сначала создай анкету через /start."
    settings = await repo.ensure_search_settings(profile)
    city_names = []
    for city_id in settings.city_ids or []:
        city = await CityRepository(session).get(int(city_id))
        if city is not None:
            city_names.append(city.name)
    return (
        "Настройки поиска:\n\n"
        f"Города: {', '.join(city_names) if city_names else 'свой город'}\n"
        f"Возраст: {settings.min_age}-{settings.max_age}\n"
        f"Пол: {settings.gender_filter.value}\n"
        f"Другие города: {'да' if settings.show_other_cities else 'нет'}"
    )


@router.message(Command("settings"))
@router.message(F.text == "Настройки")
async def settings_command(message: Message, session: AsyncSession, current_user: User) -> None:
    await message.answer(await _settings_text(session, current_user), reply_markup=settings_keyboard())


@router.callback_query(F.data == "settings:city")
async def settings_city_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.set_state(SearchSettingsEdit.city)
    cities = await CityRepository(session).popular()
    await callback.message.answer(
        "Выбери город поиска или начни вводить название.",
        reply_markup=cities_keyboard(cities, prefix="settings_city"),
    )
    await callback.answer()


@router.callback_query(SearchSettingsEdit.city, F.data.startswith("settings_city_page:"))
async def settings_city_page(callback: CallbackQuery, session: AsyncSession) -> None:
    page = int(callback.data.split(":", 1)[1])
    cities = await CityRepository(session).page(page=page)
    await callback.message.answer("Выбери город:", reply_markup=cities_keyboard(cities, prefix="settings_city", page=page))
    await callback.answer()


@router.callback_query(SearchSettingsEdit.city, F.data.startswith("settings_city:"))
async def settings_city_save(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    current_user: User,
) -> None:
    city_id = int(callback.data.split(":", 1)[1])
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    city = await CityRepository(session).get(city_id)
    if profile is None or city is None:
        await callback.message.answer("Анкета или город не найдены.")
    else:
        search_settings = await ProfileRepository(session).ensure_search_settings(profile)
        search_settings.city_ids = [city.id]
        search_settings.show_other_cities = False
        await callback.message.answer(f"Город поиска обновлён: {city.name}")
    await state.clear()
    await callback.answer()


@router.message(SearchSettingsEdit.city)
async def settings_city_search(message: Message, session: AsyncSession) -> None:
    cities = await CityRepository(session).search(message.text or "")
    if not cities:
        await message.answer("Город не найден в списке 300k+.")
        return
    await message.answer("Выбери город:", reply_markup=cities_keyboard(cities, prefix="settings_city"))


@router.callback_query(F.data == "settings:min_age")
async def settings_min_age_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SearchSettingsEdit.min_age)
    await callback.message.answer("Минимальный возраст для поиска?")
    await callback.answer()


@router.message(SearchSettingsEdit.min_age)
async def settings_min_age_save(message: Message, state: FSMContext, session: AsyncSession, current_user: User) -> None:
    ok, value = validate_age(message.text or "")
    if not ok:
        await message.answer(str(value))
        return
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if profile is not None:
        settings = await ProfileRepository(session).ensure_search_settings(profile)
        settings.min_age = int(value)
        if settings.max_age < settings.min_age:
            settings.max_age = settings.min_age
    await state.clear()
    await message.answer("Минимальный возраст обновлён.")


@router.callback_query(F.data == "settings:max_age")
async def settings_max_age_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SearchSettingsEdit.max_age)
    await callback.message.answer("Максимальный возраст для поиска?")
    await callback.answer()


@router.message(SearchSettingsEdit.max_age)
async def settings_max_age_save(message: Message, state: FSMContext, session: AsyncSession, current_user: User) -> None:
    ok, value = validate_age(message.text or "")
    if not ok:
        await message.answer(str(value))
        return
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if profile is not None:
        settings = await ProfileRepository(session).ensure_search_settings(profile)
        settings.max_age = int(value)
        if settings.min_age > settings.max_age:
            settings.min_age = settings.max_age
    await state.clear()
    await message.answer("Максимальный возраст обновлён.")


@router.callback_query(F.data.startswith("settings:gender:"))
async def settings_gender(callback: CallbackQuery, session: AsyncSession, current_user: User) -> None:
    raw_gender = callback.data.split(":")[-1]
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if profile is not None:
        settings = await ProfileRepository(session).ensure_search_settings(profile)
        settings.gender_filter = LookingForGender(raw_gender)
    await callback.message.answer("Фильтр пола обновлён.")
    await callback.answer()


@router.callback_query(F.data == "settings:toggle_other_cities")
async def settings_toggle_other_cities(callback: CallbackQuery, session: AsyncSession, current_user: User) -> None:
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if profile is not None:
        settings = await ProfileRepository(session).ensure_search_settings(profile)
        settings.show_other_cities = not settings.show_other_cities
        await callback.message.answer(f"Другие города: {'да' if settings.show_other_cities else 'нет'}")
    await callback.answer()

