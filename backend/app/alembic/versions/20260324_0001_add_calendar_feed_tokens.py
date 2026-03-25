"""Add calendar_feed_tokens table

Revision ID: 20260324_0001
Revises: 20260323_0002
Create Date: 2026-03-24 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260324_0001"
down_revision = "20260323_0002"


def upgrade() -> None:
    op.create_table(
        "calendar_feed_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_accessed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_calendar_feed_tokens_id"), "calendar_feed_tokens", ["id"]
    )
    op.create_index(
        op.f("ix_calendar_feed_tokens_user_id"),
        "calendar_feed_tokens",
        ["user_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_calendar_feed_tokens_token"),
        "calendar_feed_tokens",
        ["token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_calendar_feed_tokens_token"), table_name="calendar_feed_tokens"
    )
    op.drop_index(
        op.f("ix_calendar_feed_tokens_user_id"), table_name="calendar_feed_tokens"
    )
    op.drop_index(
        op.f("ix_calendar_feed_tokens_id"), table_name="calendar_feed_tokens"
    )
    op.drop_table("calendar_feed_tokens")
