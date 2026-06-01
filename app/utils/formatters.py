from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.reports_service import DailyReport, MonthlyReport


def user_display(username: str | None, first_name: str | None) -> str:
    if username:
        return f"@{username}"
    if first_name:
        return first_name
    return "کاربر"


def format_daily_report(report: "DailyReport") -> str:
    lines: list[str] = []
    lines.append("📊 گزارش پاسخگویی")
    lines.append("")
    lines.append(f"📅 تاریخ: {report.date_label}")
    lines.append("")

    if report.online_users:
        online = "، ".join(report.online_users)
        lines.append(f"🔴 آنلاین: {online}")
    else:
        lines.append("🔴 آنلاین: ندارد")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━")

    if not report.users:
        lines.append("")
        lines.append("امروز پاسخگویی ثبت نشده است.")
    else:
        for entry in report.users:
            lines.append("")
            lines.append(f"👤 {entry.display}")
            lines.append("")
            lines.append(f"⏰ مجموع: {entry.total_minutes} دقیقه")
            lines.append("")
            for idx, interval in enumerate(entry.intervals, start=1):
                lines.append(
                    f"{idx}. {interval.start} - {interval.end}"
                    f" ({interval.minutes} دقیقه)"
                )

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append(f"📈 جمع تیم: {report.team_total_minutes} دقیقه")
    lines.append("")
    lines.append(f"👥 کاربران: {report.user_count} نفر")
    return "\n".join(lines)


def format_monthly_report(report: "MonthlyReport") -> str:
    lines: list[str] = []
    lines.append("📊 گزارش ماهانه")
    lines.append("")
    lines.append(f"📅 ماه: {report.month_label}")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━")

    if not report.ranking:
        lines.append("")
        lines.append("در این ماه پاسخگویی ثبت نشده است.")
    else:
        for rank, entry in enumerate(report.ranking, start=1):
            lines.append("")
            lines.append(
                f"{rank}. {entry.display} — {entry.total_minutes} دقیقه"
            )

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append(f"📈 جمع کل تیم: {report.team_total_minutes} دقیقه")
    lines.append("")
    lines.append(f"👥 کاربران: {report.user_count} نفر")
    return "\n".join(lines)
