from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import (
    CB,
    DEFAULT_BUTTONS,
    admin_panel,
    back_to_admin,
    wipe_confirm_step_1,
    wipe_confirm_step_2,
)
from app.bot.states import AdminFlow
from app.database.models import User
from app.handlers.common import DEFAULT_TEXTS, menu_markup
from app.services import broadcast_service, settings_service, users_service

logger = logging.getLogger(__name__)

router = Router(name="admin")

GROUP_TYPES = {"group", "supergroup"}


def _is_owner(user: User | None) -> bool:
    return bool(user and user.is_owner)


# ----------------------------- Panel -----------------------------
@router.callback_query(F.data == CB.ADMIN_PANEL)
async def open_panel(callback: CallbackQuery, db_user: User, state: FSMContext) -> None:
    if not _is_owner(db_user):
        await callback.answer("دسترسی مدیریت ندارید.", show_alert=True)
        return
    await state.clear()
    await callback.message.answer("پنل مدیریت:", reply_markup=admin_panel())
    await callback.answer()


@router.callback_query(F.data == CB.ADM_BACK)
async def back_to_menu(callback: CallbackQuery, db_user: User, state: FSMContext) -> None:
    if not _is_owner(db_user):
        await callback.answer()
        return
    await state.clear()
    await callback.message.answer(
        "منوی اصلی:", reply_markup=await menu_markup(db_user)
    )
    await callback.answer()


