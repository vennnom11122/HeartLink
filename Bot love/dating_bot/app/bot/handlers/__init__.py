from __future__ import annotations

from aiogram import Router

from app.bot.handlers import admin, complaints, matches, profile, rating, search, settings, start, valentines


def setup_routers() -> Router:
    router = Router()
    router.include_router(start.router)
    router.include_router(profile.router)
    router.include_router(search.router)
    router.include_router(rating.router)
    router.include_router(valentines.router)
    router.include_router(matches.router)
    router.include_router(settings.router)
    router.include_router(complaints.router)
    router.include_router(admin.router)
    return router
