"""button settings (dynamic colors/emoji/text)

Revision ID: 0003_button_settings
Revises: 0002_text_settings
Create Date: 2026-06-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_button_settings"
down_revision: Union[str, None] = "0002_text_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE_OPTS = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}


def upgrade() -> None:
    op.create_table(
        "button_settings",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("button_key", sa.String(length=32), nullable=False),
        sa.Column("button_text", sa.String(length=64), nullable=True),
        sa.Column("button_emoji", sa.String(length=16), nullable=True),
        sa.Column("button_color", sa.String(length=16), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        **_TABLE_OPTS,
    )
    op.create_index(
        "ix_button_settings_button_key", "button_settings", ["button_key"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_button_settings_button_key", table_name="button_settings")
    op.drop_table("button_settings")
