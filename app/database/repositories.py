from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    SHIFT_ACTIVE,
    SHIFT_CLOSED,
    ActionLog,
    AdminState,
    ButtonSetting,
    ReportTarget,
    Setting,
    Shift,
    TextSetting,
    User,
)


# ----------------------------- Users -----------------------------
async def get_user_by_telegram_id(
    session: AsyncSession, telegram_id: int
) -> User | None:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    is_owner: bool = False,
    is_allowed: bool = False,
) -> User:
    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        is_owner=is_owner,
        is_allowed=is_allowed or is_owner,
    )
    session.add(user)
    await session.flush()
    return user


async def set_user_allowed(
    session: AsyncSession, telegram_id: int, is_allowed: bool
) -> User | None:
    user = await get_user_by_telegram_id(session, telegram_id)
    if user is None:
        return None
    user.is_allowed = is_allowed
    await session.flush()
    return user


async def list_allowed_users(session: AsyncSession) -> list[User]:
    result = await session.execute(
        select(User).where(User.is_allowed.is_(True))
    )
    return list(result.scalars().all())


# ----------------------------- Shifts -----------------------------
async def get_active_shift_for_update(
    session: AsyncSession, user_id: int
) -> Shift | None:
    result = await session.execute(
        select(Shift)
        .where(Shift.user_id == user_id, Shift.status == SHIFT_ACTIVE)
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def get_active_shift(session: AsyncSession, user_id: int) -> Shift | None:
    """Read-only fetch of the user's active shift (no row lock)."""
    result = await session.execute(
        select(Shift).where(
            Shift.user_id == user_id, Shift.status == SHIFT_ACTIVE
        )
    )
    return result.scalar_one_or_none()


async def create_shift(
    session: AsyncSession, user_id: int, start_time: datetime
) -> Shift:
    shift = Shift(user_id=user_id, start_time=start_time, status=SHIFT_ACTIVE)
    session.add(shift)
    await session.flush()
    return shift


async def close_shift(
    session: AsyncSession,
    shift: Shift,
    end_time: datetime,
    duration_minutes: int,
) -> Shift:
    shift.end_time = end_time
    shift.duration_minutes = duration_minutes
    shift.status = SHIFT_CLOSED
    await session.flush()
    return shift


async def get_closed_shifts_between(
    session: AsyncSession, start: datetime, end: datetime
) -> list[Shift]:
    result = await session.execute(
        select(Shift)
        .where(
            Shift.status == SHIFT_CLOSED,
            Shift.start_time >= start,
            Shift.start_time < end,
        )
        .order_by(Shift.user_id, Shift.start_time)
    )
    return list(result.scalars().all())


async def get_active_shifts(session: AsyncSession) -> list[Shift]:
    result = await session.execute(
        select(Shift).where(Shift.status == SHIFT_ACTIVE)
    )
    return list(result.scalars().all())


# ----------------------------- Settings -----------------------------
async def get_setting(session: AsyncSession, key: str) -> str | None:
    result = await session.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    return setting.value if setting else None


async def set_setting(session: AsyncSession, key: str, value: str) -> None:
    result = await session.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if setting is None:
        session.add(Setting(key=key, value=value))
    else:
        setting.value = value
    await session.flush()


async def get_all_settings(session: AsyncSession) -> dict[str, str]:
    result = await session.execute(select(Setting))
    return {s.key: s.value for s in result.scalars().all()}


async def delete_setting(session: AsyncSession, key: str) -> None:
    await session.execute(delete(Setting).where(Setting.key == key))


# ----------------------------- TextSettings -----------------------------
async def get_text_setting(
    session: AsyncSession, text_key: str
) -> TextSetting | None:
    result = await session.execute(
        select(TextSetting).where(TextSetting.text_key == text_key)
    )
    return result.scalar_one_or_none()


async def upsert_text_setting(
    session: AsyncSession,
    text_key: str,
    text_value: str,
    custom_emoji_id: str | None,
    formatting_config: str | None,
) -> TextSetting:
    setting = await get_text_setting(session, text_key)
    if setting is None:
        setting = TextSetting(
            text_key=text_key,
            text_value=text_value,
            custom_emoji_id=custom_emoji_id,
            formatting_config=formatting_config,
        )
        session.add(setting)
    else:
        setting.text_value = text_value
        setting.custom_emoji_id = custom_emoji_id
        setting.formatting_config = formatting_config
    await session.flush()
    return setting


async def get_all_text_settings(session: AsyncSession) -> dict[str, TextSetting]:
    result = await session.execute(select(TextSetting))
    return {s.text_key: s for s in result.scalars().all()}


# ----------------------------- ButtonSettings -----------------------------
async def get_all_button_settings(
    session: AsyncSession,
) -> dict[str, ButtonSetting]:
    result = await session.execute(select(ButtonSetting))
    return {b.button_key: b for b in result.scalars().all()}


async def upsert_button_setting(
    session: AsyncSession,
    button_key: str,
    button_text: str | None,
    button_emoji: str | None,
    button_color: str | None,
) -> ButtonSetting:
    result = await session.execute(
        select(ButtonSetting).where(ButtonSetting.button_key == button_key)
    )
    setting = result.scalar_one_or_none()
    if setting is None:
        setting = ButtonSetting(
            button_key=button_key,
            button_text=button_text,
            button_emoji=button_emoji,
            button_color=button_color,
        )
        session.add(setting)
    else:
        if button_text is not None:
            setting.button_text = button_text
        if button_emoji is not None:
            setting.button_emoji = button_emoji
        if button_color is not None:
            setting.button_color = button_color
    await session.flush()
    return setting


# ----------------------------- ReportTarget -----------------------------
async def get_active_report_target(session: AsyncSession) -> ReportTarget | None:
    result = await session.execute(
        select(ReportTarget)
        .where(ReportTarget.is_active.is_(True))
        .order_by(ReportTarget.id.desc())
    )
    return result.scalars().first()


async def upsert_report_target(
    session: AsyncSession,
    chat_id: int,
    message_thread_id: int | None,
    installed_by: int,
) -> ReportTarget:
    # Deactivate previous targets, then create/activate the requested one.
    await session.execute(
        update(ReportTarget).values(is_active=False).where(
            ReportTarget.is_active.is_(True)
        )
    )
    result = await session.execute(
        select(ReportTarget).where(
            ReportTarget.chat_id == chat_id,
            ReportTarget.message_thread_id.is_(message_thread_id)
            if message_thread_id is None
            else ReportTarget.message_thread_id == message_thread_id,
        )
    )
    target = result.scalars().first()
    if target is None:
        target = ReportTarget(
            chat_id=chat_id,
            message_thread_id=message_thread_id,
            installed_by=installed_by,
            is_active=True,
        )
        session.add(target)
    else:
        target.is_active = True
        target.installed_by = installed_by
    await session.flush()
    return target


async def deactivate_report_targets(session: AsyncSession) -> None:
    await session.execute(
        update(ReportTarget).values(is_active=False).where(
            ReportTarget.is_active.is_(True)
        )
    )


# ----------------------------- AdminState -----------------------------
async def get_admin_state(session: AsyncSession, user_id: int) -> AdminState | None:
    result = await session.execute(
        select(AdminState).where(AdminState.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def set_admin_state(
    session: AsyncSession,
    user_id: int,
    state: str | None,
    payload: str | None = None,
) -> AdminState:
    admin_state = await get_admin_state(session, user_id)
    if admin_state is None:
        admin_state = AdminState(user_id=user_id, state=state, payload=payload)
        session.add(admin_state)
    else:
        admin_state.state = state
        admin_state.payload = payload
    await session.flush()
    return admin_state


async def clear_admin_state(session: AsyncSession, user_id: int) -> None:
    await session.execute(
        delete(AdminState).where(AdminState.user_id == user_id)
    )


# ----------------------------- ActionLog -----------------------------
async def add_action_log(
    session: AsyncSession, user_id: int, action: str
) -> None:
    session.add(ActionLog(user_id=user_id, action=action))
    await session.flush()


# ----------------------------- Wipe -----------------------------
async def wipe_operational_data(session: AsyncSession) -> None:
    await session.execute(delete(Shift))
    await session.execute(delete(ActionLog))
    await session.execute(delete(AdminState))
