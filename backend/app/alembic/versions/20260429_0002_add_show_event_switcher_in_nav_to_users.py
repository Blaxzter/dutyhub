"""Add show_event_switcher_in_nav to users

Revision ID: 20260429_0002
Revises: 20260429_0001
Create Date: 2026-04-29 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op


revision = "20260429_0002"
down_revision = "20260429_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column(
            "show_event_switcher_in_nav",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade():
    op.drop_column("users", "show_event_switcher_in_nav")
