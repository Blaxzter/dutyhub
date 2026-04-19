"""Rename duty_slots -> shifts, slot_batches -> shift_batches (step 3 of 3)

Revision ID: 20260419_0003
Revises: 20260419_0002
Create Date: 2026-04-19

Final step of the 3-part rename: DutySlot (a bookable time block within
a Task) becomes Shift. SlotBatch becomes ShiftBatch.

Also renames scalar columns inside tasks/shift_batches
(slot_duration_minutes -> shift_duration_minutes, people_per_slot ->
people_per_shift) and bookings.cancelled_slot_* snapshot columns.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260419_0003"
down_revision = "20260419_0002"
branch_labels = None
depends_on = None


def upgrade():
    # Rename tables
    op.rename_table("duty_slots", "shifts")
    op.rename_table("slot_batches", "shift_batches")

    # Rename FK column on bookings + booking_reminders
    op.alter_column("bookings", "duty_slot_id", new_column_name="shift_id")
    op.alter_column("booking_reminders", "duty_slot_id", new_column_name="shift_id")

    # Rename snapshot columns on bookings
    op.alter_column(
        "bookings", "cancelled_slot_title", new_column_name="cancelled_shift_title"
    )
    op.alter_column(
        "bookings", "cancelled_slot_date", new_column_name="cancelled_shift_date"
    )
    op.alter_column(
        "bookings",
        "cancelled_slot_start_time",
        new_column_name="cancelled_shift_start_time",
    )
    op.alter_column(
        "bookings",
        "cancelled_slot_end_time",
        new_column_name="cancelled_shift_end_time",
    )

    # Rename slot_duration_minutes / people_per_slot columns in tasks and shift_batches
    op.alter_column(
        "tasks",
        "slot_duration_minutes",
        new_column_name="shift_duration_minutes",
    )
    op.alter_column("tasks", "people_per_slot", new_column_name="people_per_shift")
    op.alter_column(
        "shift_batches",
        "slot_duration_minutes",
        new_column_name="shift_duration_minutes",
    )
    op.alter_column(
        "shift_batches", "people_per_slot", new_column_name="people_per_shift"
    )

    # Rename indices on shifts (formerly duty_slots)
    op.execute("ALTER INDEX ix_duty_slots_category RENAME TO ix_shifts_category")
    op.execute("ALTER INDEX ix_duty_slots_task_id RENAME TO ix_shifts_task_id")
    op.execute("ALTER INDEX ix_duty_slots_id RENAME TO ix_shifts_id")
    op.execute("ALTER INDEX ix_duty_slots_title RENAME TO ix_shifts_title")
    op.execute("ALTER INDEX ix_duty_slots_batch_id RENAME TO ix_shifts_batch_id")
    op.execute(
        "ALTER INDEX ix_duty_slots_task_id_date RENAME TO ix_shifts_task_id_date"
    )

    # Rename indices on shift_batches
    op.execute("ALTER INDEX ix_slot_batches_task_id RENAME TO ix_shift_batches_task_id")
    op.execute("ALTER INDEX ix_slot_batches_id RENAME TO ix_shift_batches_id")

    # Rename bookings indices
    op.execute(
        "ALTER INDEX ix_bookings_duty_slot_id RENAME TO ix_bookings_shift_id"
    )
    op.execute(
        "ALTER INDEX ix_bookings_duty_slot_id_status RENAME TO ix_bookings_shift_id_status"
    )

    # Rename FK + PK + unique constraints
    op.execute(
        "ALTER TABLE shifts RENAME CONSTRAINT duty_slots_task_id_fkey TO shifts_task_id_fkey"
    )
    op.execute(
        "ALTER TABLE shifts RENAME CONSTRAINT duty_slots_batch_id_fkey TO shifts_batch_id_fkey"
    )
    op.execute("ALTER TABLE shifts RENAME CONSTRAINT duty_slots_pkey TO shifts_pkey")

    op.execute(
        "ALTER TABLE shift_batches RENAME CONSTRAINT slot_batches_task_id_fkey TO shift_batches_task_id_fkey"
    )
    op.execute(
        "ALTER TABLE shift_batches RENAME CONSTRAINT slot_batches_pkey TO shift_batches_pkey"
    )

    op.execute(
        "ALTER TABLE bookings RENAME CONSTRAINT bookings_duty_slot_id_fkey TO bookings_shift_id_fkey"
    )
    op.execute(
        "ALTER TABLE bookings RENAME CONSTRAINT uq_booking_slot_user TO uq_booking_shift_user"
    )

    # Rename the legacy booking_reminders FK to shifts
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'booking_reminders_duty_slot_id_fkey') THEN
                EXECUTE 'ALTER TABLE booking_reminders RENAME CONSTRAINT booking_reminders_duty_slot_id_fkey TO booking_reminders_shift_id_fkey';
            END IF;
        END$$;
        """
    )

    # Data migration: notification type codes + categories + scope_type (merge-aware).
    op.execute(
        "UPDATE notification_subscriptions SET scope_type = 'shift' WHERE scope_type = 'duty_slot'"
    )
    # Inline merge-aware rename for each (old_code, new_code) pair.
    for old_code, new_code, category, name, description in [
        (
            "slot.starting_soon_unfilled",
            "shift.starting_soon_unfilled",
            "shift",
            "Shift Starting Soon (Unfilled)",
            "Alert when a shift starts in 30 minutes but still has open spots",
        ),
        (
            "slot.time_changed",
            "shift.time_changed",
            "shift",
            "Shift Time Changed",
            "Notification when a shift you booked has its time changed",
        ),
        (
            "booking.slot_cobooked",
            "booking.shift_cobooked",
            "booking",
            "Shift Co-booked",
            "Notification when someone else also books a shift you are on",
        ),
    ]:
        op.execute(
            f"""
            DO $$
            DECLARE
                old_id UUID;
                new_id UUID;
            BEGIN
                SELECT id INTO old_id FROM notification_types WHERE code = '{old_code}';
                SELECT id INTO new_id FROM notification_types WHERE code = '{new_code}';

                IF old_id IS NOT NULL AND new_id IS NOT NULL THEN
                    UPDATE notification_subscriptions ns
                    SET notification_type_id = new_id
                    WHERE ns.notification_type_id = old_id
                      AND NOT EXISTS (
                          SELECT 1 FROM notification_subscriptions s2
                          WHERE s2.user_id = ns.user_id
                            AND s2.notification_type_id = new_id
                            AND s2.scope_type = ns.scope_type
                            AND s2.scope_id IS NOT DISTINCT FROM ns.scope_id
                      );
                    DELETE FROM notification_subscriptions WHERE notification_type_id = old_id;
                    DELETE FROM notification_types WHERE id = old_id;
                    UPDATE notification_types
                    SET category = '{category}', name = '{name}', description = '{description}'
                    WHERE id = new_id;
                ELSIF old_id IS NOT NULL THEN
                    UPDATE notification_types
                    SET code = '{new_code}', category = '{category}', name = '{name}', description = '{description}'
                    WHERE id = old_id;
                END IF;
            END$$;
            """
        )
    op.execute(
        "UPDATE notification_types SET category = 'shift' WHERE category = 'slot'"
    )


