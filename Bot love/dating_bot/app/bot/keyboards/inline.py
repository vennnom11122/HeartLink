from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.models import City, ComplaintReason, Gender, LookingForGender, Photo


def age_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Мне есть 18+", callback_data="age:yes")],
            [InlineKeyboardButton(text="Мне нет 18", callback_data="age:no")],
        ]
    )


def gender_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Я парень", callback_data=f"profile_gender:{Gender.MALE.value}")],
            [InlineKeyboardButton(text="Я девушка", callback_data=f"profile_gender:{Gender.FEMALE.value}")],
            [InlineKeyboardButton(text="Другое", callback_data=f"profile_gender:{Gender.OTHER.value}")],
        ]
    )


def looking_for_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Парней", callback_data=f"profile_looking:{LookingForGender.MALE.value}")],
            [InlineKeyboardButton(text="Девушек", callback_data=f"profile_looking:{LookingForGender.FEMALE.value}")],
            [InlineKeyboardButton(text="Всех", callback_data=f"profile_looking:{LookingForGender.ANY.value}")],
        ]
    )


def cities_keyboard(cities: list[City], *, prefix: str = "city", page: int = 1) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for city in cities:
        builder.button(text=city.name, callback_data=f"{prefix}:{city.id}")
    builder.adjust(1)
    builder.row(
        InlineKeyboardButton(text="◀️", callback_data=f"{prefix}_page:{max(page - 1, 1)}"),
        InlineKeyboardButton(text="▶️", callback_data=f"{prefix}_page:{page + 1}"),
    )
    return builder.as_markup()


def profile_preview_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Всё верно", callback_data="profile_confirm")],
            [
                InlineKeyboardButton(text="Изменить имя", callback_data="profile_edit:name"),
                InlineKeyboardButton(text="Изменить возраст", callback_data="profile_edit:age"),
            ],
            [
                InlineKeyboardButton(text="Изменить город", callback_data="profile_edit:city"),
                InlineKeyboardButton(text="Изменить описание", callback_data="profile_edit:bio"),
            ],
            [InlineKeyboardButton(text="Изменить фото", callback_data="profile_edit:photo")],
        ]
    )


def my_profile_keyboard(is_hidden: bool) -> InlineKeyboardMarkup:
    hide_text = "Снова показать анкету" if is_hidden else "Скрыть анкету"
    hide_action = "show" if is_hidden else "hide"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Изменить имя", callback_data="profile_edit:name"),
                InlineKeyboardButton(text="Изменить возраст", callback_data="profile_edit:age"),
            ],
            [
                InlineKeyboardButton(text="Изменить город", callback_data="profile_edit:city"),
                InlineKeyboardButton(text="Изменить описание", callback_data="profile_edit:bio"),
            ],
            [InlineKeyboardButton(text="Фото", callback_data="profile_edit:photo")],
            [InlineKeyboardButton(text=hide_text, callback_data=f"profile:{hide_action}")],
            [InlineKeyboardButton(text="Удалить анкету", callback_data="profile:delete_confirm")],
            [InlineKeyboardButton(text="Назад", callback_data="menu")],
        ]
    )


def photo_item_keyboard(photo: Photo) -> InlineKeyboardMarkup:
    buttons = []
    if not photo.is_main:
        buttons.append(InlineKeyboardButton(text="Сделать главным", callback_data=f"photo_main:{photo.id}"))
    buttons.append(InlineKeyboardButton(text="Удалить", callback_data=f"photo_delete:{photo.id}"))
    return InlineKeyboardMarkup(
        inline_keyboard=[
            buttons,
            [InlineKeyboardButton(text="Добавить фото", callback_data="profile_edit:photo_upload")],
            [InlineKeyboardButton(text="Назад", callback_data="profile:photos")],
        ]
    )


def photos_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Добавить фото", callback_data="profile_edit:photo_upload")],
            [InlineKeyboardButton(text="Назад", callback_data="menu")],
        ]
    )


def rating_keyboard(profile_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for score in range(1, 11):
        builder.button(text=str(score), callback_data=f"rate:{profile_id}:{score}")
    builder.adjust(5, 5)
    builder.row(InlineKeyboardButton(text="💌 Валентинка", callback_data=f"valentine:{profile_id}"))
    builder.row(
        InlineKeyboardButton(text="Следующая", callback_data="search:next"),
        InlineKeyboardButton(text="Пожаловаться", callback_data=f"complaint:{profile_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="Заблокировать", callback_data=f"block:{profile_id}"),
        InlineKeyboardButton(text="Назад", callback_data="menu"),
    )
    return builder.as_markup()


def valentine_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Написать сообщение", callback_data="val_msg")],
            [InlineKeyboardButton(text="Отправить без сообщения", callback_data="val_no_msg")],
            [InlineKeyboardButton(text="Отправить анонимно", callback_data="val_anon")],
            [InlineKeyboardButton(text="Отмена", callback_data="val_cancel")],
        ]
    )


def valentine_open_keyboard(valentine_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть", callback_data=f"val_open:{valentine_id}")],
            [InlineKeyboardButton(text="Позже", callback_data="menu")],
        ]
    )


def valentine_decision_keyboard(valentine_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Принять 💘", callback_data=f"val_accept:{valentine_id}")],
            [InlineKeyboardButton(text="Отклонить", callback_data=f"val_reject:{valentine_id}")],
            [InlineKeyboardButton(text="Пожаловаться", callback_data=f"val_report:{valentine_id}")],
        ]
    )


def complaint_reason_keyboard(profile_id: int) -> InlineKeyboardMarkup:
    labels = {
        ComplaintReason.FAKE: "Фейковый профиль",
        ComplaintReason.SPAM: "Спам",
        ComplaintReason.INSULTS: "Оскорбления",
        ComplaintReason.BAD_PHOTO: "Неприемлемое фото",
        ComplaintReason.UNDERAGE: "Пользователь младше 18",
        ComplaintReason.FRAUD: "Мошенничество",
        ComplaintReason.OTHER: "Другое",
    }
    builder = InlineKeyboardBuilder()
    for reason, label in labels.items():
        builder.button(text=label, callback_data=f"complaint_reason:{profile_id}:{reason.value}")
    builder.adjust(1)
    return builder.as_markup()


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Город поиска", callback_data="settings:city")],
            [
                InlineKeyboardButton(text="Мин. возраст", callback_data="settings:min_age"),
                InlineKeyboardButton(text="Макс. возраст", callback_data="settings:max_age"),
            ],
            [
                InlineKeyboardButton(text="Показывать парней", callback_data="settings:gender:male"),
                InlineKeyboardButton(text="Показывать девушек", callback_data="settings:gender:female"),
            ],
            [InlineKeyboardButton(text="Показывать всех", callback_data="settings:gender:any")],
            [InlineKeyboardButton(text="Другие города вкл/выкл", callback_data="settings:toggle_other_cities")],
            [InlineKeyboardButton(text="Назад", callback_data="menu")],
        ]
    )


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Статистика", callback_data="admin:stats")],
            [InlineKeyboardButton(text="Модерация фото", callback_data="admin:photos")],
            [InlineKeyboardButton(text="Жалобы", callback_data="admin:complaints")],
        ]
    )


def photo_moderation_keyboard(photo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Одобрить", callback_data=f"mod_photo:approve:{photo_id}"),
                InlineKeyboardButton(text="Отклонить", callback_data=f"mod_photo:reject:{photo_id}"),
            ],
            [InlineKeyboardButton(text="Забанить пользователя", callback_data=f"mod_photo:ban:{photo_id}")],
        ]
    )
