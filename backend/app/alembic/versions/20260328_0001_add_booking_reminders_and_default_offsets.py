"""Add booking_reminders table and default_reminder_offsets to users

Revision ID: 20260328_0001
Revises: 20260324_0001
Create Date: 2026-03-28 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = "20260328_0001"
down_revision = "20260324_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "booking_reminders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("duty_slot_id", sa.Uuid(), nullable=True),
        sa.Column("remind_at", sa.DateTime(), nullable=False),
        sa.Column("offset_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(), nullable=False, server_default="pending"
        ),
        sa.Column(
            "channels", JSONB(), nullable=False, server_default='["push"]'
        ),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["duty_slot_id"],
            ["duty_slots.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "booking_id", "offset_minutes", name="uq_reminder_booking_offset"
        ),
    )
    op.create_index(
        "ix_booking_reminders_booking_id",
        "booking_reminders",
        ["booking_id"],
    )
    op.create_index(
        "ix_booking_reminders_user_id",
        "booking_reminders",
        ["user_id"],
    )
    op.create_index(
        "ix_booking_reminders_poll",
        "booking_reminders",
        ["status", "remind_at"],
    )

    # Add default_reminder_offsets to users (with sensible defaults for existing users)
    _default_reminders = '[{"offset_minutes": 15, "channels": ["push"]}, {"offset_minutes": 1440, "channels": ["email"]}]'
    op.add_column(
        "users",
        sa.Column(
            "default_reminder_offsets",
            JSONB(),
            nullable=False,
            server_default=_default_reminders,
        ),
    )

    # Add is_user_configurable to notification_types
    op.add_column(
        "notification_types",
        sa.Column(
            "is_user_configurable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("notification_types", "is_user_configurable")
    op.drop_column("users", "default_reminder_offsets")
    op.drop_index("ix_booking_reminders_poll", table_name="booking_reminders")
    op.drop_index("ix_booking_reminders_user_id", table_name="booking_reminders")
    op.drop_index("ix_booking_reminders_booking_id", table_name="booking_reminders")
    op.drop_table("booking_reminders")
