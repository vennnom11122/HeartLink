from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import (
    cities_keyboard,
    gender_keyboard,
    looking_for_keyboard,
    my_profile_keyboard,
    photo_item_keyboard,
    photos_menu_keyboard,
    profile_preview_keyboard,
)
from app.bot.keyboards.reply import done_photo_keyboard, main_menu_keyboard
from app.bot.states.profile_states import ProfileCreation, ProfileEdit
from app.db.models import Gender, LookingForGender, Profile, User
from app.db.repositories.cities import CityRepository
from app.db.repositories.profiles import ProfileRepository
from app.services.profile_service import ProfileCreateDTO, ProfileService
from app.utils.validators import validate_age, validate_bio, validate_name

router = Router()


async def _send_profile_preview(target: Message, profile: Profile, *, own: bool = False) -> None:
    await target.answer(ProfileService.format_profile(profile, include_rating=not own))


async def _send_city_prompt(message: Message, session: AsyncSession, *, prefix: str = "city", page: int = 1) -> None:
    repo = CityRepository(session)
    cities = await repo.popular() if page == 1 else await repo.page(page=page)
    await message.answer(
        "Выбери свой город или начни вводить название. В списке только города 300k+.",
        reply_markup=cities_keyboard(cities, prefix=prefix, page=page),
    )


@router.message(ProfileCreation.name)
async def create_name(message: Message, state: FSMContext) -> None:
    ok, error = validate_name(message.text or "")
    if not ok:
        await message.answer(error or "Имя не подходит.")
        return
    await state.update_data(display_name=(message.text or "").strip())
    await state.set_state(ProfileCreation.age)
    await message.answer("Сколько тебе лет? Укажи число от 18 до 99.")


@router.message(ProfileCreation.age)
async def create_age(message: Message, state: FSMContext) -> None:
    ok, value = validate_age(message.text or "")
    if not ok:
        await message.answer(str(value))
        return
    await state.update_data(age=value)
    await state.set_state(ProfileCreation.gender)
    await message.answer("Какой пол указать в анкете?", reply_markup=gender_keyboard())


@router.callback_query(ProfileCreation.gender, F.data.startswith("profile_gender:"))
async def create_gender(callback: CallbackQuery, state: FSMContext) -> None:
    gender = Gender(callback.data.split(":", 1)[1])
    await state.update_data(gender=gender.value)
    await state.set_state(ProfileCreation.looking_for)
    await callback.message.answer("Кого HeartLink будет показывать тебе в ленте?", reply_markup=looking_for_keyboard())
    await callback.answer()


