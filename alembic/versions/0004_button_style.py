"""migrate button_settings to native Bot API style + premium emoji

Replaces the old emoji-prefix colour columns (button_emoji, button_color) with
the official Bot API ``button_style`` plus ``button_custom_emoji_id`` and an
``updated_at`` timestamp. Existing rows are dropped because the old colour data
has no meaning under the new model (each button just falls back to its default).

Revision ID: 0004_button_style
Revises: 0003_button_settings
Create Date: 2026-06-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_button_style"
down_revision: Union[str, None] = "0003_button_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Old colour data is incompatible with the native style model; clear rows so
    # every button cleanly falls back to its built-in default style.
    op.execute("DELETE FROM button_settings")
    op.drop_column("button_settings", "button_emoji")
    op.drop_column("button_settings", "button_color")
    op.add_column(
        "button_settings",
        sa.Column("button_style", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "button_settings",
        sa.Column("button_custom_emoji_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "button_settings",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("button_settings", "updated_at")
    op.drop_column("button_settings", "button_custom_emoji_id")
    op.drop_column("button_settings", "button_style")
    op.add_column(
        "button_settings",
        sa.Column("button_color", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "button_settings",
        sa.Column("button_emoji", sa.String(length=16), nullable=True),
    )
