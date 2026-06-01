from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.utils.rich import REPORT_ICON_SPECS

if TYPE_CHECKING:
    from app.services.settings_service import ButtonSettingData


# Callback data identifiers (kept short and stable).
class CB:
    START_SHIFT = "start_shift"
    END_SHIFT = "end_shift"
    STATUS = "status"
    DAILY_REPORT = "daily_report"
    MONTHLY_REPORT = "monthly_report"
    SUPPORT = "support"
    TODAY = "today"
    ADMIN_PANEL = "admin_panel"

    ADM_BROADCAST = "adm_broadcast"
    ADM_ADD_ACCESS = "adm_add_access"
    ADM_REMOVE_ACCESS = "adm_remove_access"
    ADM_WIPE = "adm_wipe"
    ADM_CUSTOM_TEXT = "adm_custom_text"
    ADM_CUSTOM_BUTTON = "adm_custom_button"
    ADM_REPORT_EMOJI = "adm_report_emoji"
    ADM_BACK = "adm_back"

    WIPE_CONFIRM_1 = "wipe_confirm_1"
    WIPE_CONFIRM_2 = "wipe_confirm_2"
    WIPE_CANCEL = "wipe_cancel"

    # Prefixed callbacks (the suffix carries a button key / attribute / value).
    BTN_PICK = "bpk:"  # bpk:<button_key>
    BTN_ATTR = "bat:"  # bat:<button_key>:<attr>  (attr in text|style|emoji)
    BTN_STYLE = "bst:"  # bst:<button_key>:<style>  (style in primary|success|danger)
    REPORT_ICON_PICK = "ric:"  # ric:<slot>


# Official Bot API button colours (Bot API 9.4+). NOTE: the API also accepts an
# omitted style (app default); we always set one of these three.
STYLE_PRIMARY = "primary"  # blue
STYLE_SUCCESS = "success"  # green
STYLE_DANGER = "danger"  # red
VALID_STYLES = (STYLE_PRIMARY, STYLE_SUCCESS, STYLE_DANGER)

# Persian display names for each style (shown in the admin picker).
STYLE_LABELS: dict[str, str] = {
    STYLE_PRIMARY: "آبی",
    STYLE_SUCCESS: "سبز",
    STYLE_DANGER: "قرمز",
}

# Editable button attributes shown in the customization picker.
BUTTON_ATTRS: dict[str, str] = {
    "text": "متن",
    "style": "رنگ",
    "emoji": "ایموجی پریمیوم",
}


# Default appearance per button: (style, text). Colours follow the spec:
#   start = success(green), end = danger(red), status/reports = primary(blue),
#   today = success(green), support = danger(red), admin = primary(blue).
BUTTON_DEFAULTS: dict[str, tuple[str, str]] = {
    CB.START_SHIFT: (STYLE_SUCCESS, "شروع پاسخگویی"),
    CB.END_SHIFT: (STYLE_DANGER, "پایان پاسخگویی"),
    CB.STATUS: (STYLE_PRIMARY, "وضعیت"),
    CB.DAILY_REPORT: (STYLE_PRIMARY, "گزارش روزانه"),
    CB.MONTHLY_REPORT: (STYLE_PRIMARY, "گزارش ماهانه"),
    CB.TODAY: (STYLE_SUCCESS, "تاریخ امروز"),
    CB.SUPPORT: (STYLE_DANGER, "پشتیبانی ربات"),
    CB.ADMIN_PANEL: (STYLE_PRIMARY, "پنل مدیریت"),
}

# Buttons exposed in the "customize buttons" admin picker.
CUSTOMIZABLE_BUTTONS = list(BUTTON_DEFAULTS.keys())


def _resolve(
    key: str, overrides: "dict[str, ButtonSettingData] | None"
) -> tuple[str, str, str | None]:
    """Return ``(style, text, custom_emoji_id)`` for a button, applying owner
    overrides on top of the built-in defaults."""
    style, text = BUTTON_DEFAULTS[key]
    custom_emoji_id: str | None = None
    override = overrides.get(key) if overrides else None
    if override is not None:
        if override.button_style in VALID_STYLES:
            style = override.button_style
        if override.button_text:
            text = override.button_text
        if override.button_custom_emoji_id:
            custom_emoji_id = override.button_custom_emoji_id
    return style, text, custom_emoji_id


def _btn(key: str, overrides) -> InlineKeyboardButton:
    """Build a main-menu button using the official ``style`` colour and an
    optional premium ``icon_custom_emoji_id``."""
    style, text, custom_emoji_id = _resolve(key, overrides)
    return InlineKeyboardButton(
        text=text,
        callback_data=key,
        style=style,
        icon_custom_emoji_id=custom_emoji_id,
    )


