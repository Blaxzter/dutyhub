"""Add time_format to users

Revision ID: 20260428_0001
Revises: 20260426_0001
Create Date: 2026-04-28 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260428_0001"
down_revision = "20260426_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column(
            "time_format",
            sa.String(10),
            nullable=False,
            server_default="locale",
        ),
    )


def downgrade():
    op.drop_column("users", "time_format")
