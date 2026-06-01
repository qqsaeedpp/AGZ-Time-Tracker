from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.formatting import Text

from app.bot.keyboards import CB, main_menu, sanitize_markup
from app.database.models import User
from app.services import settings_service
from app.utils.datetime_utils import now_tehran
from app.utils.jalali_utils import to_gregorian_date, to_jalali_date
from app.utils.rich import (
    SPECS,
    Rendered,
    apply_placeholders,
    compose,
    dicts_to_entities,
    load_entities,
    normalize,
    substitute,
)

logger = logging.getLogger(__name__)

router = Router(name="common")

NO_ACCESS = "شما اجازهٔ دسترسی به این ربات را ندارید."

# Keys an owner may customize via the admin panel (text + premium emoji).
CUSTOM_TEXT_KEYS = list(SPECS.keys())


# --------------------------- Rich text rendering ---------------------------
async def render(key: str, replacements: dict[str, object] | None = None) -> Text:
    """Build the (possibly owner-customized) rich message for ``key``.

    Falls back to the built-in default text and a normal emoji when no custom
    value / premium emoji is stored, so the bot always renders something valid.
    """
    spec = SPECS[key]
    setting = await settings_service.get_text_setting(key)
    if setting is not None and setting.text_value:
        # Owner-customized: replay the exact text + entities they typed, so any
        # premium emoji shows precisely where it was placed. Placeholder tokens
        # are substituted with entity offsets shifted to stay aligned.
        entity_dicts = load_entities(setting.formatting_config)
        text, adjusted = apply_placeholders(
            setting.text_value, entity_dicts, replacements
        )
        return Rendered(text, dicts_to_entities(adjusted))

    # Default: built-in beautified message with a normal leading emoji.
    text_value = substitute(spec.default_text, replacements)
    return compose(
        text_value,
        emoji_char=spec.emoji,
        custom_emoji_id=None,
        formatting=dict(spec.default_formatting),
    )


# --------------------------- Clean-chat send helper ---------------------------
async def _send(
    message: Message,
    text: str,
    entities: list | None,
    reply_markup: InlineKeyboardMarkup | None,
) -> None:
    """Send a fresh message; if the entities or a premium emoji on a button are
    rejected, retry once as plain text with button icons stripped so delivery
    never fails."""
    try:
        await message.answer(
            text, entities=entities, reply_markup=reply_markup, parse_mode=None
        )
    except TelegramBadRequest:
        await message.answer(
            text, reply_markup=sanitize_markup(reply_markup), parse_mode=None
        )


async def _replace(
    message: Message,
    text: str,
    entities: list | None,
    reply_markup: InlineKeyboardMarkup | None,
) -> None:
    """Delete the previous menu message (best-effort) then send a new one, so
    the chat is not cluttered with stale menus."""
    try:
        await message.delete()
    except TelegramAPIError:
        pass
    await _send(message, text, entities, reply_markup)


async def safe_edit_or_send(
    event: CallbackQuery | Message,
    content: str | Text,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Render ``content`` in place without leaving previous menus behind.

    For callbacks we edit the originating message when possible; otherwise we
    delete it and send a fresh one. Telegram quirks ("message is not modified",
    "message to delete not found", "message can't be edited") are handled
    without crashing, and the callback query is always answered.
    """
    text, entities = normalize(content)

    if isinstance(event, CallbackQuery):
        message = event.message
        if message is not None:
            try:
                await message.edit_text(
                    text,
                    entities=entities,
                    reply_markup=reply_markup,
                    parse_mode=None,
                )
            except TelegramBadRequest as exc:
                if "message is not modified" not in str(exc).lower():
                    await _replace(message, text, entities, reply_markup)
            except TelegramAPIError:
                await _replace(message, text, entities, reply_markup)
        await event.answer()
    else:
        await _send(event, text, entities, reply_markup)


async def send_report(
    event: CallbackQuery | Message, content: str | Text
) -> None:
    """Always deliver a report as a brand-new message — never edit or delete the
    previous one. Falls back to plain text if the entities are rejected (e.g. an
    unavailable premium emoji). The callback query is still answered."""
    text, entities = normalize(content)
    message = event.message if isinstance(event, CallbackQuery) else event
    if message is not None:
        await _send(message, text, entities, None)
    if isinstance(event, CallbackQuery):
        await event.answer()


# --------------------------- Menus ---------------------------
async def menu_markup(user: User) -> InlineKeyboardMarkup:
    overrides = await settings_service.get_all_button_settings()
    return main_menu(is_owner=user.is_owner, overrides=overrides)


async def show_main_menu(event: CallbackQuery | Message, user: User) -> None:
    content = await render("welcome")
    await safe_edit_or_send(event, content, reply_markup=await menu_markup(user))


def today_replacements() -> dict[str, object]:
    now = now_tehran()
    return {
        "jalali": to_jalali_date(now),
        "greg": to_gregorian_date(now),
        "time": now.strftime("%H:%M"),
    }


# --------------------------- Handlers ---------------------------
@router.callback_query(F.data == CB.TODAY)
async def on_today(callback: CallbackQuery, db_user: User) -> None:
    if not db_user.is_allowed:
        await callback.answer(NO_ACCESS, show_alert=True)
        return
    content = await render("today", today_replacements())
    await safe_edit_or_send(
        callback, content, reply_markup=await menu_markup(db_user)
    )


@router.callback_query(F.data == CB.SUPPORT)
async def on_support(callback: CallbackQuery, db_user: User) -> None:
    if not db_user.is_allowed:
        await callback.answer(NO_ACCESS, show_alert=True)
        return
    content = await render("support")
    await safe_edit_or_send(
        callback, content, reply_markup=await menu_markup(db_user)
    )


@router.callback_query()
async def on_unknown_callback(callback: CallbackQuery) -> None:
    # Fallback for stale/expired inline buttons.
    await callback.answer()