def downgrade():
    op.execute(
        "UPDATE notification_types SET name = 'Slot Co-booked' WHERE code = 'booking.shift_cobooked'"
    )
    op.execute(
        "UPDATE notification_types SET name = 'Slot Time Changed' WHERE code = 'shift.time_changed'"
    )
    op.execute(
        "UPDATE notification_types SET name = 'Slot Starting Soon (Unfilled)' WHERE code = 'shift.starting_soon_unfilled'"
    )
    op.execute(
        "UPDATE notification_types SET category = 'slot' WHERE category = 'shift'"
    )
    op.execute(
        "UPDATE notification_types SET code = 'booking.slot_cobooked' WHERE code = 'booking.shift_cobooked'"
    )
    op.execute(
        "UPDATE notification_types SET code = 'slot.time_changed' WHERE code = 'shift.time_changed'"
    )
    op.execute(
        "UPDATE notification_types SET code = 'slot.starting_soon_unfilled' WHERE code = 'shift.starting_soon_unfilled'"
    )
    op.execute(
        "UPDATE notification_subscriptions SET scope_type = 'duty_slot' WHERE scope_type = 'shift'"
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'booking_reminders_shift_id_fkey') THEN
                EXECUTE 'ALTER TABLE booking_reminders RENAME CONSTRAINT booking_reminders_shift_id_fkey TO booking_reminders_duty_slot_id_fkey';
            END IF;
        END$$;
        """
    )

    op.execute(
        "ALTER TABLE bookings RENAME CONSTRAINT uq_booking_shift_user TO uq_booking_slot_user"
    )
    op.execute(
        "ALTER TABLE bookings RENAME CONSTRAINT bookings_shift_id_fkey TO bookings_duty_slot_id_fkey"
    )
    op.execute(
        "ALTER TABLE shift_batches RENAME CONSTRAINT shift_batches_pkey TO slot_batches_pkey"
    )
    op.execute(
        "ALTER TABLE shift_batches RENAME CONSTRAINT shift_batches_task_id_fkey TO slot_batches_task_id_fkey"
    )
    op.execute("ALTER TABLE shifts RENAME CONSTRAINT shifts_pkey TO duty_slots_pkey")
    op.execute(
        "ALTER TABLE shifts RENAME CONSTRAINT shifts_batch_id_fkey TO duty_slots_batch_id_fkey"
    )
    op.execute(
        "ALTER TABLE shifts RENAME CONSTRAINT shifts_task_id_fkey TO duty_slots_task_id_fkey"
    )

    op.execute(
        "ALTER INDEX ix_bookings_shift_id_status RENAME TO ix_bookings_duty_slot_id_status"
    )
    op.execute(
        "ALTER INDEX ix_bookings_shift_id RENAME TO ix_bookings_duty_slot_id"
    )
    op.execute("ALTER INDEX ix_shift_batches_id RENAME TO ix_slot_batches_id")
    op.execute(
        "ALTER INDEX ix_shift_batches_task_id RENAME TO ix_slot_batches_task_id"
    )
    op.execute(
        "ALTER INDEX ix_shifts_task_id_date RENAME TO ix_duty_slots_task_id_date"
    )
    op.execute("ALTER INDEX ix_shifts_batch_id RENAME TO ix_duty_slots_batch_id")
    op.execute("ALTER INDEX ix_shifts_title RENAME TO ix_duty_slots_title")
    op.execute("ALTER INDEX ix_shifts_id RENAME TO ix_duty_slots_id")
    op.execute("ALTER INDEX ix_shifts_task_id RENAME TO ix_duty_slots_task_id")
    op.execute("ALTER INDEX ix_shifts_category RENAME TO ix_duty_slots_category")

    op.alter_column(
        "shift_batches", "people_per_shift", new_column_name="people_per_slot"
    )
    op.alter_column(
        "shift_batches",
        "shift_duration_minutes",
        new_column_name="slot_duration_minutes",
    )
    op.alter_column("tasks", "people_per_shift", new_column_name="people_per_slot")
    op.alter_column(
        "tasks", "shift_duration_minutes", new_column_name="slot_duration_minutes"
    )

    op.alter_column(
        "bookings",
        "cancelled_shift_end_time",
        new_column_name="cancelled_slot_end_time",
    )
    op.alter_column(
        "bookings",
        "cancelled_shift_start_time",
        new_column_name="cancelled_slot_start_time",
    )
    op.alter_column(
        "bookings", "cancelled_shift_date", new_column_name="cancelled_slot_date"
    )
    op.alter_column(
        "bookings", "cancelled_shift_title", new_column_name="cancelled_slot_title"
    )

    op.alter_column(
        "booking_reminders", "shift_id", new_column_name="duty_slot_id"
    )
    op.alter_column("bookings", "shift_id", new_column_name="duty_slot_id")

    op.rename_table("shift_batches", "slot_batches")
    op.rename_table("shifts", "duty_slots")
