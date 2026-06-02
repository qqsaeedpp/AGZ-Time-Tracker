from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import (
    BUTTON_ATTRS,
    CB,
    STYLE_LABELS,
    VALID_STYLES,
    admin_panel,
    back_to_admin,
    button_attr_picker,
    button_picker,
    button_style_picker,
    report_icon_picker,
    wipe_confirm_step_1,
    wipe_confirm_step_2,
)
from app.utils.rich import REPORT_ICON_SPECS
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
from app.utils.rich import (
    SPECS,
    custom_emoji_ids,
    dump_entities,
    entities_to_dicts,
)

logger = logging.getLogger(__name__)

router = Router(name="admin")

GROUP_TYPES = {"group", "supergroup"}

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
        f"متن جدید برای «{SPECS[key].label}» را ارسال کنید.\n\n"
        "می‌توانید ایموجی پریمیوم (Custom Emoji) را مستقیماً داخل همین متن "
        "بنویسید؛ ربات به‌صورت خودکار آن را شناسایی و ذخیره می‌کند و دقیقاً "
        "همان‌جا نمایش می‌دهد.",
        reply_markup=back_to_admin(),
    )


@router.message(AdminFlow.waiting_custom_text_value)
async def custom_text_value(
    message: Message, db_user: User, state: FSMContext, bot: Bot
) -> None:
    if not _is_owner(db_user):
        return

    value = message.text or message.caption
    if not value:
        await message.answer("لطفاً یک متن ارسال کنید.")
        return

    # Automatically capture every entity the owner used — including the numeric
    # custom_emoji_id of any premium emoji typed inside the text — and store it
    # so the message is replayed exactly (premium emoji rendered correctly).
    raw_entities = message.entities or message.caption_entities or []
    entity_dicts = entities_to_dicts(raw_entities)
    ids = custom_emoji_ids(entity_dicts)

    # Best-effort validation so the owner learns if the bot can't use an emoji.
    invalid: list[str] = []
    for cid in ids:
        if not await _is_valid_custom_emoji(bot, cid):
            invalid.append(cid)

    data = await state.get_data()
    key = data.get("text_key")
    await state.clear()

    await settings_service.set_text_setting(
        key,
        value,
        ids[0] if ids else None,
        dump_entities(entity_dicts),
    )

    if ids:
        note = f"با {len(ids)} ایموجی پریمیوم"
        if invalid:
            note += " (برخی شناسه‌ها در دسترس نبودند و در صورت خطا به متن ساده برمی‌گردد)"
    else:
        note = "بدون ایموجی پریمیوم"
    await message.answer(f"✅ متن «{SPECS[key].label}» ذخیره شد — {note}.")

    # Live preview of the saved text exactly as users will see it.
    preview = await render(key, _preview_replacements())
    await safe_edit_or_send(message, preview, reply_markup=admin_panel())
    logger.info(
        "Custom text saved key=%s premium_count=%s by owner=%s",
        key,
        len(ids),
        db_user.telegram_id,
    )


