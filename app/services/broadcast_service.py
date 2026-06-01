from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.services.users_service import list_allowed_users

logger = logging.getLogger(__name__)


@dataclass
class BroadcastResult:
    success: int
    failed: int


async def broadcast_message(bot: Bot, text: str) -> BroadcastResult:
    """Send `text` to every allowed user. Failures (blocked bot, deactivated
    account) are counted, not raised."""
    users = await list_allowed_users()
    success = 0
    failed = 0
    for user in users:
        try:
            await bot.send_message(user.telegram_id, text)
            success += 1
        except TelegramAPIError as exc:
            failed += 1
            logger.warning("Broadcast to %s failed: %s", user.telegram_id, exc)
        # Stay well under Telegram's ~30 msg/sec limit.
        await asyncio.sleep(0.05)
    return BroadcastResult(success=success, failed=failed)
