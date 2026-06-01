from __future__ import annotations

from dataclasses import dataclass

from app.database import repositories as repo
from app.database.db import session_factory
from app.utils.rich import (
    REPORT_EMOJI_PREFIX,
    REPORT_ICON_SPECS,
    EmojiIcon,
)


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


@dataclass
class ButtonSettingData:
    button_key: str
    button_text: str | None
    button_style: str | None
    button_custom_emoji_id: str | None


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


# --------------------------- Report icons (premium emoji) ---------------------------
async def get_report_icons() -> dict[str, EmojiIcon]:
    """Return the icon for every report slot, applying any owner-set premium
    emoji and falling back to the default normal emoji otherwise."""
    async with session_factory() as session:
        stored = await repo.get_all_settings(session)
    icons: dict[str, EmojiIcon] = {}
    for slot, (char, _label) in REPORT_ICON_SPECS.items():
        custom_id = stored.get(f"{REPORT_EMOJI_PREFIX}{slot}") or None
        icons[slot] = EmojiIcon(char=char, custom_emoji_id=custom_id)
    return icons


async def set_report_emoji(slot: str, custom_emoji_id: str | None) -> None:
    key = f"{REPORT_EMOJI_PREFIX}{slot}"
    async with session_factory() as session:
        async with session.begin():
            if custom_emoji_id:
                await repo.set_setting(session, key, custom_emoji_id)
            else:
                await repo.delete_setting(session, key)


# --------------------------- Button settings ---------------------------
async def get_all_button_settings() -> dict[str, ButtonSettingData]:
    async with session_factory() as session:
        settings = await repo.get_all_button_settings(session)
        return {
            k: ButtonSettingData(
                button_key=v.button_key,
                button_text=v.button_text,
                button_style=v.button_style,
                button_custom_emoji_id=v.button_custom_emoji_id,
            )
            for k, v in settings.items()
        }


async def set_button_setting(
    button_key: str,
    button_text: str | None = None,
    button_style: str | None = None,
    button_custom_emoji_id: str | None = None,
) -> None:
    async with session_factory() as session:
        async with session.begin():
            await repo.upsert_button_setting(
                session,
                button_key,
                button_text,
                button_style,
                button_custom_emoji_id,
            )


# --------------------------- Maintenance ---------------------------
async def wipe_operational_data() -> None:
    """Delete shifts, action logs and admin states. Owners, core settings and
    report targets are intentionally preserved."""
    async with session_factory() as session:
        async with session.begin():
            await repo.wipe_operational_data(session)
