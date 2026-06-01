from __future__ import annotations

from dataclasses import dataclass

from app.database import repositories as repo
from app.database.db import session_factory


@dataclass
class ReportTargetInfo:
    chat_id: int
    message_thread_id: int | None


@dataclass
class TextSettingData:
    text_key: str
    text_value: str
    custom_emoji_id: str | None
    formatting_config: str | None


# --------------------------- Report target ---------------------------
async def install_report_target(
    chat_id: int, message_thread_id: int | None, installed_by: int
) -> None:
    async with session_factory() as session:
        async with session.begin():
            await repo.upsert_report_target(
                session, chat_id, message_thread_id, installed_by
            )


async def remove_report_target() -> None:
    async with session_factory() as session:
        async with session.begin():
            await repo.deactivate_report_targets(session)


async def get_report_target() -> ReportTargetInfo | None:
    async with session_factory() as session:
        target = await repo.get_active_report_target(session)
        if target is None:
            return None
        return ReportTargetInfo(
            chat_id=target.chat_id,
            message_thread_id=target.message_thread_id,
        )


# --------------------------- Custom texts / buttons ---------------------------
async def get_custom_value(key: str, default: str) -> str:
    async with session_factory() as session:
        value = await repo.get_setting(session, key)
        return value if value is not None else default


async def set_custom_value(key: str, value: str) -> None:
    async with session_factory() as session:
        async with session.begin():
            await repo.set_setting(session, key, value)


async def get_all_custom_values() -> dict[str, str]:
    async with session_factory() as session:
        return await repo.get_all_settings(session)


# --------------------------- Customizable rich texts ---------------------------
def _to_data(setting) -> TextSettingData:
    return TextSettingData(
        text_key=setting.text_key,
        text_value=setting.text_value,
        custom_emoji_id=setting.custom_emoji_id,
        formatting_config=setting.formatting_config,
    )


async def get_text_setting(text_key: str) -> TextSettingData | None:
    async with session_factory() as session:
        setting = await repo.get_text_setting(session, text_key)
        return _to_data(setting) if setting is not None else None


async def set_text_setting(
    text_key: str,
    text_value: str,
    custom_emoji_id: str | None,
    formatting_config: str | None,
) -> None:
    async with session_factory() as session:
        async with session.begin():
            await repo.upsert_text_setting(
                session, text_key, text_value, custom_emoji_id, formatting_config
            )


async def get_all_text_settings() -> dict[str, TextSettingData]:
    async with session_factory() as session:
        settings = await repo.get_all_text_settings(session)
        return {k: _to_data(v) for k, v in settings.items()}


# --------------------------- Maintenance ---------------------------
async def wipe_operational_data() -> None:
    """Delete shifts, action logs and admin states. Owners, core settings and
    report targets are intentionally preserved."""
    async with session_factory() as session:
        async with session.begin():
            await repo.wipe_operational_data(session)