@router.callback_query(ProfileCreation.looking_for, F.data.startswith("profile_looking:"))
async def create_looking_for(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    looking_for = LookingForGender(callback.data.split(":", 1)[1])
    await state.update_data(looking_for_gender=looking_for.value)
    await state.set_state(ProfileCreation.city)
    await _send_city_prompt(callback.message, session)
    await callback.answer()


@router.callback_query(ProfileCreation.city, F.data.startswith("city_page:"))
async def create_city_page(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    page = int(callback.data.split(":", 1)[1])
    await _send_city_prompt(callback.message, session, page=page)
    await callback.answer()


@router.callback_query(ProfileCreation.city, F.data.startswith("city:"))
async def create_city_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    city_id = int(callback.data.split(":", 1)[1])
    city = await CityRepository(session).get(city_id)
    if city is None or not city.is_active:
        await callback.message.answer("Город не найден. Выбери город из списка.")
        await callback.answer()
        return
    await state.update_data(city_id=city.id)
    await state.set_state(ProfileCreation.bio)
    await callback.message.answer(
        "Расскажи немного о себе: чем увлекаешься и кого хочешь встретить.\n\n"
        "До 500 символов, без ссылок и контактов."
    )
    await callback.answer()


@router.message(ProfileCreation.city)
async def create_city_search(message: Message, session: AsyncSession) -> None:
    query = (message.text or "").strip()
    if len(query) < 2:
        await message.answer("Введи минимум 2 буквы города.")
        return
    cities = await CityRepository(session).search(query)
    if not cities:
        await message.answer("Такого города в списке 300k+ нет. Попробуй другое название.")
        return
    await message.answer("Нашёл такие варианты:", reply_markup=cities_keyboard(cities))


@router.message(ProfileCreation.bio)
async def create_bio(message: Message, state: FSMContext, session: AsyncSession, current_user: User) -> None:
    ok, error = validate_bio(message.text or "")
    if not ok:
        await message.answer(error or "Описание не подходит.")
        return

    data = await state.get_data()
    service = ProfileService(session)
    profile = await service.create_profile(
        current_user,
        ProfileCreateDTO(
            display_name=data["display_name"],
            age=int(data["age"]),
            gender=Gender(data["gender"]),
            looking_for_gender=LookingForGender(data["looking_for_gender"]),
            city_id=int(data["city_id"]),
            bio=(message.text or "").strip(),
        ),
    )
    await state.update_data(profile_id=profile.id)
    await state.set_state(ProfileCreation.photos)
    await message.answer(
        "Остался последний шаг — фото.\n\n"
        "Загрузи своё фото. Анкеты без одобренного фото не показываются другим пользователям.\n\n"
        "Можно добавить от 1 до 6 фото. Когда закончишь, нажми «Готово».",
        reply_markup=done_photo_keyboard(),
    )


@router.message(ProfileCreation.photos, F.photo)
async def create_photo(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    profile_id = int(data["profile_id"])
    photo = message.photo[-1]
    try:
        await ProfileService(session).add_photo(profile_id, photo.file_id, photo.file_unique_id)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await message.answer("Фото добавлено и отправлено на модерацию. Можно загрузить ещё или нажать «Готово».")


@router.message(ProfileCreation.photos, F.text.casefold() == "готово")
async def create_photos_done(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    profile_id = int(data["profile_id"])
    try:
        await ProfileService(session).activate_if_ready(profile_id)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    profile = await ProfileRepository(session).get(profile_id, with_photos=True)
    await state.set_state(ProfileCreation.preview)
    await message.answer("Вот как выглядит твоя анкета:", reply_markup=ReplyKeyboardRemove())
    if profile is not None:
        await _send_profile_preview(message, profile, own=True)
    await message.answer(
        "Фото появятся публично после модерации.",
        reply_markup=profile_preview_keyboard(),
    )


@router.callback_query(ProfileCreation.preview, F.data == "profile_confirm")
async def create_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer(
        "Готово! Твоя анкета HeartLink создана 💫\n\n"
        "Теперь ты можешь смотреть анкеты других пользователей и ставить оценки.",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@router.message(Command("profile"))
@router.message(F.text == "Моя анкета")
async def my_profile(message: Message, session: AsyncSession, current_user: User) -> None:
    profile = await ProfileRepository(session).get_by_user_id(current_user.id, with_photos=True)
    if profile is None:
        await message.answer("Анкеты пока нет. Нажми /start, чтобы создать её.")
        return
    await message.answer("Твоя анкета:")
    await _send_profile_preview(message, profile, own=True)
    approved_count = len([p for p in profile.photos if p.is_approved])
    await message.answer(
        f"Фото: {len(profile.photos)} загружено, {approved_count} одобрено.",
        reply_markup=my_profile_keyboard(profile.is_hidden),
    )


async def _send_photos_menu(message: Message, profile: Profile) -> None:
    if not profile.photos:
        await message.answer("Фото пока нет.", reply_markup=photos_menu_keyboard())
        return

    await message.answer("Твои фото:")
    for photo in profile.photos:
        status = photo.moderation_status.value
        marker = "главное" if photo.is_main else f"позиция {photo.position}"
        await message.answer_photo(
            photo.telegram_file_id,
            caption=f"Фото #{photo.id}: {marker}, статус {status}",
            reply_markup=photo_item_keyboard(photo),
        )
    await message.answer("Можно добавить ещё фото или вернуться назад.", reply_markup=photos_menu_keyboard())


@router.callback_query(F.data == "profile:hide")
async def hide_profile(callback: CallbackQuery, session: AsyncSession, current_user: User) -> None:
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if profile is None:
        await callback.message.answer("Анкета не найдена.")
    else:
        await ProfileService(session).hide(profile.id, hidden=True)
        await callback.message.answer("Анкета скрыта. Её не будут видеть в поиске.")
    await callback.answer()


@router.callback_query(F.data == "profile:show")
async def show_profile(callback: CallbackQuery, session: AsyncSession, current_user: User) -> None:
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if profile is None:
        await callback.message.answer("Анкета не найдена.")
    else:
        await ProfileService(session).hide(profile.id, hidden=False)
        await callback.message.answer("Анкета снова видна в поиске, если есть одобренное фото.")
    await callback.answer()


@router.callback_query(F.data == "profile:delete_confirm")
async def delete_profile_confirm(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "Удалить анкету без восстановления?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Да, удалить", callback_data="profile:delete")],
                [InlineKeyboardButton(text="Отмена", callback_data="menu")],
            ]
        ),
    )
    await callback.answer()


@router.message(Command("delete_profile"))
async def delete_profile_command(message: Message) -> None:
    await message.answer(
        "Удалить анкету без восстановления?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Да, удалить", callback_data="profile:delete")],
                [InlineKeyboardButton(text="Отмена", callback_data="menu")],
            ]
        ),
    )


