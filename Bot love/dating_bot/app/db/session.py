from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings


def make_engine(settings: Settings):
    return create_async_engine(settings.database_url, pool_pre_ping=True)


def make_session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(make_engine(settings), expire_on_commit=False)


@asynccontextmanager
async def session_scope(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

