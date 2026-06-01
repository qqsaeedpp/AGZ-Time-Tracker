"""Rich-text rendering with premium (custom) emoji support.

Messages are built with :mod:`aiogram.utils.formatting` so that bold/italic and
custom emoji are expressed as message *entities*. Entities and ``parse_mode``
are mutually exclusive in the Telegram API, so the whole app sends with
``parse_mode=None`` and relies on entities only — this guarantees they never
conflict.

A "customizable text" has:
  * a body string (``text_value``) — may contain ``{placeholder}`` tokens that
    are substituted at render time (e.g. ``{minutes}`` for the shift summary);
  * an optional ``custom_emoji_id`` — a Telegram premium emoji used as the
    leading icon. When absent we fall back to a normal unicode emoji so the bot
    keeps working without premium emoji;
  * a small ``formatting`` mapping describing which parts to embolden/italicize.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from aiogram.utils.formatting import Bold, CustomEmoji, Italic, Text


@dataclass(frozen=True)
class TextSpec:
    """Definition of one owner-customizable message."""

    key: str
    label: str  # Persian label shown in the admin picker
    emoji: str  # normal unicode fallback emoji (leading icon)
    default_text: str  # default body, may contain {placeholder} tokens
    default_formatting: dict = field(
        default_factory=lambda: {"bold_title": True, "italic_body": True}
    )


# Order here drives the admin "customize texts" menu.
SPECS: dict[str, TextSpec] = {
    "welcome": TextSpec(
        key="welcome",
        label="پیام خوش‌آمد",
        emoji="👋",
        default_text=(
            "به ربات ثبت زمان پاسخگویی AGZ خوش آمدید\n\n"
            "برای شروع، یکی از گزینه‌های زیر را انتخاب کنید."
        ),
    ),
    "start_ok": TextSpec(
        key="start_ok",
        label="شروع پاسخگویی",
        emoji="🟢",
        default_text=(
            "زمان شروع پاسخگویی شما ثبت شد\n\n"
            "وضعیت شما هم‌اکنون: آنلاین 🟢"
        ),
    ),
    "start_already": TextSpec(
        key="start_already",
        label="پاسخگویی فعال",
        emoji="🟢",
        default_text=(
            "شما هم‌اکنون در حال پاسخگویی هستید\n\n"
            "برای پایان، دکمهٔ «پایان پاسخگویی» را بزنید."
        ),
    ),
    "end_done": TextSpec(
        key="end_done",
        label="پایان پاسخگویی",
        emoji="🔴",
        default_text=(
            "پایان پاسخگویی شما ثبت شد\n\n"
            "مدت پاسخگویی: {minutes} دقیقه\n"
            "وضعیت شما هم‌اکنون: آفلاین 🔴"
        ),
    ),
    "end_none": TextSpec(
        key="end_none",
        label="بدون شیفت فعال",
        emoji="🔴",
        default_text=(
            "شیفت فعالی برای شما یافت نشد\n\n"
            "برای ثبت پاسخگویی ابتدا «شروع پاسخگویی» را بزنید."
        ),
    ),
    "support": TextSpec(
        key="support",
        label="پشتیبانی ربات",
        emoji="🛟",
        default_text=(
            "پشتیبانی ربات\n\n"
            "در صورت بروز هرگونه مشکل، با پشتیبانی در ارتباط باشید:\n@amirjrha"
        ),
    ),
    "today": TextSpec(
        key="today",
        label="تاریخ امروز",
        emoji="🗓",
        default_text=(
            "تاریخ امروز\n\n"
            "شمسی: {jalali}\n"
            "میلادی: {greg}\n"
            "ساعت تهران: {time}"
        ),
    ),
    "daily_user_notice": TextSpec(
        key="daily_user_notice",
        label="اطلاع گزارش روزانه",
        emoji="🔵",
        default_text=(
            "گزارش روزانه\n\n"
            "هر شب ساعت ۲۳ به‌صورت خودکار در گروه ثبت ورود و خروج ارسال می‌شود."
        ),
    ),
    "monthly_user_notice": TextSpec(
        key="monthly_user_notice",
        label="اطلاع گزارش ماهانه",
        emoji="📘",
        default_text=(
            "گزارش ماهانه\n\n"
            "این گزارش توسط مدیریت تهیه و منتشر می‌شود."
        ),
    ),
}


def parse_formatting(raw: str | None, default: dict) -> dict:
    """Decode a stored ``formatting_config`` JSON blob, falling back safely."""
    if not raw:
        return dict(default)
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return dict(default)
    return data if isinstance(data, dict) else dict(default)


def dump_formatting(formatting: dict) -> str:
    return json.dumps(formatting, ensure_ascii=False)


def substitute(text_value: str, replacements: dict[str, object] | None) -> str:
    """Replace ``{token}`` placeholders without using str.format(), so literal
    braces typed by an admin can never raise."""
    if not replacements:
        return text_value
    for token, value in replacements.items():
        text_value = text_value.replace("{" + token + "}", str(value))
    return text_value


def compose(
    text_value: str,
    *,
    emoji_char: str | None = None,
    custom_emoji_id: str | None = None,
    formatting: dict | None = None,
) -> Text:
    """Build an aiogram ``Text`` node: a leading emoji (custom or normal) plus a
    title line and an optional body, formatted per ``formatting``."""
    formatting = formatting or {}
    nodes: list = []

    if emoji_char or custom_emoji_id:
        char = emoji_char or "⭐"
        if custom_emoji_id:
            nodes.append(CustomEmoji(char, custom_emoji_id=custom_emoji_id))
        else:
            nodes.append(char)
        nodes.append(" ")

    first_nl = text_value.find("\n")
    if first_nl == -1:
        title, body = text_value, ""
    else:
        title, body = text_value[:first_nl], text_value[first_nl:]

    if formatting.get("bold_title", True):
        nodes.append(Bold(title))
    else:
        nodes.append(title)

    if body:
        if formatting.get("italic_body", False):
            nodes.append(Italic(body))
        else:
            nodes.append(body)

    return Text(*nodes)


def normalize(content: "str | Text") -> tuple[str, list | None]:
    """Return ``(text, entities)`` for either a plain string or an aiogram
    formatting node. Entities are returned without a parse_mode so callers can
    safely pass ``parse_mode=None``."""
    if isinstance(content, str):
        return content, None
    kwargs = content.as_kwargs()
    return kwargs["text"], (kwargs.get("entities") or None)
