from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.types import BotCommand

from app.bot.router import create_bot, create_dispatcher
from app.config import setup_logging
from app.database.db import engine
from app.scheduler.daily_report import setup_scheduler

logger = logging.getLogger(__name__)


async def _set_commands(bot: Bot) -> None:
    """Register the bot's command menu. Only /start is exposed — every other
    action is reachable through inline buttons, so no extra commands are added."""
    await bot.set_my_commands([BotCommand(command="start", description="شروع ربات")])


async def main() -> None:
    setup_logging()
    logger.info("Starting AGZ Support Time bot...")

    bot = create_bot()
    dp = create_dispatcher()
    scheduler = setup_scheduler(bot)

    scheduler.start()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await _set_commands(bot)
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        await engine.dispose()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
