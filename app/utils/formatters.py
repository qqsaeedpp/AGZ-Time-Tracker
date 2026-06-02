from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.utils.formatting import Bold, Text

from app.utils.rich import EmojiIcon, icon_node

if TYPE_CHECKING:
    from app.services.reports_service import DailyReport, MonthlyReport

# Visual separators / footer used across reports.
SEP = "━━━━━━━━━━━━━━━━━━━━━━"
FOOTER = "AGZ Support Time"


def user_display(username: str | None, first_name: str | None) -> str:
    if username:
        return f"@{username}"
    if first_name:
        return first_name
    return "کاربر"


def _default_icons() -> dict[str, EmojiIcon]:
    """Normal-emoji fallback icons, used when no report icons are supplied
    (e.g. unit tests). Mirrors REPORT_ICON_SPECS defaults."""
    from app.utils.rich import REPORT_ICON_SPECS

    return {
        slot: EmojiIcon(char=char)
        for slot, (char, _label) in REPORT_ICON_SPECS.items()
    }


def _join(lines: list[list]) -> Text:
    """Compose a multi-line :class:`Text` from a list of *lines*, where each
    line is itself a list of formatting nodes (strings, icon nodes, ``Bold``)."""
    nodes: list = []
    for index, line in enumerate(lines):
        if index:
            nodes.append("\n")
        nodes.extend(line)
    return Text(*nodes)


def format_daily_report(
    report: "DailyReport", icons: dict[str, EmojiIcon] | None = None
) -> Text:
    """Render the daily team report as a rich :class:`Text` node.

    Layout (no offline users are ever shown):

        📊 گزارش روزانه تیم پشتیبانی
        📅 تاریخ: ...
        ━━━━...
        🟢 آنلاین: N نفر      (or  🔴 آنلاین: ندارد)
        🟢 @user
        ━━━━...
        👤 @user
        ⏰ مجموع پاسخگویی: N دقیقه
        📌 بازه‌های فعالیت:
        1. 08:15 تا 11:00
        ━━━━...
        📈 مجموع تیم: N دقیقه
        👥 کاربران دارای فعالیت: N نفر
        ━━━━...
        AGZ Support Time
    """
    icons = icons or _default_icons()

    def ico(slot: str):
        return icon_node(icons[slot])

    lines: list[list] = []
    lines.append([ico("report"), " ", Bold("گزارش روزانه تیم پشتیبانی")])
    lines.append([ico("date"), " ", "تاریخ: ", report.date_label])
    lines.append([SEP])

    # Online block (online == users with an active shift right now).
    if report.online_users:
        lines.append(
            [ico("online"), " ", Bold(f"آنلاین: {len(report.online_users)} نفر")]
        )
        for name in report.online_users:
            lines.append([ico("online"), " ", name])
    else:
        lines.append([ico("offline"), " ", "آنلاین: ندارد"])
    lines.append([SEP])

    # Per-user activity blocks.
    if not report.users:
        lines.append(["امروز پاسخگویی ثبت نشده است."])
        lines.append([SEP])
    else:
        for entry in report.users:
            lines.append([ico("user"), " ", Bold(entry.display)])
            lines.append(
                [ico("clock"), " ", f"مجموع پاسخگویی: {entry.total_minutes} دقیقه"]
            )
            lines.append([ico("intervals"), " ", "بازه‌های فعالیت:"])
            for idx, interval in enumerate(entry.intervals, start=1):
                suffix = " 🟢 فعال" if interval.active else ""
                lines.append(
                    [
                        f"{idx}. {interval.start} تا {interval.end} "
                        f"({interval.minutes} دقیقه){suffix}"
                    ]
                )
            lines.append([SEP])

    lines.append([ico("team"), " ", f"مجموع تیم: {report.team_total_minutes} دقیقه"])
    lines.append([ico("users"), " ", f"کاربران دارای فعالیت: {report.user_count} نفر"])
    lines.append([SEP])
    lines.append([Bold(FOOTER)])

    return _join(lines)


def format_monthly_report(
    report: "MonthlyReport", icons: dict[str, EmojiIcon] | None = None
) -> Text:
    """Render the monthly team report as a rich :class:`Text` node."""
    icons = icons or _default_icons()

    def ico(slot: str):
        return icon_node(icons[slot])

    lines: list[list] = []
    lines.append([ico("report"), " ", Bold("گزارش ماهانه تیم پشتیبانی")])
    lines.append([ico("date"), " ", "ماه: ", report.month_label])
    lines.append([SEP])

    if not report.ranking:
        lines.append(["در این ماه پاسخگویی ثبت نشده است."])
    else:
        for rank, entry in enumerate(report.ranking, start=1):
            lines.append(
                [f"{rank}. ", entry.display, f" — {entry.total_minutes} دقیقه"]
            )
    lines.append([SEP])

    lines.append([ico("team"), " ", f"مجموع کل تیم: {report.team_total_minutes} دقیقه"])
    lines.append([ico("users"), " ", f"کاربران: {report.user_count} نفر"])
    lines.append([SEP])
    lines.append([Bold(FOOTER)])

    return _join(lines)
