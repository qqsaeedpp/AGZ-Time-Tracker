from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.database.models import User
from app.handlers.common import NO_ACCESS, get_text, menu_markup

router = Router(name="start")


@router.message(CommandStart())
async def on_start(message: Message, db_user: User) -> None:
    if not db_user.is_allowed:
        await message.answer(NO_ACCESS)
        return
    await message.answer(
        await get_text("welcome"),
        reply_markup=await menu_markup(db_user),
    )
