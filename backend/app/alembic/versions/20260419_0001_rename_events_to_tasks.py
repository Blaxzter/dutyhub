"""Rename events -> tasks (step 1 of 3 terminology rename)

Revision ID: 20260419_0001
Revises: 20260406_0001
Create Date: 2026-04-19

Step 1 of 3-part rename: the old "Event" domain concept (a specific unit
of work) becomes "Task". The next migrations rename EventGroup -> Event
and DutySlot -> Shift.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260419_0001"
down_revision = "20260406_0001"
branch_labels = None
depends_on = None


def upgrade():
    # Rename table events -> tasks
    op.rename_table("events", "tasks")

    # Rename FK columns in child tables (events.id is now tasks.id)
    op.alter_column("duty_slots", "event_id", new_column_name="task_id")
    op.alter_column("slot_batches", "event_id", new_column_name="task_id")

    # Rename snapshot column on bookings
    op.alter_column(
        "bookings", "cancelled_event_name", new_column_name="cancelled_task_name"
    )

    # Rename per-column indices created by autogenerate (ix_<table>_<col>)
    op.execute(
        "ALTER INDEX ix_duty_slots_event_id RENAME TO ix_duty_slots_task_id"
    )
    op.execute(
        "ALTER INDEX ix_slot_batches_event_id RENAME TO ix_slot_batches_task_id"
    )
    # Rename composite index from feed query indexes migration
    op.execute(
        "ALTER INDEX ix_duty_slots_event_id_date RENAME TO ix_duty_slots_task_id_date"
    )

    # Rename foreign-key constraints
    op.execute(
        "ALTER TABLE duty_slots RENAME CONSTRAINT duty_slots_event_id_fkey TO duty_slots_task_id_fkey"
    )
    op.execute(
        "ALTER TABLE slot_batches RENAME CONSTRAINT slot_batches_event_id_fkey TO slot_batches_task_id_fkey"
    )

    # Rename primary-key constraint on the old events table
    op.execute("ALTER TABLE tasks RENAME CONSTRAINT events_pkey TO tasks_pkey")

    # Data migration: notification subscription scopes + type codes
    op.execute(
        "UPDATE notification_subscriptions SET scope_type = 'task' WHERE scope_type = 'event'"
    )
    op.execute(
        "UPDATE notification_types SET code = 'task.published' WHERE code = 'event.published'"
    )
    op.execute(
        "UPDATE notification_types SET category = 'task' WHERE category = 'event'"
    )
    op.execute(
        "UPDATE notification_types SET name = 'Task Published' WHERE code = 'task.published'"
    )
    op.execute(
        "UPDATE notification_types SET description = 'Notification when a new task is published' WHERE code = 'task.published'"
    )


def downgrade():
    op.execute(
        "UPDATE notification_types SET description = 'Notification when a new event is published' WHERE code = 'task.published'"
    )
    op.execute(
        "UPDATE notification_types SET name = 'Event Published' WHERE code = 'task.published'"
    )
    op.execute(
        "UPDATE notification_types SET category = 'event' WHERE category = 'task'"
    )
    op.execute(
        "UPDATE notification_types SET code = 'event.published' WHERE code = 'task.published'"
    )
    op.execute(
        "UPDATE notification_subscriptions SET scope_type = 'event' WHERE scope_type = 'task'"
    )

    op.execute("ALTER TABLE tasks RENAME CONSTRAINT tasks_pkey TO events_pkey")
    op.execute(
        "ALTER TABLE slot_batches RENAME CONSTRAINT slot_batches_task_id_fkey TO slot_batches_event_id_fkey"
    )
    op.execute(
        "ALTER TABLE duty_slots RENAME CONSTRAINT duty_slots_task_id_fkey TO duty_slots_event_id_fkey"
    )
    op.execute(
        "ALTER INDEX ix_duty_slots_task_id_date RENAME TO ix_duty_slots_event_id_date"
    )
    op.execute(
        "ALTER INDEX ix_slot_batches_task_id RENAME TO ix_slot_batches_event_id"
    )
    op.execute(
        "ALTER INDEX ix_duty_slots_task_id RENAME TO ix_duty_slots_event_id"
    )

    op.alter_column(
        "bookings", "cancelled_task_name", new_column_name="cancelled_event_name"
    )
    op.alter_column("slot_batches", "task_id", new_column_name="event_id")
    op.alter_column("duty_slots", "task_id", new_column_name="event_id")
    op.rename_table("tasks", "events")
