from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.keyboards import CB
from app.database.models import User
from app.handlers.common import NO_ACCESS, send_report
from app.services import reports_service, settings_service
from app.utils.formatters import format_daily_report, format_monthly_report

router = Router(name="reports")

# Shown when a non-manager tries to open a report via a stale/forged callback
# (the buttons are hidden for them, so this is the defensive backstop).
NO_REPORT_ACCESS = "شما به گزارش‌ها دسترسی ندارید."


@router.callback_query(F.data == CB.DAILY_REPORT)
async def on_daily_report(callback: CallbackQuery, db_user: User) -> None:
    if not db_user.is_allowed:
        await callback.answer(NO_ACCESS, show_alert=True)
        return
    # Reports are manager-only. Reject crafted/stale callbacks from normal users.
    if not db_user.is_owner:
        await callback.answer(NO_REPORT_ACCESS, show_alert=True)
        return

    icons = await settings_service.get_report_icons()
    report = await reports_service.build_daily_report()
    # Reports are ALWAYS sent as a new message (never edit/delete the menu).
    await send_report(callback, format_daily_report(report, icons))


@router.callback_query(F.data == CB.MONTHLY_REPORT)
async def on_monthly_report(callback: CallbackQuery, db_user: User) -> None:
    if not db_user.is_allowed:
        await callback.answer(NO_ACCESS, show_alert=True)
        return
    if not db_user.is_owner:
        await callback.answer(NO_REPORT_ACCESS, show_alert=True)
        return

    icons = await settings_service.get_report_icons()
    report = await reports_service.build_monthly_report()
    await send_report(callback, format_monthly_report(report, icons))
