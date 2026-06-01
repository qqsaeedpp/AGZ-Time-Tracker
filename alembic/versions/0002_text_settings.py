"""text settings (custom texts + premium emoji)

Revision ID: 0002_text_settings
Revises: 0001_initial
Create Date: 2026-06-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_text_settings"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE_OPTS = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}


def upgrade() -> None:
    op.create_table(
        "text_settings",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("text_key", sa.String(length=64), nullable=False),
        sa.Column("text_value", sa.Text(), nullable=False),
        sa.Column("custom_emoji_id", sa.String(length=64), nullable=True),
        sa.Column("formatting_config", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        **_TABLE_OPTS,
    )
    op.create_index(
        "ix_text_settings_text_key", "text_settings", ["text_key"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_text_settings_text_key", table_name="text_settings")
    op.drop_table("text_settings")
