from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.keyboards import CB
from app.database.models import User
from app.handlers.common import NO_ACCESS, menu_markup, render, safe_edit_or_send
from app.services import shifts_service

logger = logging.getLogger(__name__)

router = Router(name="shifts")


@router.callback_query(F.data == CB.START_SHIFT)
async def on_start_shift(callback: CallbackQuery, db_user: User) -> None:
    if not db_user.is_allowed:
        await callback.answer(NO_ACCESS, show_alert=True)
        return

    result = await shifts_service.start_shift(db_user.id)
    if result.already_active:
        content = await render("start_already")
    else:
        content = await render("start_ok")
        logger.info("Shift started for user_id=%s", db_user.id)
    await safe_edit_or_send(
        callback, content, reply_markup=await menu_markup(db_user)
    )


@router.callback_query(F.data == CB.END_SHIFT)
async def on_end_shift(callback: CallbackQuery, db_user: User) -> None:
    if not db_user.is_allowed:
        await callback.answer(NO_ACCESS, show_alert=True)
        return

    result = await shifts_service.end_shift(db_user.id)
    if not result.closed:
        content = await render("end_none")
    else:
        content = await render("end_done", {"minutes": result.minutes or 0})
        logger.info(
            "Shift closed for user_id=%s (%s min)", db_user.id, result.minutes
        )
    await safe_edit_or_send(
        callback, content, reply_markup=await menu_markup(db_user)
    )
