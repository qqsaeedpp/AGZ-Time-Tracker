from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.services import reports_service, settings_service
from app.utils.datetime_utils import TEHRAN_TZ
from app.utils.formatters import format_daily_report
from app.utils.rich import normalize

logger = logging.getLogger(__name__)


async def send_daily_report(bot: Bot) -> None:
    """Build today's report and deliver it to the active report target."""
    target = await settings_service.get_report_target()
    if target is None:
        logger.info("Daily report skipped: no active report target.")
        return

    icons = await settings_service.get_report_icons()
    report = await reports_service.build_daily_report()
    text, entities = normalize(format_daily_report(report, icons))
    try:
        try:
            await bot.send_message(
                chat_id=target.chat_id,
                message_thread_id=target.message_thread_id,
                text=text,
                entities=entities,
                parse_mode=None,
            )
        except TelegramAPIError:
            # Retry as plain text if premium-emoji entities are rejected.
            await bot.send_message(
                chat_id=target.chat_id,
                message_thread_id=target.message_thread_id,
                text=text,
                parse_mode=None,
            )
        logger.info("Daily report sent to chat=%s", target.chat_id)
    except TelegramAPIError as exc:
        logger.error("Failed to send daily report: %s", exc)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TEHRAN_TZ)
    scheduler.add_job(
        send_daily_report,
        trigger=CronTrigger(
            hour=settings.daily_report_hour,
            minute=settings.daily_report_minute,
            timezone=TEHRAN_TZ,
        ),
        kwargs={"bot": bot},
        id="daily_report",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    return scheduler
