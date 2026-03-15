"""Add global notification channel toggles to users

Revision ID: 20260315_0001
Revises: 20260313_0001
Create Date: 2026-03-15 22:47:51.169768

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260315_0001"
down_revision = "20260313_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("notify_email", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "users",
        sa.Column("notify_push", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "users",
        sa.Column("notify_telegram", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade():
    op.drop_column("users", "notify_telegram")
    op.drop_column("users", "notify_push")
    op.drop_column("users", "notify_email")
