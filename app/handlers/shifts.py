from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.keyboards import CB
from app.database.models import User
from app.handlers.common import NO_ACCESS, get_text
from app.services import shifts_service
from app.utils.formatters import format_shift_end

logger = logging.getLogger(__name__)

router = Router(name="shifts")


@router.callback_query(F.data == CB.START_SHIFT)
async def on_start_shift(callback: CallbackQuery, db_user: User) -> None:
    if not db_user.is_allowed:
        await callback.answer(NO_ACCESS, show_alert=True)
        return

    result = await shifts_service.start_shift(db_user.id)
    if result.already_active:
        await callback.message.answer(await get_text("start_already"))
    else:
        await callback.message.answer(await get_text("start_ok"))
        logger.info("Shift started for user_id=%s", db_user.id)
    await callback.answer()


@router.callback_query(F.data == CB.END_SHIFT)
async def on_end_shift(callback: CallbackQuery, db_user: User) -> None:
    if not db_user.is_allowed:
        await callback.answer(NO_ACCESS, show_alert=True)
        return

    result = await shifts_service.end_shift(db_user.id)
    if not result.closed:
        await callback.message.answer(await get_text("end_none"))
    else:
        await callback.message.answer(format_shift_end(result.minutes or 0))
        logger.info(
            "Shift closed for user_id=%s (%s min)", db_user.id, result.minutes
        )
    await callback.answer()
