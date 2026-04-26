"""Add user_avatars table and replace users.picture with users.avatar_etag

Revision ID: 20260426_0001
Revises: 20260419_0004
Create Date: 2026-04-26
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260426_0001"
down_revision = "20260419_0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_avatars",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column(
            "content_type",
            sa.String(length=64),
            nullable=False,
            server_default="image/webp",
        ),
        sa.Column("etag", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_avatars_user_id"),
    )
    op.create_index(
        op.f("ix_user_avatars_id"), "user_avatars", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_user_avatars_user_id"),
        "user_avatars",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_avatars_etag"), "user_avatars", ["etag"], unique=False
    )

    op.add_column(
        "users",
        sa.Column("avatar_etag", sa.String(length=64), nullable=True),
    )
    op.drop_column("users", "picture")


def downgrade():
    op.add_column(
        "users",
        sa.Column("picture", sa.String(), nullable=True),
    )
    op.drop_column("users", "avatar_etag")

    op.drop_index(op.f("ix_user_avatars_etag"), table_name="user_avatars")
    op.drop_index(op.f("ix_user_avatars_user_id"), table_name="user_avatars")
    op.drop_index(op.f("ix_user_avatars_id"), table_name="user_avatars")
    op.drop_table("user_avatars")
