from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.keyboards import CB
from app.database.models import User
from app.handlers.common import NO_ACCESS, menu_markup, render, safe_edit_or_send
from app.services import reports_service
from app.utils.formatters import format_daily_report, format_monthly_report

router = Router(name="reports")


@router.callback_query(F.data == CB.DAILY_REPORT)
async def on_daily_report(callback: CallbackQuery, db_user: User) -> None:
    if not db_user.is_allowed:
        await callback.answer(NO_ACCESS, show_alert=True)
        return

    markup = await menu_markup(db_user)
    if not db_user.is_owner:
        content = await render("daily_user_notice")
        await safe_edit_or_send(callback, content, reply_markup=markup)
        return

    report = await reports_service.build_daily_report()
    await safe_edit_or_send(
        callback, format_daily_report(report), reply_markup=markup
    )


@router.callback_query(F.data == CB.MONTHLY_REPORT)
async def on_monthly_report(callback: CallbackQuery, db_user: User) -> None:
    if not db_user.is_allowed:
        await callback.answer(NO_ACCESS, show_alert=True)
        return

    markup = await menu_markup(db_user)
    if not db_user.is_owner:
        content = await render("monthly_user_notice")
        await safe_edit_or_send(callback, content, reply_markup=markup)
        return

    report = await reports_service.build_monthly_report()
    await safe_edit_or_send(
        callback, format_monthly_report(report), reply_markup=markup
    )
