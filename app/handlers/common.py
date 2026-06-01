from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup

from app.bot.keyboards import CB, main_menu
from app.database.models import User
from app.services import settings_service
from app.utils.datetime_utils import now_tehran
from app.utils.jalali_utils import to_gregorian_date, to_jalali_date

router = Router(name="common")

BUTTON_PREFIX = "button:"
TEXT_PREFIX = "text:"

NO_ACCESS = "شما اجازه دسترسی به این ربات را ندارید."

DEFAULT_TEXTS: dict[str, str] = {
    "welcome": "به ربات ثبت زمان پشتیبانی AGZ خوش آمدید.\nیکی از گزینه‌ها را انتخاب کنید:",
    "support": "جهت پشتیبانی ربات:\n\n@amirjrha",
    "start_already": "شما هم‌اکنون در حال پاسخگویی هستید.",
    "start_ok": "زمان اولیه پاسخگویی شما در سیستم ثبت شد.",
    "end_none": "شیفت فعالی برای شما یافت نشد.",
    "daily_user_notice": "گزارش روزانه هر شب ساعت 23 در تاپیک ورود و خروج ارسال می‌شود.",
    "monthly_user_notice": "گزارش ماهانه توسط مدیریت منتشر می‌شود.",
}


async def get_text(key: str) -> str:
    default = DEFAULT_TEXTS.get(key, "")
    return await settings_service.get_custom_value(f"{TEXT_PREFIX}{key}", default)


async def menu_markup(user: User) -> InlineKeyboardMarkup:
    custom = await settings_service.get_all_custom_values()
    labels = {
        k[len(BUTTON_PREFIX):]: v
        for k, v in custom.items()
        if k.startswith(BUTTON_PREFIX)
    }
    return main_menu(is_owner=user.is_owner, labels=labels)


def format_today() -> str:
    now = now_tehran()
    return (
        "📅 تاریخ امروز\n\n"
        f"شمسی: {to_jalali_date(now)}\n"
        f"میلادی: {to_gregorian_date(now)}\n"
        f"ساعت تهران: {now.strftime('%H:%M')}"
    )


@router.callback_query(F.data == CB.TODAY)
async def on_today(callback: CallbackQuery, db_user: User) -> None:
    if not db_user.is_allowed:
        await callback.answer(NO_ACCESS, show_alert=True)
        return
    await callback.message.answer(format_today())
    await callback.answer()


@router.callback_query(F.data == CB.SUPPORT)
async def on_support(callback: CallbackQuery, db_user: User) -> None:
    if not db_user.is_allowed:
        await callback.answer(NO_ACCESS, show_alert=True)
        return
    await callback.message.answer(await get_text("support"))
    await callback.answer()


@router.callback_query()
async def on_unknown_callback(callback: CallbackQuery) -> None:
    # Fallback for stale/expired inline buttons.
    await callback.answer()
