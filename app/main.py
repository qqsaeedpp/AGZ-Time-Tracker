from __future__ import annotations

import asyncio
import logging

from app.bot.router import create_bot, create_dispatcher
from app.config import setup_logging
from app.database.db import engine
from app.scheduler.daily_report import setup_scheduler

logger = logging.getLogger(__name__)


async def main() -> None:
    setup_logging()
    logger.info("Starting AGZ Support Time bot...")

    bot = create_bot()
    dp = create_dispatcher()
    scheduler = setup_scheduler(bot)

    scheduler.start()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
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
