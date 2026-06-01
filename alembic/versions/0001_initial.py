"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NOW = sa.text("CURRENT_TIMESTAMP")
_TABLE_OPTS = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("first_name", sa.String(length=128), nullable=True),
        sa.Column("is_allowed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_owner", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        **_TABLE_OPTS,
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "shifts",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column(
            "active_marker",
            sa.Integer(),
            sa.Computed(
                "(CASE WHEN status = 'active' THEN user_id ELSE NULL END)",
                persisted=True,
            ),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=_NOW, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        **_TABLE_OPTS,
    )
    op.create_index("ix_shifts_user_id", "shifts", ["user_id"], unique=False)
    op.create_index(
        "uq_one_active_shift_per_user", "shifts", ["active_marker"], unique=True
    )

    op.create_table(
        "settings",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        **_TABLE_OPTS,
    )
    op.create_index("ix_settings_key", "settings", ["key"], unique=True)

    op.create_table(
        "report_targets",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("message_thread_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("installed_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        **_TABLE_OPTS,
    )

    op.create_table(
        "admin_states",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=_NOW,
            server_onupdate=_NOW,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        **_TABLE_OPTS,
    )
    op.create_index("ix_admin_states_user_id", "admin_states", ["user_id"], unique=True)

    op.create_table(
        "action_logs",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        **_TABLE_OPTS,
    )
    op.create_index("ix_action_logs_user_id", "action_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_action_logs_user_id", table_name="action_logs")
    op.drop_table("action_logs")
    op.drop_index("ix_admin_states_user_id", table_name="admin_states")
    op.drop_table("admin_states")
    op.drop_table("report_targets")
    op.drop_index("ix_settings_key", table_name="settings")
    op.drop_table("settings")
    op.drop_index("uq_one_active_shift_per_user", table_name="shifts")
    op.drop_index("ix_shifts_user_id", table_name="shifts")
    op.drop_table("shifts")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")
