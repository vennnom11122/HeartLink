from __future__ import annotations

from app.config import Settings


def test_settings_normalizes_railway_postgres_url() -> None:
    settings = Settings(
        BOT_TOKEN="123456:abcdefghijklmnopqrstuvwxyz",
        DATABASE_URL="postgresql://user:password@host:5432/db",
        REDIS_URL="redis://localhost:6379/0",
    )

    assert settings.database_url == "postgresql+asyncpg://user:password@host:5432/db"