def main_menu(
    is_owner: bool, overrides: "dict[str, ButtonSettingData] | None" = None
) -> InlineKeyboardMarkup:
    rows = [
        [_btn(CB.START_SHIFT, overrides), _btn(CB.END_SHIFT, overrides)],
        [_btn(CB.STATUS, overrides), _btn(CB.DAILY_REPORT, overrides)],
        [_btn(CB.MONTHLY_REPORT, overrides), _btn(CB.TODAY, overrides)],
        [_btn(CB.SUPPORT, overrides)],
    ]
    if is_owner:
        rows.append([_btn(CB.ADMIN_PANEL, overrides)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_panel() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="📣 ارسال همگانی", callback_data=CB.ADM_BROADCAST)],
        [
            InlineKeyboardButton(
                text="➕ افزودن دسترسی", callback_data=CB.ADM_ADD_ACCESS
            ),
            InlineKeyboardButton(
                text="➖ حذف دسترسی", callback_data=CB.ADM_REMOVE_ACCESS
            ),
        ],
        [
            InlineKeyboardButton(
                text="✏️ شخصی‌سازی متن‌ها", callback_data=CB.ADM_CUSTOM_TEXT
            ),
            InlineKeyboardButton(
                text="🔘 شخصی‌سازی دکمه‌ها", callback_data=CB.ADM_CUSTOM_BUTTON
            ),
        ],
        [
            InlineKeyboardButton(
                text="🎨 ایموجی گزارش‌ها", callback_data=CB.ADM_REPORT_EMOJI
            )
        ],
        [
            InlineKeyboardButton(
                text="🧹 پاک کردن اطلاعات", callback_data=CB.ADM_WIPE
            )
        ],
        [InlineKeyboardButton(text="↩️ بازگشت", callback_data=CB.ADM_BACK)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def wipe_confirm_step_1() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ بله", callback_data=CB.WIPE_CONFIRM_1)],
            [InlineKeyboardButton(text="↩️ انصراف", callback_data=CB.WIPE_CANCEL)],
        ]
    )


def wipe_confirm_step_2() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 تایید نهایی", callback_data=CB.WIPE_CONFIRM_2
                )
            ],
            [InlineKeyboardButton(text="↩️ انصراف", callback_data=CB.WIPE_CANCEL)],
        ]
    )


def back_to_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="↩️ بازگشت", callback_data=CB.ADM_BACK)]
        ]
    )


def button_picker(
    overrides: "dict[str, ButtonSettingData] | None" = None,
) -> InlineKeyboardMarkup:
    """List every customizable button so the owner can choose which to edit.

    Each picker row is rendered with the button's *own* current style and
    premium emoji, so the owner sees a live preview of its real colour."""
    rows = []
    for key in CUSTOMIZABLE_BUTTONS:
        style, text, custom_emoji_id = _resolve(key, overrides)
        rows.append(
            [
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"{CB.BTN_PICK}{key}",
                    style=style,
                    icon_custom_emoji_id=custom_emoji_id,
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="↩️ بازگشت", callback_data=CB.ADM_BACK)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def button_attr_picker(button_key: str) -> InlineKeyboardMarkup:
    """Offer the editable attributes (text / style / premium emoji)."""
    rows = [
        [
            InlineKeyboardButton(
                text=label, callback_data=f"{CB.BTN_ATTR}{button_key}:{attr}"
            )
        ]
        for attr, label in BUTTON_ATTRS.items()
    ]
    rows.append(
        [InlineKeyboardButton(text="↩️ بازگشت", callback_data=CB.ADM_CUSTOM_BUTTON)]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def button_style_picker(button_key: str) -> InlineKeyboardMarkup:
    """Offer the three official colours, each rendered in its own style so the
    owner previews the real colour before choosing."""
    rows = [
        [
            InlineKeyboardButton(
                text=STYLE_LABELS[style],
                callback_data=f"{CB.BTN_STYLE}{button_key}:{style}",
                style=style,
            )
        ]
        for style in VALID_STYLES
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text="↩️ بازگشت", callback_data=f"{CB.BTN_PICK}{button_key}"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def sanitize_markup(
    markup: InlineKeyboardMarkup | None,
) -> InlineKeyboardMarkup | None:
    """Return a copy of *markup* with every ``icon_custom_emoji_id`` removed.

    Used as a fallback when Telegram rejects a send/edit because a premium emoji
    on a button is unavailable — the menu still renders (just without the custom
    emoji) instead of failing entirely."""
    if markup is None:
        return None
    has_icon = any(
        getattr(btn, "icon_custom_emoji_id", None)
        for row in markup.inline_keyboard
        for btn in row
    )
    if not has_icon:
        return markup
    rows = [
        [
            btn.model_copy(update={"icon_custom_emoji_id": None})
            for btn in row
        ]
        for row in markup.inline_keyboard
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def report_icon_picker() -> InlineKeyboardMarkup:
    """List every report icon slot the owner may override with a premium emoji."""
    rows = [
        [
            InlineKeyboardButton(
                text=f"{char} {label}", callback_data=f"{CB.REPORT_ICON_PICK}{slot}"
            )
        ]
        for slot, (char, label) in REPORT_ICON_SPECS.items()
    ]
    rows.append([InlineKeyboardButton(text="↩️ بازگشت", callback_data=CB.ADM_BACK)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
