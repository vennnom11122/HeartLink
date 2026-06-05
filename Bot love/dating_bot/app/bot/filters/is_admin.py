from __future__ import annotations

from typing import Any

from aiogram.filters import BaseFilter
from aiogram.types import Message


class IsAdmin(BaseFilter):
    async def __call__(self, message: Message, current_user: Any | None = None) -> bool:
        return bool(current_user and (current_user.is_admin or current_user.is_moderator))

