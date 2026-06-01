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
from app.handlers.common import (
    menu_markup,
    render,
    safe_edit_or_send,
    show_main_menu,
    today_replacements,
)
from app.services import broadcast_service, settings_service, users_service
from app.utils.rich import SPECS, dump_formatting

logger = logging.getLogger(__name__)

router = Router(name="admin")

GROUP_TYPES = {"group", "supergroup"}

# Tokens the owner may send to skip attaching a premium emoji to a custom text.
SKIP_TOKENS = {"-", "خیر", "نه", "رد", "بدون", "skip"}

PANEL_TITLE = "⚙️ پنل مدیریت\n\nیکی از گزینه‌ها را انتخاب کنید:"


def _is_owner(user: User | None) -> bool:
    return bool(user and user.is_owner)


def _preview_replacements() -> dict[str, object]:
    """Cover every placeholder token so a saved-text preview never shows raw
    ``{token}`` text, regardless of which key was edited."""
    replacements = today_replacements()
    replacements["minutes"] = 0
    return replacements


# ----------------------------- Panel -----------------------------
@router.callback_query(F.data == CB.ADMIN_PANEL)
async def open_panel(callback: CallbackQuery, db_user: User, state: FSMContext) -> None:
    if not _is_owner(db_user):
        await callback.answer("دسترسی مدیریت ندارید.", show_alert=True)
        return
    await state.clear()
    await safe_edit_or_send(callback, PANEL_TITLE, reply_markup=admin_panel())


@router.callback_query(F.data == CB.ADM_BACK)
async def back_to_menu(callback: CallbackQuery, db_user: User, state: FSMContext) -> None:
    if not _is_owner(db_user):
        await callback.answer()
        return
    await state.clear()
    await show_main_menu(callback, db_user)


