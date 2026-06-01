from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.database import repositories as repo
from app.database.db import session_factory
from app.database.models import User
from app.utils.datetime_utils import (
    day_bounds_tehran,
    format_time_hm,
    month_bounds_tehran,
)
from app.utils.formatters import user_display
from app.utils.jalali_utils import jalali_month_label, to_jalali_date


@dataclass
class Interval:
    start: str
    end: str
    minutes: int


@dataclass
class UserDailyEntry:
    display: str
    total_minutes: int
    intervals: list[Interval] = field(default_factory=list)


@dataclass
class DailyReport:
    date_label: str
    online_users: list[str]
    users: list[UserDailyEntry]
    team_total_minutes: int
    user_count: int


@dataclass
class UserMonthlyEntry:
    display: str
    total_minutes: int


@dataclass
class MonthlyReport:
    month_label: str
    ranking: list[UserMonthlyEntry]
    team_total_minutes: int
    user_count: int


async def _users_by_id(session, user_ids: set[int]) -> dict[int, User]:
    users: dict[int, User] = {}
    for uid in user_ids:
        user = await repo.get_user_by_id(session, uid)
        if user is not None:
            users[uid] = user
    return users


async def build_daily_report(reference: datetime | None = None) -> DailyReport:
    start, end = day_bounds_tehran(reference)
    async with session_factory() as session:
        shifts = await repo.get_closed_shifts_between(session, start, end)
        active = await repo.get_active_shifts(session)

        user_ids = {s.user_id for s in shifts} | {s.user_id for s in active}
        users = await _users_by_id(session, user_ids)

    grouped: dict[int, UserDailyEntry] = {}
    for shift in shifts:
        user = users.get(shift.user_id)
        display = user_display(
            user.username if user else None, user.first_name if user else None
        )
        entry = grouped.get(shift.user_id)
        if entry is None:
            entry = UserDailyEntry(display=display, total_minutes=0)
            grouped[shift.user_id] = entry
        minutes = shift.duration_minutes or 0
        entry.total_minutes += minutes
        entry.intervals.append(
            Interval(
                start=format_time_hm(shift.start_time),
                end=format_time_hm(shift.end_time) if shift.end_time else "--:--",
                minutes=minutes,
            )
        )

    online_users: list[str] = []
    for shift in active:
        user = users.get(shift.user_id)
        online_users.append(
            user_display(
                user.username if user else None,
                user.first_name if user else None,
            )
        )

    entries = list(grouped.values())
    team_total = sum(e.total_minutes for e in entries)

    return DailyReport(
        date_label=to_jalali_date(reference),
        online_users=online_users,
        users=entries,
        team_total_minutes=team_total,
        user_count=len(entries),
    )


async def build_monthly_report(reference: datetime | None = None) -> MonthlyReport:
    start, end = month_bounds_tehran(reference)
    async with session_factory() as session:
        shifts = await repo.get_closed_shifts_between(session, start, end)
        user_ids = {s.user_id for s in shifts}
        users = await _users_by_id(session, user_ids)

    totals: dict[int, int] = {}
    for shift in shifts:
        totals[shift.user_id] = totals.get(shift.user_id, 0) + (
            shift.duration_minutes or 0
        )

    ranking = [
        UserMonthlyEntry(
            display=user_display(
                users[uid].username if uid in users else None,
                users[uid].first_name if uid in users else None,
            ),
            total_minutes=minutes,
        )
        for uid, minutes in totals.items()
    ]
    ranking.sort(key=lambda e: e.total_minutes, reverse=True)

    return MonthlyReport(
        month_label=jalali_month_label(reference),
        ranking=ranking,
        team_total_minutes=sum(totals.values()),
        user_count=len(ranking),
    )
