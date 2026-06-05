from __future__ import annotations

import asyncio
import logging
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aiogram.exceptions import TelegramUnauthorizedError
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.handlers import setup_routers
from app.bot.middlewares.auth import AuthMiddleware
from app.bot.middlewares.db import DbSessionMiddleware
from app.bot.middlewares.throttling import ThrottlingMiddleware
from app.config import get_settings
from app.db.session import make_session_factory, session_scope
from app.services.limit_service import LimitService
from app.services.valentine_service import ValentineService
from app.utils.logger import configure_logging


BOT_TOKEN_RE = re.compile(r"^\d+:[A-Za-z0-9_-]{20,}$")


def _validate_runtime_settings(settings) -> None:
    problems: list[str] = []
    token = settings.bot_token.strip()
    if not token or token == "replace-with-your-botfather-token":
        problems.append("BOT_TOKEN не указан. Получи токен у @BotFather и запиши его в dating_bot\\.env.")
    elif not BOT_TOKEN_RE.match(token):
        problems.append("BOT_TOKEN выглядит неверно. Проверь значение в dating_bot\\.env.")
    if not settings.database_url.strip():
        problems.append("DATABASE_URL не указан. Для локального запуска используй PostgreSQL URL из .env.example.")
    if not settings.redis_url.strip():
        problems.append("REDIS_URL не указан. Для локального запуска обычно нужен redis://localhost:6379/0.")
    if problems:
        raise RuntimeError(
            "Не заполнена конфигурация проекта:\n"
            + "\n".join(f"- {problem}" for problem in problems)
            + "\n\nСоздай/исправь файл: dating_bot\\.env"
        )


async def _preflight_services(
    redis: Redis,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    redis_url: str,
) -> None:
    try:
        await redis.ping()
    except Exception as exc:
        raise RuntimeError(
            "Не удалось подключиться к Redis.\n"
            f"REDIS_URL={redis_url}\n\n"
            "Запусти Redis, например:\n"
            "  docker compose up -d redis\n"
            "или запусти весь проект через:\n"
            "  docker compose up --build"
        ) from exc

    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise RuntimeError(
            "Не удалось подключиться к PostgreSQL.\n\n"
            "Запусти базу, например:\n"
            "  docker compose up -d postgres\n"
            "или запусти весь проект через:\n"
            "  docker compose up --build"
        ) from exc

    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1 FROM users LIMIT 1"))
    except Exception as exc:
        raise RuntimeError(
            "PostgreSQL доступен, но схема базы ещё не создана.\n\n"
            "Примени миграции и заполни города:\n"
            "  .\\.venv\\Scripts\\python.exe -m alembic upgrade head\n"
            "  .\\.venv\\Scripts\\python.exe scripts\\seed_cities.py"
        ) from exc


async def main() -> None:
    settings = get_settings()
    _validate_runtime_settings(settings)
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)

    session_factory = make_session_factory(settings)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    await _preflight_services(redis, session_factory, redis_url=settings.redis_url)
    storage = RedisStorage(redis=redis)

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=storage)
    dp["settings"] = settings

    db_middleware = DbSessionMiddleware(session_factory)
    auth_middleware = AuthMiddleware(settings)
    throttle_middleware = ThrottlingMiddleware(redis)

    dp.update.middleware(db_middleware)
    dp.message.middleware(auth_middleware)
    dp.callback_query.middleware(auth_middleware)
    dp.message.middleware(throttle_middleware)
    dp.callback_query.middleware(throttle_middleware)

    dp.include_router(setup_routers())

    scheduler = AsyncIOScheduler(timezone="UTC")

    async def expire_valentines_job() -> None:
        async with session_scope(session_factory) as session:
            service = ValentineService(session, settings, LimitService(session, settings))
            expired = await service.expire_old()
            if expired:
                logger.info("Expired valentines: %s", expired)

    scheduler.add_job(expire_valentines_job, "interval", hours=6, id="expire_valentines")
    scheduler.start()

    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except TelegramUnauthorizedError:
        print(
            "Telegram отклонил BOT_TOKEN. Проверь токен в dating_bot\\.env или перевыпусти его через @BotFather.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    except ValidationError as exc:
        print(f"Ошибка в .env: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
