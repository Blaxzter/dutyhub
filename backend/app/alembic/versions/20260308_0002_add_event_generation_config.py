"""Add event generation config

Revision ID: 20260308_0002
Revises: 20260308_0001
Create Date: 2026-03-08 16:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

revision = "20260308_0002"
down_revision = "20260308_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("events", sa.Column("location", sa.String(), nullable=True))
    op.add_column("events", sa.Column("category", sa.String(), nullable=True))
    op.add_column(
        "events", sa.Column("slot_duration_minutes", sa.Integer(), nullable=True)
    )
    op.add_column(
        "events", sa.Column("default_start_time", sa.Time(), nullable=True)
    )
    op.add_column(
        "events", sa.Column("default_end_time", sa.Time(), nullable=True)
    )
    op.add_column(
        "events", sa.Column("people_per_slot", sa.Integer(), nullable=True)
    )
    op.add_column(
        "events", sa.Column("schedule_overrides", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("events", "schedule_overrides")
    op.drop_column("events", "people_per_slot")
    op.drop_column("events", "default_end_time")
    op.drop_column("events", "default_start_time")
    op.drop_column("events", "slot_duration_minutes")
    op.drop_column("events", "category")
    op.drop_column("events", "location")