@router.callback_query(F.data == "profile:delete")
async def delete_profile(callback: CallbackQuery, session: AsyncSession, current_user: User, state: FSMContext) -> None:
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if profile is not None:
        await ProfileService(session).delete(profile.id)
    await state.clear()
    await callback.message.answer("Анкета удалена.", reply_markup=ReplyKeyboardRemove())
    await callback.answer()


@router.callback_query(F.data == "profile:photos")
async def photos_menu(callback: CallbackQuery, session: AsyncSession, current_user: User) -> None:
    profile = await ProfileRepository(session).get_by_user_id(current_user.id, with_photos=True)
    if profile is None:
        await callback.message.answer("Анкета не найдена.")
    else:
        await _send_photos_menu(callback.message, profile)
    await callback.answer()


@router.callback_query(F.data == "profile_edit:name")
async def edit_name_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileEdit.name)
    await callback.message.answer("Напиши новое имя.")
    await callback.answer()


@router.message(ProfileEdit.name)
async def edit_name_save(message: Message, state: FSMContext, session: AsyncSession, current_user: User) -> None:
    ok, error = validate_name(message.text or "")
    if not ok:
        await message.answer(error or "Имя не подходит.")
        return
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if profile is not None:
        profile.display_name = (message.text or "").strip()
    await state.clear()
    await message.answer("Имя обновлено.", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "profile_edit:age")
async def edit_age_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileEdit.age)
    await callback.message.answer("Укажи новый возраст.")
    await callback.answer()


@router.message(ProfileEdit.age)
async def edit_age_save(message: Message, state: FSMContext, session: AsyncSession, current_user: User) -> None:
    ok, value = validate_age(message.text or "")
    if not ok:
        await message.answer(str(value))
        return
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if profile is not None:
        profile.age = int(value)
    await state.clear()
    await message.answer("Возраст обновлён.", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "profile_edit:bio")
async def edit_bio_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileEdit.bio)
    await callback.message.answer("Напиши новое описание.")
    await callback.answer()


@router.message(ProfileEdit.bio)
async def edit_bio_save(message: Message, state: FSMContext, session: AsyncSession, current_user: User) -> None:
    ok, error = validate_bio(message.text or "")
    if not ok:
        await message.answer(error or "Описание не подходит.")
        return
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if profile is not None:
        profile.bio = (message.text or "").strip()
    await state.clear()
    await message.answer("Описание обновлено.", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "profile_edit:city")
