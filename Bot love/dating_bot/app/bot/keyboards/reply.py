from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Смотреть анкеты"), KeyboardButton(text="Моя анкета")],
            [KeyboardButton(text="Кто меня оценил"), KeyboardButton(text="Валентинки")],
            [KeyboardButton(text="Настройки"), KeyboardButton(text="Помощь")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие",
    )


def done_photo_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Готово")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

