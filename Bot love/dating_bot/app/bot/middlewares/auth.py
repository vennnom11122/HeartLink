from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.config import Settings
from app.db.repositories.users import UserRepository


class AuthMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = None
        if isinstance(event, (Message, CallbackQuery)):
            tg_user = event.from_user

        if tg_user is not None and "session" in data:
            repo = UserRepository(data["session"])
            data["current_user"] = await repo.upsert_from_telegram(tg_user, admin_ids=set(self.settings.admins))

        return await handler(event, data)

