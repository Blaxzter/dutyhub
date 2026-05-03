"""Add default_start_time and default_end_time to events

Revision ID: 20260430_0001
Revises: 20260429_0002
Create Date: 2026-04-30 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op


revision = "20260430_0001"
down_revision = "20260429_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "events",
        sa.Column("default_start_time", sa.Time(), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column("default_end_time", sa.Time(), nullable=True),
    )


def downgrade():
    op.drop_column("events", "default_end_time")
    op.drop_column("events", "default_start_time")