# ----------------------------- Custom buttons (text / style / premium emoji) -----------------------------
@router.callback_query(F.data == CB.ADM_CUSTOM_BUTTON)
async def custom_button_start(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        await callback.answer("دسترسی مدیریت ندارید.", show_alert=True)
        return
    await state.clear()
    overrides = await settings_service.get_all_button_settings()
    await safe_edit_or_send(
        callback,
        "🔘 کدام دکمه را می‌خواهید شخصی‌سازی کنید؟\n\n"
        "(رنگ هر دکمه در همین فهرست به‌صورت واقعی نمایش داده می‌شود)",
        reply_markup=button_picker(overrides),
    )


@router.callback_query(F.data.startswith(CB.BTN_PICK))
async def custom_button_pick(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        await callback.answer("دسترسی مدیریت ندارید.", show_alert=True)
        return
    key = callback.data[len(CB.BTN_PICK):]
    await state.clear()
    await safe_edit_or_send(
        callback,
        f"🔘 دکمه «{key}»\n\nکدام بخش را تغییر می‌دهید؟\n"
        "• متن: عنوان دکمه\n"
        "• رنگ: آبی / سبز / قرمز (استایل رسمی تلگرام)\n"
        "• ایموجی پریمیوم: نمایش یک Custom Emoji کنار متن",
        reply_markup=button_attr_picker(key),
    )


@router.callback_query(F.data.startswith(CB.BTN_ATTR))
async def custom_button_attr(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        await callback.answer("دسترسی مدیریت ندارید.", show_alert=True)
        return
    payload = callback.data[len(CB.BTN_ATTR):]
    key, _, attr = payload.partition(":")
    if attr not in BUTTON_ATTRS:
        await callback.answer()
        return

    # Style is picked from an inline keyboard (no text input needed).
    if attr == "style":
        await state.clear()
        await safe_edit_or_send(
            callback,
            f"🎨 رنگ دکمه «{key}» را انتخاب کنید:",
            reply_markup=button_style_picker(key),
        )
        return

    await state.update_data(button_key=key, button_attr=attr)
    await state.set_state(AdminFlow.waiting_custom_button_value)
    if attr == "emoji":
        hint = (
            "یک ایموجی پریمیوم (Custom Emoji) ارسال کنید تا کنار متن دکمه نمایش "
            "داده شود؛ ربات شناسهٔ آن را خودکار استخراج می‌کند.\n\n"
            "برای برداشتن ایموجی، «حذف» را ارسال کنید.\n"
            "توجه: نمایش ایموجی پریمیوم روی دکمه‌ها نیازمند Premium مالک ربات است."
        )
    else:  # text
        hint = "متن جدید دکمه را ارسال کنید:"
    await safe_edit_or_send(
        callback,
        f"🔘 دکمه «{key}» — {BUTTON_ATTRS[attr]}\n\n{hint}",
        reply_markup=back_to_admin(),
    )


@router.callback_query(F.data.startswith(CB.BTN_STYLE))
async def custom_button_style(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        await callback.answer("دسترسی مدیریت ندارید.", show_alert=True)
        return
    payload = callback.data[len(CB.BTN_STYLE):]
    key, _, style = payload.partition(":")
    if style not in VALID_STYLES:
        await callback.answer()
        return
    await state.clear()
    await settings_service.set_button_setting(button_key=key, button_style=style)
    overrides = await settings_service.get_all_button_settings()
    await safe_edit_or_send(
        callback,
        f"✅ رنگ دکمه «{key}» به «{STYLE_LABELS[style]}» تغییر کرد.\n\n"
        "دکمهٔ دیگری برای ویرایش انتخاب کنید:",
        reply_markup=button_picker(overrides),
    )


@router.message(AdminFlow.waiting_custom_button_value)
async def custom_button_value(
    message: Message, db_user: User, state: FSMContext, bot: Bot
) -> None:
    if not _is_owner(db_user):
        return
    data = await state.get_data()
    key = data.get("button_key")
    attr = data.get("button_attr")
    if key is None or attr not in {"text", "emoji"}:
        await state.clear()
        await safe_edit_or_send(
            message, "عملیات نامعتبر بود.", reply_markup=admin_panel()
        )
        return

    if attr == "text":
        value = (message.text or "").strip()
        if not value:
            await message.answer("لطفاً یک عنوان ارسال کنید.")
            return
        await state.clear()
        await settings_service.set_button_setting(button_key=key, button_text=value)
        note = "متن دکمه ذخیره شد"
    else:  # premium emoji
        text = (message.text or "").strip()
        if text in {"حذف", "-"}:
            await state.clear()
            await settings_service.set_button_setting(
                button_key=key, button_custom_emoji_id=""
            )
            note = "ایموجی پریمیوم دکمه برداشته شد"
        else:
            raw_entities = message.entities or message.caption_entities or []
            ids = custom_emoji_ids(entities_to_dicts(raw_entities))
            if not ids:
                await message.answer(
                    "ایموجی پریمیوم پیدا نشد. یک Custom Emoji ارسال کنید یا «حذف» بزنید."
                )
                return
            await state.clear()
            valid = await _is_valid_custom_emoji(bot, ids[0])
            await settings_service.set_button_setting(
                button_key=key, button_custom_emoji_id=ids[0]
            )
            note = "ایموجی پریمیوم دکمه ذخیره شد"
            if not valid:
                note += " (شناسه در دسترس نبود؛ در صورت خطا روی دکمه نمایش داده نمی‌شود)"

    overrides = await settings_service.get_all_button_settings()
    await safe_edit_or_send(
        message,
        f"✅ {note}.\n\nدکمهٔ دیگری برای ویرایش انتخاب کنید:",
        reply_markup=button_picker(overrides),
    )


# ----------------------------- Report icons (premium emoji) -----------------------------
@router.callback_query(F.data == CB.ADM_REPORT_EMOJI)
async def report_emoji_start(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        await callback.answer("دسترسی مدیریت ندارید.", show_alert=True)
        return
    await state.clear()
    await safe_edit_or_send(
        callback,
        "🎨 کدام آیکن گزارش را می‌خواهید با ایموجی پریمیوم تنظیم کنید؟",
        reply_markup=report_icon_picker(),
    )


@router.callback_query(F.data.startswith(CB.REPORT_ICON_PICK))
async def report_emoji_pick(
    callback: CallbackQuery, db_user: User, state: FSMContext
) -> None:
    if not _is_owner(db_user):
        await callback.answer("دسترسی مدیریت ندارید.", show_alert=True)
        return
    slot = callback.data[len(CB.REPORT_ICON_PICK):]
    if slot not in REPORT_ICON_SPECS:
        await callback.answer()
        return
    await state.update_data(report_slot=slot)
    await state.set_state(AdminFlow.waiting_report_emoji_value)
    label = REPORT_ICON_SPECS[slot][1]
    await safe_edit_or_send(
        callback,
        f"🎨 آیکن «{label}»\n\n"
        "یک ایموجی پریمیوم (Custom Emoji) ارسال کنید تا جایگزین آیکن این بخش "
        "در گزارش‌ها شود. ربات شناسهٔ آن را خودکار استخراج می‌کند.\n\n"
        "برای بازگشت به ایموجی پیش‌فرض، «پیش‌فرض» را ارسال کنید.",
        reply_markup=back_to_admin(),
    )


@router.message(AdminFlow.waiting_report_emoji_value)
async def report_emoji_value(
    message: Message, db_user: User, state: FSMContext, bot: Bot
) -> None:
    if not _is_owner(db_user):
        return
    data = await state.get_data()
    slot = data.get("report_slot")
    if slot not in REPORT_ICON_SPECS:
        await state.clear()
        await safe_edit_or_send(
            message, "عملیات نامعتبر بود.", reply_markup=admin_panel()
        )
        return

    text = (message.text or "").strip()
    if text in {"پیش‌فرض", "پیشفرض", "حذف", "-"}:
        await state.clear()
        await settings_service.set_report_emoji(slot, None)
        await safe_edit_or_send(
            message,
            "✅ آیکن به حالت پیش‌فرض بازگشت.",
            reply_markup=report_icon_picker(),
        )
        return

    raw_entities = message.entities or message.caption_entities or []
    ids = custom_emoji_ids(entities_to_dicts(raw_entities))
    if not ids:
        await message.answer(
            "ایموجی پریمیوم پیدا نشد. یک Custom Emoji ارسال کنید یا «پیش‌فرض» بزنید."
        )
        return

    await state.clear()
    valid = await _is_valid_custom_emoji(bot, ids[0])
    await settings_service.set_report_emoji(slot, ids[0])
    note = "" if valid else "\n\n(توجه: این شناسه در دسترس نبود و در صورت خطا به ایموجی معمولی برمی‌گردد)"
    await safe_edit_or_send(
        message,
        f"✅ آیکن «{REPORT_ICON_SPECS[slot][1]}» تنظیم شد." + note,
        reply_markup=report_icon_picker(),
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
def _target_thread_id(message: Message) -> int | None:
    """Topic id only for genuine forum-topic messages.

    Telegram also sets ``message_thread_id`` on plain replies in non-forum
    groups, so we guard with ``is_topic_message`` to avoid storing a bogus
    thread id (which would send the report into the wrong place)."""
    return message.message_thread_id if message.is_topic_message else None


@router.message(F.chat.type.in_(GROUP_TYPES), F.text == "نصب")
async def install_report_target(message: Message, db_user: User) -> None:
    if not _is_owner(db_user):
        return
    thread_id = _target_thread_id(message)
    await settings_service.install_report_target(
        chat_id=message.chat.id,
        message_thread_id=thread_id,
        installed_by=message.from_user.id,
    )
    # aiogram's ``answer`` already replies inside the same topic when the
    # source message is a topic message, so we don't pass the thread id again.
    await message.answer(
        "✅ مقصد گزارش روزانه ثبت شد.\n\n"
        "از این پس گزارش روزانه هر شب ساعت ۲۳:۰۰ به وقت تهران در همین بخش "
        "ارسال می‌شود."
    )
    logger.info(
        "Report target installed chat=%s thread=%s by owner=%s",
        message.chat.id,
        thread_id,
        message.from_user.id,
    )


@router.message(F.chat.type.in_(GROUP_TYPES), F.text == "حذف")
async def remove_report_target(message: Message, db_user: User) -> None:
    if not _is_owner(db_user):
        return
    thread_id = _target_thread_id(message)
    removed = await settings_service.remove_report_target(
        chat_id=message.chat.id, message_thread_id=thread_id
    )
    if removed:
        await message.answer("🗑 ارسال گزارش روزانه برای این بخش غیرفعال شد.")
        logger.info(
            "Report target removed chat=%s thread=%s by owner=%s",
            message.chat.id,
            thread_id,
            message.from_user.id,
        )
    else:
        await message.answer(
            "⚠️ برای این گروه یا تاپیک مقصد فعالی ثبت نشده است."
        )


# ----------------------------- Helpers -----------------------------
def _parse_user_id(text: str | None) -> int | None:
    if not text:
        return None
    text = text.strip()
    if not text.lstrip("-").isdigit():
        return None
    value = int(text)
    return value if value > 0 else None


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
