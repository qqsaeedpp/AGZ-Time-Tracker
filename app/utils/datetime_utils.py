from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import settings

TEHRAN_TZ = ZoneInfo(settings.timezone)


def now_tehran() -> datetime:
    return datetime.now(TEHRAN_TZ)


def to_tehran(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(TEHRAN_TZ)


def duration_minutes(start: datetime, end: datetime) -> int:
    delta = end - start
    return max(0, int(delta.total_seconds() // 60))


def day_bounds_tehran(reference: datetime | None = None) -> tuple[datetime, datetime]:
    """Return [start, end) of the Tehran day containing `reference`."""
    ref = to_tehran(reference) if reference else now_tehran()
    start = ref.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


def month_bounds_tehran(
    reference: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Return [start, end) of the Jalali month containing `reference`."""
    import jdatetime

    ref = to_tehran(reference) if reference else now_tehran()
    j = jdatetime.datetime.fromgregorian(datetime=ref)
    j_start = jdatetime.datetime(j.year, j.month, 1, tzinfo=TEHRAN_TZ)
    if j.month == 12:
        next_month = jdatetime.datetime(j.year + 1, 1, 1, tzinfo=TEHRAN_TZ)
    else:
        next_month = jdatetime.datetime(j.year, j.month + 1, 1, tzinfo=TEHRAN_TZ)
    return j_start.togregorian(), next_month.togregorian()


def format_time_hm(dt: datetime) -> str:
    return to_tehran(dt).strftime("%H:%M")
