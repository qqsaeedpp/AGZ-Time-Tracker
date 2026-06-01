from __future__ import annotations

from dataclasses import dataclass

from app.database import repositories as repo
from app.database.db import session_factory
from app.utils.datetime_utils import duration_minutes, format_time_hm, now_tehran


@dataclass
class StartResult:
    started: bool
    already_active: bool


@dataclass
class EndResult:
    closed: bool
    minutes: int | None


@dataclass
class StatusResult:
    active: bool
    start_time: str | None = None  # "HH:MM" snapshot
    elapsed_minutes: int | None = None  # computed once, at click time


async def get_status(user_id: int) -> StatusResult:
    """Return a point-in-time snapshot of the user's answering status.

    The elapsed duration is computed once, at call time — it is NOT a live
    counter and is never auto-refreshed."""
    async with session_factory() as session:
        active = await repo.get_active_shift(session, user_id)
    if active is None:
        return StatusResult(active=False)
    return StatusResult(
        active=True,
        start_time=format_time_hm(active.start_time),
        elapsed_minutes=duration_minutes(active.start_time, now_tehran()),
    )


async def start_shift(user_id: int) -> StartResult:
    """Start a shift transaction-safely. The active-shift row lock plus the
    partial unique index guarantee a single active shift per user even under
    concurrent taps."""
    async with session_factory() as session:
        async with session.begin():
            active = await repo.get_active_shift_for_update(session, user_id)
            if active is not None:
                return StartResult(started=False, already_active=True)
            await repo.create_shift(session, user_id, now_tehran())
            await repo.add_action_log(session, user_id, "start_shift")
    return StartResult(started=True, already_active=False)


async def end_shift(user_id: int) -> EndResult:
    async with session_factory() as session:
        async with session.begin():
            active = await repo.get_active_shift_for_update(session, user_id)
            if active is None:
                return EndResult(closed=False, minutes=None)
            end_time = now_tehran()
            minutes = duration_minutes(active.start_time, end_time)
            await repo.close_shift(session, active, end_time, minutes)
            await repo.add_action_log(session, user_id, "end_shift")
    return EndResult(closed=True, minutes=minutes)
