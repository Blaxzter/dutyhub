"""Add phone_number to users

Revision ID: 20260323_0001
Revises: 20260317_0001
Create Date: 2026-03-23 18:42:38.918290

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260323_0001"
down_revision = "20260317_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("phone_number", sa.String(), nullable=True))


def downgrade():
    op.drop_column("users", "phone_number")
