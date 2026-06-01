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

    # Prefixed callbacks (the suffix carries a button key / attribute / slot).
    BTN_PICK = "bpk:"  # bpk:<button_key>
    BTN_ATTR = "bat:"  # bat:<button_key>:<attr>  (attr in text|emoji|color)
    REPORT_ICON_PICK = "ric:"  # ric:<slot>


# Persian labels for the three editable button attributes.
BUTTON_ATTRS: dict[str, str] = {
    "text": "متن",
    "emoji": "ایموجی",
    "color": "رنگ (ایموجی رنگی)",
}


# Default appearance per button: (color emoji, thematic emoji, text).
# NOTE: inline-keyboard text does NOT support premium emoji — only plain unicode
# emoji are used here (premium emoji are documented as reports-only in README).
# Colors follow the project spec: reports = blue, today = green, support = red.
BUTTON_DEFAULTS: dict[str, tuple[str, str, str]] = {
    CB.START_SHIFT: ("🟢", "", "شروع پاسخگویی"),
    CB.END_SHIFT: ("🔴", "", "پایان پاسخگویی"),
    CB.STATUS: ("🟡", "", "وضعیت"),
    CB.DAILY_REPORT: ("🔵", "", "گزارش روزانه"),
    CB.MONTHLY_REPORT: ("🔵", "", "گزارش ماهانه"),
    CB.TODAY: ("🟢", "", "تاریخ امروز"),
    CB.SUPPORT: ("🔴", "", "پشتیبانی ربات"),
    CB.ADMIN_PANEL: ("⚙️", "", "پنل مدیریت"),
}

# Buttons exposed in the "customize buttons" admin picker.
CUSTOMIZABLE_BUTTONS = list(BUTTON_DEFAULTS.keys())


def _caption(
    key: str, overrides: "dict[str, ButtonSettingData] | None"
) -> str:
    """Compose a button caption as ``color emoji text``, applying owner
    overrides on top of the defaults."""
    color, emoji, text = BUTTON_DEFAULTS[key]
    override = overrides.get(key) if overrides else None
    if override is not None:
        if override.button_color:
            color = override.button_color
        if override.button_emoji is not None:
            emoji = override.button_emoji
        if override.button_text:
            text = override.button_text
    return " ".join(part for part in (color, emoji, text) if part)


def _btn(key: str, overrides) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=_caption(key, overrides), callback_data=key)


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
    """List every customizable button (showing its current caption) so the owner
    can choose which one to edit."""
    rows = [
        [InlineKeyboardButton(text=_caption(key, overrides), callback_data=f"{CB.BTN_PICK}{key}")]
        for key in CUSTOMIZABLE_BUTTONS
    ]
    rows.append([InlineKeyboardButton(text="↩️ بازگشت", callback_data=CB.ADM_BACK)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def button_attr_picker(button_key: str) -> InlineKeyboardMarkup:
    """Offer the three editable attributes (text/emoji/color) for one button."""
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
