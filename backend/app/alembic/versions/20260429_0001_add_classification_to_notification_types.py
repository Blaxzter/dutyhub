"""Add classification to notification_types

Revision ID: 20260429_0001
Revises: 20260428_0001
Create Date: 2026-04-29 09:00:00.000000

"""

import sqlalchemy as sa
from alembic import op


revision = "20260429_0001"
down_revision = "20260428_0001"
branch_labels = None
depends_on = None


# Backfill map — kept in sync with app.logic.notifications.registry.
_CLASSIFICATION_BY_CODE: dict[str, str] = {
    "booking.confirmed": "change",
    "booking.cancelled_by_user": "change",
    "booking.cancelled_by_admin": "change",
    "booking.shift_cobooked": "announcement",
    "booking.reminder": "reminder",
    "shift.starting_soon_unfilled": "reminder",
    "shift.time_changed": "change",
    "task.published": "match",
    "event.published": "match",
    "availability.reminder": "reminder",
    "user.registered": "announcement",
    "user.approved": "change",
    "user.rejected": "change",
}


def upgrade() -> None:
    op.add_column(
        "notification_types",
        sa.Column(
            "classification",
            sa.String(),
            nullable=False,
            server_default="announcement",
        ),
    )
    op.create_index(
        "ix_notification_types_classification",
        "notification_types",
        ["classification"],
    )

    # Backfill rows that already exist for known codes.
    for code, classification in _CLASSIFICATION_BY_CODE.items():
        op.execute(
            sa.text(
                "UPDATE notification_types SET classification = :c WHERE code = :code"
            ).bindparams(c=classification, code=code)
        )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_types_classification", table_name="notification_types"
    )
    op.drop_column("notification_types", "classification")
