from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.database.models import User
from app.handlers.common import NO_ACCESS, show_main_menu

router = Router(name="start")


@router.message(CommandStart())
async def on_start(message: Message, db_user: User) -> None:
    if not db_user.is_allowed:
        await message.answer(NO_ACCESS)
        return
    await show_main_menu(message, db_user)
