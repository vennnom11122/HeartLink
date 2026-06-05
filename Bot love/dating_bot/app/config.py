from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field("", alias="BOT_TOKEN")
    database_url: str = Field("", alias="DATABASE_URL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")

    app_env: str = Field("local", alias="APP_ENV")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    admins: list[int] = Field(default_factory=list, alias="ADMINS")

    daily_views_limit: int = Field(100, alias="DAILY_VIEWS_LIMIT")
    daily_ratings_limit: int = Field(50, alias="DAILY_RATINGS_LIMIT")
    daily_valentines_limit: int = Field(3, alias="DAILY_VALENTINES_LIMIT")
    daily_complaints_limit: int = Field(10, alias="DAILY_COMPLAINTS_LIMIT")

    premium_daily_views_limit: int = Field(500, alias="PREMIUM_DAILY_VIEWS_LIMIT")
    premium_daily_ratings_limit: int = Field(300, alias="PREMIUM_DAILY_RATINGS_LIMIT")
    premium_daily_valentines_limit: int = Field(20, alias="PREMIUM_DAILY_VALENTINES_LIMIT")
    premium_daily_complaints_limit: int = Field(30, alias="PREMIUM_DAILY_COMPLAINTS_LIMIT")

    min_public_rating_count: int = Field(5, alias="MIN_PUBLIC_RATING_COUNT")
    min_public_rating: float = Field(5.0, alias="MIN_PUBLIC_RATING")
    complaint_auto_hide_threshold: int = Field(5, alias="COMPLAINT_AUTO_HIDE_THRESHOLD")
    profile_recent_view_days: int = Field(14, alias="PROFILE_RECENT_VIEW_DAYS")
    rating_repeat_cooldown_days: int = Field(30, alias="RATING_REPEAT_COOLDOWN_DAYS")
    valentine_ttl_days: int = Field(7, alias="VALENTINE_TTL_DAYS")

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
