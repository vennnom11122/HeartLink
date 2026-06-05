from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from redis.asyncio import Redis


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, redis: Redis, *, ttl_seconds: int = 1) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = getattr(getattr(event, "from_user", None), "id", None)
        if user_id is None:
            return await handler(event, data)

        key = f"throttle:{user_id}"
        allowed = await self.redis.set(key, "1", ex=self.ttl_seconds, nx=True)
        if allowed:
            return await handler(event, data)

        if isinstance(event, CallbackQuery):
            await event.answer("Слишком быстро. Попробуй через секунду.", show_alert=False)
        elif isinstance(event, Message):
            await event.answer("Слишком быстро. Попробуй через секунду.")
        return None

