from __future__ import annotations

from datetime import datetime

import jdatetime

from app.utils.datetime_utils import now_tehran, to_tehran


def to_jalali_date(dt: datetime | None = None) -> str:
    ref = to_tehran(dt) if dt else now_tehran()
    j = jdatetime.datetime.fromgregorian(datetime=ref)
    return f"{j.year}/{j.month:02d}/{j.day:02d}"


def to_gregorian_date(dt: datetime | None = None) -> str:
    ref = to_tehran(dt) if dt else now_tehran()
    return ref.strftime("%Y-%m-%d")


def jalali_month_label(dt: datetime | None = None) -> str:
    ref = to_tehran(dt) if dt else now_tehran()
    j = jdatetime.datetime.fromgregorian(datetime=ref)
    return f"{j.year}/{j.month:02d}"