# ----------------------------- Broadcast -----------------------------
@router.callback_query(F.data == CB.ADM_BROADCAST)
async def broadcast_start(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        await callback.answer("دسترسی مدیریت ندارید.", show_alert=True)
        return
    await state.set_state(AdminFlow.waiting_broadcast_message)
    await callback.message.answer(
        "متن پیام همگانی را ارسال کنید:", reply_markup=back_to_admin()
    )
    await callback.answer()


@router.message(AdminFlow.waiting_broadcast_message)
async def broadcast_send(
    message: Message, db_user: User, state: FSMContext, bot: Bot
) -> None:
    if not _is_owner(db_user):
        return
    text = message.text or message.caption
    if not text:
        await message.answer("لطفاً یک پیام متنی ارسال کنید.")
        return
    await state.clear()
    result = await broadcast_service.broadcast_message(bot, text)
    await message.answer(
        "ارسال همگانی انجام شد.\n\n"
        f"موفق:\n{result.success}\n\n"
        f"ناموفق:\n{result.failed}",
        reply_markup=admin_panel(),
    )
    logger.info(
        "Broadcast by owner=%s success=%s failed=%s",
        db_user.telegram_id,
        result.success,
        result.failed,
    )


# ----------------------------- Add access -----------------------------
@router.callback_query(F.data == CB.ADM_ADD_ACCESS)
async def add_access_start(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        await callback.answer("دسترسی مدیریت ندارید.", show_alert=True)
        return
    await state.set_state(AdminFlow.waiting_access_user_id)
    await callback.message.answer(
        "آیدی عددی کاربر را برای فعال‌سازی دسترسی ارسال کنید:",
        reply_markup=back_to_admin(),
    )
    await callback.answer()


@router.message(AdminFlow.waiting_access_user_id)
async def add_access_apply(
    message: Message, db_user: User, state: FSMContext, bot: Bot
) -> None:
    if not _is_owner(db_user):
        return
    target_id = _parse_user_id(message.text)
    if target_id is None:
        await message.answer("آیدی عددی معتبر نیست. دوباره ارسال کنید.")
        return
    await state.clear()
    await users_service.grant_access(target_id)
    await _notify_user(bot, target_id, "دسترسی شما برای استفاده از ربات فعال شد.")
    await message.answer(
        f"دسترسی کاربر {target_id} فعال شد.", reply_markup=admin_panel()
    )
    logger.info("Access granted to %s by owner=%s", target_id, db_user.telegram_id)


# ----------------------------- Remove access -----------------------------
@router.callback_query(F.data == CB.ADM_REMOVE_ACCESS)
async def remove_access_start(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        await callback.answer("دسترسی مدیریت ندارید.", show_alert=True)
        return
    await state.set_state(AdminFlow.waiting_remove_access_user_id)
    await callback.message.answer(
        "آیدی عددی کاربر را برای حذف دسترسی ارسال کنید:",
        reply_markup=back_to_admin(),
    )
    await callback.answer()


@router.message(AdminFlow.waiting_remove_access_user_id)
async def remove_access_apply(
    message: Message, db_user: User, state: FSMContext, bot: Bot
) -> None:
    if not _is_owner(db_user):
        return
    target_id = _parse_user_id(message.text)
    if target_id is None:
        await message.answer("آیدی عددی معتبر نیست. دوباره ارسال کنید.")
        return
    await state.clear()
    removed = await users_service.revoke_access(target_id)
    if removed:
        await _notify_user(bot, target_id, "دسترسی شما به ربات غیرفعال شد.")
        await message.answer(
            f"دسترسی کاربر {target_id} حذف شد.", reply_markup=admin_panel()
        )
    else:
        await message.answer(
            "کاربری با این آیدی یافت نشد.", reply_markup=admin_panel()
        )
    logger.info("Access revoked for %s by owner=%s", target_id, db_user.telegram_id)


# ----------------------------- Custom texts -----------------------------
@router.callback_query(F.data == CB.ADM_CUSTOM_TEXT)
async def custom_text_start(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        await callback.answer("دسترسی مدیریت ندارید.", show_alert=True)
        return
    await state.set_state(AdminFlow.waiting_custom_text_key)
    keys = "\n".join(f"• {k}" for k in DEFAULT_TEXTS)
    await callback.message.answer(
        "کلید متن مورد نظر را ارسال کنید:\n\n" + keys,
        reply_markup=back_to_admin(),
    )
    await callback.answer()


@router.message(AdminFlow.waiting_custom_text_key)
async def custom_text_key(
    message: Message, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        return
    key = (message.text or "").strip()
    if key not in DEFAULT_TEXTS:
        await message.answer("کلید نامعتبر است. یکی از کلیدهای فهرست را ارسال کنید.")
        return
    await state.update_data(text_key=key)
    await state.set_state(AdminFlow.waiting_custom_text_value)
    await message.answer(
        f"متن جدید برای «{key}» را ارسال کنید:", reply_markup=back_to_admin()
    )


@router.message(AdminFlow.waiting_custom_text_value)
async def custom_text_value(
    message: Message, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        return
    value = message.text
    if not value:
        await message.answer("لطفاً یک متن ارسال کنید.")
        return
    data = await state.get_data()
    key = data.get("text_key")
    await state.clear()
    await settings_service.set_custom_value(f"text:{key}", value)
    await message.answer("متن با موفقیت ذخیره شد.", reply_markup=admin_panel())


# ----------------------------- Custom buttons -----------------------------
@router.callback_query(F.data == CB.ADM_CUSTOM_BUTTON)
async def custom_button_start(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        await callback.answer("دسترسی مدیریت ندارید.", show_alert=True)
        return
    await state.set_state(AdminFlow.waiting_custom_button_key)
    keys = "\n".join(f"• {k}" for k in DEFAULT_BUTTONS)
    await callback.message.answer(
        "کلید دکمه مورد نظر را ارسال کنید:\n\n" + keys,
        reply_markup=back_to_admin(),
    )
    await callback.answer()


@router.message(AdminFlow.waiting_custom_button_key)
async def custom_button_key(
    message: Message, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        return
    key = (message.text or "").strip()
    if key not in DEFAULT_BUTTONS:
        await message.answer("کلید نامعتبر است. یکی از کلیدهای فهرست را ارسال کنید.")
        return
    await state.update_data(button_key=key)
    await state.set_state(AdminFlow.waiting_custom_button_value)
    await message.answer(
        f"عنوان جدید برای دکمه «{key}» را ارسال کنید:",
        reply_markup=back_to_admin(),
    )


@router.message(AdminFlow.waiting_custom_button_value)
async def custom_button_value(
    message: Message, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        return
    value = (message.text or "").strip()
    if not value:
        await message.answer("لطفاً یک عنوان ارسال کنید.")
        return
    data = await state.get_data()
    key = data.get("button_key")
    await state.clear()
    await settings_service.set_custom_value(f"button:{key}", value)
    await message.answer("عنوان دکمه ذخیره شد.", reply_markup=admin_panel())


# ----------------------------- Wipe (two-step) -----------------------------
@router.callback_query(F.data == CB.ADM_WIPE)
async def wipe_step1(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        await callback.answer("دسترسی مدیریت ندارید.", show_alert=True)
        return
    await state.set_state(AdminFlow.confirm_delete_step_1)
    await callback.message.answer(
        "آیا مطمئن هستید؟", reply_markup=wipe_confirm_step_1()
    )
    await callback.answer()


@router.callback_query(F.data == CB.WIPE_CONFIRM_1, AdminFlow.confirm_delete_step_1)
async def wipe_step2(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        await callback.answer()
        return
    await state.set_state(AdminFlow.confirm_delete_step_2)
    await callback.message.answer(
        "این عملیات غیرقابل بازگشت است.\n"
        "برای تایید نهایی، تایید نهایی را انتخاب کنید.",
        reply_markup=wipe_confirm_step_2(),
    )
    await callback.answer()


@router.callback_query(F.data == CB.WIPE_CONFIRM_2, AdminFlow.confirm_delete_step_2)
async def wipe_confirm(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        await callback.answer()
        return
    await state.clear()
    await settings_service.wipe_operational_data()
    await callback.message.answer(
        "تمامی اطلاعات عملیاتی پاک شد.", reply_markup=admin_panel()
    )
    logger.warning("Operational data wiped by owner=%s", db_user.telegram_id)
    await callback.answer()


@router.callback_query(F.data == CB.WIPE_CANCEL)
async def wipe_cancel(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    await state.clear()
    await callback.message.answer("عملیات لغو شد.", reply_markup=admin_panel())
    await callback.answer()


# ----------------------------- Group report target -----------------------------
@router.message(F.chat.type.in_(GROUP_TYPES), F.text == "نصب")
async def install_report_target(message: Message, db_user: User) -> None:
    if not _is_owner(db_user):
        return
    await settings_service.install_report_target(
        chat_id=message.chat.id,
        message_thread_id=message.message_thread_id,
        installed_by=message.from_user.id,
    )
    await message.answer("نصب گزارش در این مکان انجام شد. گزارش روزانه اینجا ارسال می‌شود.")
    logger.info(
        "Report target installed chat=%s thread=%s",
        message.chat.id,
        message.message_thread_id,
    )


@router.message(F.chat.type.in_(GROUP_TYPES), F.text == "حذف")
async def remove_report_target(message: Message, db_user: User) -> None:
    if not _is_owner(db_user):
        return
    await settings_service.remove_report_target()
    await message.answer("ارسال گزارش غیرفعال شد.")
    logger.info("Report target removed by owner=%s", message.from_user.id)


# ----------------------------- Helpers -----------------------------
def _parse_user_id(text: str | None) -> int | None:
    if not text:
        return None
    text = text.strip()
    if not text.lstrip("-").isdigit():
        return None
    value = int(text)
    return value if value > 0 else None


async def _notify_user(bot: Bot, telegram_id: int, text: str) -> None:
    try:
        await bot.send_message(telegram_id, text)
    except TelegramAPIError as exc:
        logger.warning("Could not notify user %s: %s", telegram_id, exc)
