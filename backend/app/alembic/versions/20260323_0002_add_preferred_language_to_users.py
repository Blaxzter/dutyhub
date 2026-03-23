"""Add preferred_language to users

Revision ID: 20260323_0002
Revises: 20260323_0001
Create Date: 2026-03-23 20:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260323_0002"
down_revision = "20260323_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("preferred_language", sa.String(5), nullable=False, server_default="en"),
    )


def downgrade():
    op.drop_column("users", "preferred_language")
