from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ValentineCreation(StatesGroup):
    choose_mode = State()
    message = State()


class ComplaintCreation(StatesGroup):
    comment = State()

