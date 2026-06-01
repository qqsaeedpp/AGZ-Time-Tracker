from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.keyboards import CB
from app.database.models import User
from app.handlers.common import NO_ACCESS, get_text
from app.services import reports_service
from app.utils.formatters import format_daily_report, format_monthly_report

router = Router(name="reports")


@router.callback_query(F.data == CB.DAILY_REPORT)
async def on_daily_report(callback: CallbackQuery, db_user: User) -> None:
    if not db_user.is_allowed:
        await callback.answer(NO_ACCESS, show_alert=True)
        return

    if not db_user.is_owner:
        await callback.message.answer(await get_text("daily_user_notice"))
        await callback.answer()
        return

    report = await reports_service.build_daily_report()
    await callback.message.answer(format_daily_report(report))
    await callback.answer()


@router.callback_query(F.data == CB.MONTHLY_REPORT)
async def on_monthly_report(callback: CallbackQuery, db_user: User) -> None:
    if not db_user.is_allowed:
        await callback.answer(NO_ACCESS, show_alert=True)
        return

    if not db_user.is_owner:
        await callback.message.answer(await get_text("monthly_user_notice"))
        await callback.answer()
        return

    report = await reports_service.build_monthly_report()
    await callback.message.answer(format_monthly_report(report))
    await callback.answer()
