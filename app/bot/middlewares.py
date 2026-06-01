from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from app.services.users_service import get_or_create_user

# Callback actions that must be debounced against rapid repeated taps.
SENSITIVE_ACTIONS = {
    "start_shift",
    "end_shift",
    "daily_report",
    "monthly_report",
    "adm_broadcast",
    "adm_add_access",
    "adm_remove_access",
    "adm_wipe",
    "wipe_confirm_1",
    "wipe_confirm_2",
}


class UserContextMiddleware(BaseMiddleware):
    """Resolve (and lazily create) the DB user for each incoming event and make
    it available to handlers as `db_user`."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user") or getattr(event, "from_user", None)
        if tg_user is not None and not tg_user.is_bot:
            data["db_user"] = await get_or_create_user(
                telegram_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
            )
        return await handler(event, data)


class AntiSpamMiddleware(BaseMiddleware):
    """Drop duplicate sensitive callbacks fired within `window` seconds."""

    def __init__(self, window: float = 2.0) -> None:
        self.window = window
        self._last: dict[tuple[int, str], float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        action = event.data or ""
        if action in SENSITIVE_ACTIONS and event.from_user is not None:
            key = (event.from_user.id, action)
            now = time.monotonic()
            last = self._last.get(key)
            if last is not None and (now - last) < self.window:
                await event.answer("لطفاً چند لحظه صبر کنید.", show_alert=False)
                return None
            self._last[key] = now
        return await handler(event, data)
