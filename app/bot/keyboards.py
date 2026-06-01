from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


# Callback data identifiers (kept short and stable).
class CB:
    START_SHIFT = "start_shift"
    END_SHIFT = "end_shift"
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
    ADM_BACK = "adm_back"

    WIPE_CONFIRM_1 = "wipe_confirm_1"
    WIPE_CONFIRM_2 = "wipe_confirm_2"
    WIPE_CANCEL = "wipe_cancel"


# Default button captions (overridable via custom-button settings).
DEFAULT_BUTTONS = {
    CB.START_SHIFT: "شروع پاسخگویی",
    CB.END_SHIFT: "پایان پاسخگویی",
    CB.DAILY_REPORT: "گزارش روزانه",
    CB.MONTHLY_REPORT: "گزارش ماهانه",
    CB.SUPPORT: "پشتیبانی ربات",
    CB.TODAY: "تاریخ امروز",
    CB.ADMIN_PANEL: "پنل مدیریت",
}


def main_menu(is_owner: bool, labels: dict[str, str] | None = None) -> InlineKeyboardMarkup:
    captions = dict(DEFAULT_BUTTONS)
    if labels:
        captions.update({k: v for k, v in labels.items() if k in captions})

    rows = [
        [
            InlineKeyboardButton(
                text=captions[CB.START_SHIFT], callback_data=CB.START_SHIFT
            ),
            InlineKeyboardButton(
                text=captions[CB.END_SHIFT], callback_data=CB.END_SHIFT
            ),
        ],
        [
            InlineKeyboardButton(
                text=captions[CB.DAILY_REPORT], callback_data=CB.DAILY_REPORT
            ),
            InlineKeyboardButton(
                text=captions[CB.MONTHLY_REPORT], callback_data=CB.MONTHLY_REPORT
            ),
        ],
        [
            InlineKeyboardButton(
                text=captions[CB.TODAY], callback_data=CB.TODAY
            ),
            InlineKeyboardButton(
                text=captions[CB.SUPPORT], callback_data=CB.SUPPORT
            ),
        ],
    ]
    if is_owner:
        rows.append(
            [
                InlineKeyboardButton(
                    text=captions[CB.ADMIN_PANEL], callback_data=CB.ADMIN_PANEL
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_panel() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="ارسال همگانی", callback_data=CB.ADM_BROADCAST)],
        [
            InlineKeyboardButton(
                text="اضافه کردن دسترسی", callback_data=CB.ADM_ADD_ACCESS
            ),
            InlineKeyboardButton(
                text="حذف دسترسی", callback_data=CB.ADM_REMOVE_ACCESS
            ),
        ],
        [
            InlineKeyboardButton(
                text="شخصی‌سازی متن‌ها", callback_data=CB.ADM_CUSTOM_TEXT
            ),
            InlineKeyboardButton(
                text="شخصی‌سازی دکمه‌ها", callback_data=CB.ADM_CUSTOM_BUTTON
            ),
        ],
        [
            InlineKeyboardButton(
                text="پاک کردن تمامی اطلاعات", callback_data=CB.ADM_WIPE
            )
        ],
        [InlineKeyboardButton(text="بازگشت", callback_data=CB.ADM_BACK)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def wipe_confirm_step_1() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="بله", callback_data=CB.WIPE_CONFIRM_1)],
            [InlineKeyboardButton(text="انصراف", callback_data=CB.WIPE_CANCEL)],
        ]
    )


def wipe_confirm_step_2() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="تایید نهایی", callback_data=CB.WIPE_CONFIRM_2
                )
            ],
            [InlineKeyboardButton(text="انصراف", callback_data=CB.WIPE_CANCEL)],
        ]
    )


def back_to_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="بازگشت", callback_data=CB.ADM_BACK)]
        ]
    )
