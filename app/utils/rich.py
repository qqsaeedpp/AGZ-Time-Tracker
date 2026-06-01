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

from aiogram.types import MessageEntity
from aiogram.utils.formatting import Bold, CustomEmoji, Italic, Text

# Entity types we faithfully store and replay from an owner-supplied message so
# that premium (custom) emoji and bold/italic land exactly where they were typed.
REPLAYABLE_ENTITY_TYPES = {
    "custom_emoji",
    "bold",
    "italic",
    "underline",
    "strikethrough",
    "spoiler",
    "code",
    "pre",
    "blockquote",
    "text_link",
    "text_mention",
}


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


# Report icons that an owner may override with a premium emoji. Each entry is
# (default normal emoji, Persian label shown in the admin picker). The custom
# id, when set, is stored in the key/value settings table as ``remoji:<slot>``.
REPORT_ICON_SPECS: dict[str, tuple[str, str]] = {
    "report": ("📊", "گزارش"),
    "date": ("📅", "تاریخ"),
    "online": ("🟢", "آنلاین"),
    "offline": ("🔴", "آفلاین"),
    "clock": ("⏰", "ساعت / مجموع کاربر"),
    "intervals": ("📌", "بازه‌های فعالیت"),
    "user": ("👤", "کاربر"),
    "team": ("📈", "مجموع تیم"),
    "users": ("👥", "تعداد کاربران"),
}

REPORT_EMOJI_PREFIX = "remoji:"


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


@dataclass
class Rendered:
    """A ready-to-send message: plain text plus explicit Telegram entities
    (already in UTF-16 offsets), used to replay owner-typed premium emoji."""

    text: str
    entities: list | None = None


@dataclass(frozen=True)
class EmojiIcon:
    """An icon used inside reports: a normal unicode ``char`` plus an optional
    premium ``custom_emoji_id`` override. Renders as a custom emoji when set,
    otherwise falls back to the normal emoji."""

    char: str
    custom_emoji_id: str | None = None


def icon_node(icon: EmojiIcon):
    """Return an aiogram formatting node for an :class:`EmojiIcon`."""
    if icon.custom_emoji_id:
        return CustomEmoji(icon.char, custom_emoji_id=icon.custom_emoji_id)
    return icon.char


def normalize(content: "str | Text | Rendered") -> tuple[str, list | None]:
    """Return ``(text, entities)`` for a plain string, an aiogram formatting
    node, or a :class:`Rendered`. Entities carry no parse_mode so callers can
    safely pass ``parse_mode=None``."""
    if isinstance(content, Rendered):
        return content.text, content.entities
    if isinstance(content, str):
        return content, None
    kwargs = content.as_kwargs()
    return kwargs["text"], (kwargs.get("entities") or None)


# --------------------- Premium-emoji entity capture/replay ---------------------
def _utf16_len(text: str) -> int:
    """Length of ``text`` in UTF-16 code units (Telegram entity offset unit)."""
    return len(text.encode("utf-16-le")) // 2


def entities_to_dicts(entities) -> list[dict]:
    """Serialize the entities of an owner-supplied message into plain dicts,
    keeping only the formatting/custom-emoji entities we can replay. This is how
    the bot automatically captures the numeric ``custom_emoji_id`` of any premium
    emoji the owner typed inside their text."""
    result: list[dict] = []
    for entity in entities or []:
        if entity.type not in REPLAYABLE_ENTITY_TYPES:
            continue
        data: dict = {
            "type": entity.type,
            "offset": entity.offset,
            "length": entity.length,
        }
        if getattr(entity, "custom_emoji_id", None):
            data["custom_emoji_id"] = entity.custom_emoji_id
        if getattr(entity, "url", None):
            data["url"] = entity.url
        if getattr(entity, "language", None):
            data["language"] = entity.language
        result.append(data)
    return result


def dicts_to_entities(dicts) -> list[MessageEntity] | None:
    if not dicts:
        return None
    return [
        MessageEntity(
            type=d["type"],
            offset=d["offset"],
            length=d["length"],
            custom_emoji_id=d.get("custom_emoji_id"),
            url=d.get("url"),
            language=d.get("language"),
        )
        for d in dicts
    ]


def custom_emoji_ids(dicts) -> list[str]:
    return [d["custom_emoji_id"] for d in dicts if d.get("custom_emoji_id")]


def dump_entities(dicts) -> str:
    return json.dumps({"entities": dicts}, ensure_ascii=False)


def load_entities(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if isinstance(data, dict):
        entities = data.get("entities")
        return entities if isinstance(entities, list) else []
    return []


def apply_placeholders(
    text: str, entity_dicts: list[dict], replacements: dict[str, object] | None
) -> tuple[str, list[dict]]:
    """Substitute ``{token}`` placeholders and shift entity offsets so premium
    emoji and styling stay aligned after the (variable-length) substitution.

    Assumes placeholders never sit inside an entity span, which holds for our
    templates (placeholders are bare ``{minutes}``/``{jalali}`` tokens).
    """
    if not replacements:
        return text, entity_dicts

    # Record each occurrence as (utf16_start_in_original, delta_in_utf16).
    occurrences: list[tuple[int, int]] = []
    for token, value in replacements.items():
        marker = "{" + token + "}"
        delta = _utf16_len(str(value)) - _utf16_len(marker)
        start = 0
        while True:
            idx = text.find(marker, start)
            if idx == -1:
                break
            occurrences.append((_utf16_len(text[:idx]), delta))
            start = idx + len(marker)

    new_text = text
    for token, value in replacements.items():
        new_text = new_text.replace("{" + token + "}", str(value))

    new_entities: list[dict] = []
    for d in entity_dicts:
        shift = sum(delta for pos, delta in occurrences if pos < d["offset"])
        adjusted = dict(d)
        adjusted["offset"] = d["offset"] + shift
        new_entities.append(adjusted)

    return new_text, new_entities
