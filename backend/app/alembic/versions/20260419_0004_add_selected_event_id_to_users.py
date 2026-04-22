"""Add selected_event_id to users

Revision ID: 20260419_0004
Revises: 20260419_0003
Create Date: 2026-04-19
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260419_0004"
down_revision = "20260419_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("selected_event_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_users_selected_event_id",
        "users",
        ["selected_event_id"],
    )
    op.create_foreign_key(
        "users_selected_event_id_fkey",
        "users",
        "events",
        ["selected_event_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("users_selected_event_id_fkey", "users", type_="foreignkey")
    op.drop_index("ix_users_selected_event_id", table_name="users")
    op.drop_column("users", "selected_event_id")