# ----------------------------- Broadcast -----------------------------
@router.callback_query(F.data == CB.ADM_BROADCAST)
async def broadcast_start(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        await callback.answer("دسترسی مدیریت ندارید.", show_alert=True)
        return
    await state.set_state(AdminFlow.waiting_broadcast_message)
    await safe_edit_or_send(
        callback,
        "📣 متن پیام همگانی را ارسال کنید:",
        reply_markup=back_to_admin(),
    )


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
    await safe_edit_or_send(
        message,
        "✅ ارسال همگانی انجام شد.\n\n"
        f"موفق: {result.success}\n"
        f"ناموفق: {result.failed}",
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
    await safe_edit_or_send(
        callback,
        "➕ آیدی عددی کاربر را برای فعال‌سازی دسترسی ارسال کنید:",
        reply_markup=back_to_admin(),
    )


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
    await safe_edit_or_send(
        message,
        f"✅ دسترسی کاربر {target_id} فعال شد.",
        reply_markup=admin_panel(),
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
    await safe_edit_or_send(
        callback,
        "➖ آیدی عددی کاربر را برای حذف دسترسی ارسال کنید:",
        reply_markup=back_to_admin(),
    )


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
        text = f"✅ دسترسی کاربر {target_id} حذف شد."
    else:
        text = "کاربری با این آیدی یافت نشد."
    await safe_edit_or_send(message, text, reply_markup=admin_panel())
    logger.info("Access revoked for %s by owner=%s", target_id, db_user.telegram_id)


# ----------------------------- Custom texts (+ premium emoji) -----------------------------
@router.callback_query(F.data == CB.ADM_CUSTOM_TEXT)
async def custom_text_start(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        await callback.answer("دسترسی مدیریت ندارید.", show_alert=True)
        return
    await state.set_state(AdminFlow.waiting_custom_text_key)
    keys = "\n".join(f"• {key} — {spec.label}" for key, spec in SPECS.items())
    await safe_edit_or_send(
        callback,
        "✏️ کلید متن مورد نظر را ارسال کنید:\n\n" + keys,
        reply_markup=back_to_admin(),
    )


@router.message(AdminFlow.waiting_custom_text_key)
async def custom_text_key(
    message: Message, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        return
    key = (message.text or "").strip()
    if key not in SPECS:
        await message.answer("کلید نامعتبر است. یکی از کلیدهای فهرست را ارسال کنید.")
        return
    await state.update_data(text_key=key)
    await state.set_state(AdminFlow.waiting_custom_text_value)
    await message.answer(
        f"متن جدید برای «{SPECS[key].label}» را ارسال کنید:",
        reply_markup=back_to_admin(),
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
    await state.update_data(text_value=value)
    await state.set_state(AdminFlow.waiting_custom_text_emoji)
    await message.answer(
        "حالا ایموجی پریمیوم (Custom Emoji) را به یکی از این روش‌ها ارسال کنید:\n\n"
        "• خودِ ایموجی پریمیوم را بفرستید\n"
        "• یا شناسهٔ عددی (custom_emoji_id) را ارسال کنید\n\n"
        "اگر نمی‌خواهید ایموجی پریمیوم تنظیم شود، عبارت «-» را بفرستید "
        "تا از ایموجی معمولی استفاده شود.",
        reply_markup=back_to_admin(),
    )


@router.message(AdminFlow.waiting_custom_text_emoji)
async def custom_text_emoji(
    message: Message, db_user: User, state: FSMContext, bot: Bot
) -> None:
    if not _is_owner(db_user):
        return

    custom_emoji_id = _extract_custom_emoji_id(message)
    text = (message.text or "").strip()

    if custom_emoji_id is None:
        if text in SKIP_TOKENS:
            custom_emoji_id = None  # fall back to the normal emoji
        elif text.isdigit():
            custom_emoji_id = text
        else:
            await message.answer(
                "ورودی نامعتبر است. یک ایموجی پریمیوم، یک شناسهٔ عددی، "
                "یا «-» برای رد کردن ارسال کنید.",
                reply_markup=back_to_admin(),
            )
            return  # stay in this state

    if custom_emoji_id is not None and not await _is_valid_custom_emoji(
        bot, custom_emoji_id
    ):
        await message.answer(
            "شناسهٔ ایموجی پریمیوم نامعتبر است یا در دسترس نیست. "
            "دوباره ارسال کنید یا «-» را بفرستید.",
            reply_markup=back_to_admin(),
        )
        return  # stay in this state

    data = await state.get_data()
    key = data.get("text_key")
    value = data.get("text_value")
    await state.clear()

    formatting = dump_formatting(dict(SPECS[key].default_formatting))
    await settings_service.set_text_setting(key, value, custom_emoji_id, formatting)

    note = (
        "با ایموجی پریمیوم" if custom_emoji_id else "با ایموجی معمولی"
    )
    await message.answer(f"✅ متن «{SPECS[key].label}» ذخیره شد ({note}).")
    # Live preview of the saved text exactly as users will see it.
    preview = await render(key, _preview_replacements())
    await safe_edit_or_send(message, preview, reply_markup=admin_panel())
    logger.info(
        "Custom text saved key=%s premium=%s by owner=%s",
        key,
        bool(custom_emoji_id),
        db_user.telegram_id,
    )


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
    await safe_edit_or_send(
        callback,
        "🔘 کلید دکمه مورد نظر را ارسال کنید:\n\n" + keys + "\n\n"
        "توجه: متن دکمه‌ها فقط از ایموجی معمولی پشتیبانی می‌کند "
        "(ایموجی پریمیوم در دکمه‌ها مجاز نیست).",
        reply_markup=back_to_admin(),
    )


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
    await safe_edit_or_send(
        message, "✅ عنوان دکمه ذخیره شد.", reply_markup=admin_panel()
    )


# ----------------------------- Wipe (two-step) -----------------------------
@router.callback_query(F.data == CB.ADM_WIPE)
async def wipe_step1(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        await callback.answer("دسترسی مدیریت ندارید.", show_alert=True)
        return
    await state.set_state(AdminFlow.confirm_delete_step_1)
    await safe_edit_or_send(
        callback,
        "🧹 آیا از پاک کردن تمامی اطلاعات عملیاتی مطمئن هستید؟",
        reply_markup=wipe_confirm_step_1(),
    )


@router.callback_query(F.data == CB.WIPE_CONFIRM_1, AdminFlow.confirm_delete_step_1)
async def wipe_step2(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        await callback.answer()
        return
    await state.set_state(AdminFlow.confirm_delete_step_2)
    await safe_edit_or_send(
        callback,
        "⚠️ این عملیات غیرقابل بازگشت است.\n"
        "برای ادامه، «تایید نهایی» را انتخاب کنید.",
        reply_markup=wipe_confirm_step_2(),
    )


@router.callback_query(F.data == CB.WIPE_CONFIRM_2, AdminFlow.confirm_delete_step_2)
async def wipe_confirm(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        await callback.answer()
        return
    await state.clear()
    await settings_service.wipe_operational_data()
    await safe_edit_or_send(
        callback, "✅ تمامی اطلاعات عملیاتی پاک شد.", reply_markup=admin_panel()
    )
    logger.warning("Operational data wiped by owner=%s", db_user.telegram_id)


@router.callback_query(F.data == CB.WIPE_CANCEL)
async def wipe_cancel(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    await state.clear()
    await safe_edit_or_send(
        callback, "عملیات لغو شد.", reply_markup=admin_panel()
    )


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


def _extract_custom_emoji_id(message: Message) -> str | None:
    """Pull a custom_emoji_id out of a message's entities, if the owner sent an
    actual premium emoji (requires Telegram Premium to send)."""
    for entity in message.entities or []:
        if entity.type == "custom_emoji" and entity.custom_emoji_id:
            return entity.custom_emoji_id
    return None


async def _is_valid_custom_emoji(bot: Bot, custom_emoji_id: str) -> bool:
    try:
        stickers = await bot.get_custom_emoji_stickers(
            custom_emoji_ids=[custom_emoji_id]
        )
    except TelegramAPIError:
        return False
    return bool(stickers)


async def _notify_user(bot: Bot, telegram_id: int, text: str) -> None:
    try:
        await bot.send_message(telegram_id, text)
    except TelegramAPIError as exc:
        logger.warning("Could not notify user %s: %s", telegram_id, exc)