async def edit_city_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.set_state(ProfileEdit.city)
    await _send_city_prompt(callback.message, session, prefix="edit_city")
    await callback.answer()


@router.callback_query(ProfileEdit.city, F.data.startswith("edit_city_page:"))
async def edit_city_page(callback: CallbackQuery, session: AsyncSession) -> None:
    page = int(callback.data.split(":", 1)[1])
    await _send_city_prompt(callback.message, session, prefix="edit_city", page=page)
    await callback.answer()


@router.callback_query(ProfileEdit.city, F.data.startswith("edit_city:"))
async def edit_city_save(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User) -> None:
    city_id = int(callback.data.split(":", 1)[1])
    city = await CityRepository(session).get(city_id)
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if city is None or profile is None:
        await callback.message.answer("Город или анкета не найдены.")
    else:
        profile.city_id = city.id
        settings = await ProfileRepository(session).ensure_search_settings(profile)
        settings.city_ids = [city.id]
        await callback.message.answer(f"Город обновлён: {city.name}", reply_markup=main_menu_keyboard())
    await state.clear()
    await callback.answer()


@router.message(ProfileEdit.city)
async def edit_city_search(message: Message, session: AsyncSession) -> None:
    query = (message.text or "").strip()
    cities = await CityRepository(session).search(query)
    if not cities:
        await message.answer("Город не найден в списке 300k+.")
        return
    await message.answer("Выбери город:", reply_markup=cities_keyboard(cities, prefix="edit_city"))


@router.callback_query(F.data == "profile_edit:photo")
async def edit_photo_start(callback: CallbackQuery, session: AsyncSession, current_user: User) -> None:
    profile = await ProfileRepository(session).get_by_user_id(current_user.id, with_photos=True)
    if profile is None:
        await callback.message.answer("Анкета не найдена.")
    else:
        await _send_photos_menu(callback.message, profile)
    await callback.answer()


@router.callback_query(F.data == "profile_edit:photo_upload")
async def edit_photo_upload_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileEdit.photo)
    await callback.message.answer("Загрузи новое фото. Оно уйдёт на модерацию.")
    await callback.answer()


@router.message(ProfileEdit.photo, F.photo)
async def edit_photo_save(message: Message, state: FSMContext, session: AsyncSession, current_user: User) -> None:
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if profile is None:
        await message.answer("Анкета не найдена.")
        return
    photo = message.photo[-1]
    try:
        await ProfileService(session).add_photo(profile.id, photo.file_id, photo.file_unique_id)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await state.clear()
    await message.answer("Фото добавлено и отправлено на модерацию.", reply_markup=main_menu_keyboard())


@router.callback_query(F.data.startswith("photo_main:"))
async def photo_set_main(callback: CallbackQuery, session: AsyncSession, current_user: User) -> None:
    photo_id = int(callback.data.split(":", 1)[1])
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if profile is None:
        await callback.message.answer("Анкета не найдена.")
    else:
        try:
            await ProfileService(session).set_main_photo(profile.id, photo_id)
        except ValueError as exc:
            await callback.message.answer(str(exc))
        else:
            await callback.message.answer("Главное фото обновлено.")
    await callback.answer()


@router.callback_query(F.data.startswith("photo_delete:"))
async def photo_delete(callback: CallbackQuery, session: AsyncSession, current_user: User) -> None:
    photo_id = int(callback.data.split(":", 1)[1])
    profile = await ProfileRepository(session).get_by_user_id(current_user.id)
    if profile is None:
        await callback.message.answer("Анкета не найдена.")
    else:
        try:
            await ProfileService(session).delete_photo(profile.id, photo_id)
        except ValueError as exc:
            await callback.message.answer(str(exc))
        else:
            await callback.message.answer("Фото удалено.")
    await callback.answer()
