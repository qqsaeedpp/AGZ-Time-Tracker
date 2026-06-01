from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# MySQL has no timezone-aware DATETIME; the whole app works in Tehran local
# time and stores naive Tehran wall-clock values (see app.utils.datetime_utils).
_NOW = text("CURRENT_TIMESTAMP")
_MYSQL_TABLE = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}


class Base(DeclarativeBase):
    pass


SHIFT_ACTIVE = "active"
SHIFT_CLOSED = "closed"


class User(Base):
    __tablename__ = "users"
    __table_args__ = _MYSQL_TABLE

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=_NOW, nullable=False
    )

    shifts: Mapped[list["Shift"]] = relationship(back_populates="user")


class Shift(Base):
    __tablename__ = "shifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # No ON DELETE CASCADE: MySQL forbids a cascading FK whose base column
    # (user_id) feeds a STORED generated column (active_marker). Shifts are
    # removed explicitly by the wipe operation, and users are not deleted.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), default=SHIFT_ACTIVE, nullable=False
    )
    # Generated column that equals user_id only while the shift is active and is
    # NULL otherwise. A UNIQUE index on it gives a database-level guarantee of
    # at most one active shift per user (MySQL allows multiple NULLs), which is
    # the MySQL equivalent of a partial unique index.
    active_marker: Mapped[int | None] = mapped_column(
        Integer,
        Computed(
            "(CASE WHEN status = 'active' THEN user_id ELSE NULL END)",
            persisted=True,
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=_NOW, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="shifts")

    __table_args__ = (
        Index("uq_one_active_shift_per_user", "active_marker", unique=True),
        _MYSQL_TABLE,
    )


class Setting(Base):
    __tablename__ = "settings"
    __table_args__ = _MYSQL_TABLE

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class ReportTarget(Base):
    __tablename__ = "report_targets"
    __table_args__ = _MYSQL_TABLE

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_thread_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    installed_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=_NOW, nullable=False
    )


class AdminState(Base):
    __tablename__ = "admin_states"
    __table_args__ = _MYSQL_TABLE

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=_NOW,
        server_onupdate=_NOW,
        nullable=False,
    )


class ActionLog(Base):
    __tablename__ = "action_logs"
    __table_args__ = _MYSQL_TABLE

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=_NOW, nullable=False
    )


class TextSetting(Base):
    """Owner-customizable message text plus optional premium (custom) emoji.

    - ``text_value`` is the raw message body (plain text; bold/italic are
      applied at render time via message entities, never parse_mode).
    - ``custom_emoji_id`` is the numeric id of a Telegram premium/custom emoji
      used as the leading icon. When NULL the renderer falls back to a normal
      unicode emoji, so messages keep working without premium emoji.
    - ``formatting_config`` is a small JSON blob (e.g. ``{"bold_title": true}``)
      describing which formatting to apply when rendering.
    """

    __tablename__ = "text_settings"
    __table_args__ = _MYSQL_TABLE

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text_key: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    text_value: Mapped[str] = mapped_column(Text, nullable=False)
    custom_emoji_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    formatting_config: Mapped[str | None] = mapped_column(Text, nullable=True)
