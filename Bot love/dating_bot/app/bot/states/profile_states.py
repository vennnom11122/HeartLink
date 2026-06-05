from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ProfileCreation(StatesGroup):
    name = State()
    age = State()
    gender = State()
    looking_for = State()
    city = State()
    bio = State()
    photos = State()
    preview = State()


class ProfileEdit(StatesGroup):
    name = State()
    age = State()
    city = State()
    bio = State()
    photo = State()


class SearchSettingsEdit(StatesGroup):
    city = State()
    min_age = State()
    max_age = State()

