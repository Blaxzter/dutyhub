"""Add indexes for feed query performance

Revision ID: 20260317_0001
Revises: 20260315_0001
Create Date: 2026-03-17 21:30:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260317_0001"
down_revision = "20260315_0001"
branch_labels = None
depends_on = None


def upgrade():
    # Composite: slot window queries filter by (event_id, date)
    op.create_index(
        "ix_duty_slots_event_id_date",
        "duty_slots",
        ["event_id", "date"],
    )
    # Composite: booking count subquery groups by duty_slot_id, filters status
    op.create_index(
        "ix_bookings_duty_slot_id_status",
        "bookings",
        ["duty_slot_id", "status"],
    )
    # Calendar date-overlap filter: WHERE end_date >= ? AND start_date <= ?
    op.create_index("ix_events_start_date", "events", ["start_date"])
    op.create_index("ix_events_end_date", "events", ["end_date"])


def downgrade():
    op.drop_index("ix_events_end_date", table_name="events")
    op.drop_index("ix_events_start_date", table_name="events")
    op.drop_index("ix_bookings_duty_slot_id_status", table_name="bookings")
    op.drop_index("ix_duty_slots_event_id_date", table_name="duty_slots")
