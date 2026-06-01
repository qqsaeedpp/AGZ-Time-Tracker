from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.middlewares import AntiSpamMiddleware, UserContextMiddleware
from app.config import settings
from app.handlers import admin, common, reports, shifts, start


def create_bot() -> Bot:
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=None),
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    # Inject the DB user on every message/callback.
    dp.message.middleware(UserContextMiddleware())
    dp.callback_query.middleware(UserContextMiddleware())
    # Debounce sensitive callbacks.
    dp.callback_query.middleware(AntiSpamMiddleware())

    # Order matters: specific handlers first, generic fallback (common) last.
    dp.include_router(start.router)
    dp.include_router(shifts.router)
    dp.include_router(reports.router)
    dp.include_router(admin.router)
    dp.include_router(common.router)
    return dp
