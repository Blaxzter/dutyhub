"""Rename event_groups -> events (step 2 of 3 terminology rename)

Revision ID: 20260419_0002
Revises: 20260419_0001
Create Date: 2026-04-19

Step 2 of 3-part rename: the old "EventGroup" (time-bounded container)
becomes "Event". EventGroupManager becomes EventManager.

Also cleans up index/constraint names on the tasks table that retained
the old "events_*" naming because PG rename_table doesn't cascade to
associated object names.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260419_0002"
down_revision = "20260419_0001"
branch_labels = None
depends_on = None


def upgrade():
    # Rename tables
    op.rename_table("event_groups", "events")
    op.rename_table("event_group_managers", "event_managers")

    # Rename FK columns (event_groups.id is now events.id)
    op.alter_column("tasks", "event_group_id", new_column_name="event_id")
    op.alter_column("event_managers", "event_group_id", new_column_name="event_id")
    op.alter_column("user_availabilities", "event_group_id", new_column_name="event_id")

    # Rename indices. Note: step 1 renamed the events table to tasks but
    # didn't rename the associated indices — they still start with "ix_events_".
    op.execute(
        "ALTER INDEX ix_events_event_group_id RENAME TO ix_tasks_event_id"
    )
    op.execute(
        "ALTER INDEX ix_event_group_managers_event_group_id RENAME TO ix_event_managers_event_id"
    )
    op.execute(
        "ALTER INDEX ix_event_group_managers_user_id RENAME TO ix_event_managers_user_id"
    )
    op.execute(
        "ALTER INDEX ix_event_group_managers_id RENAME TO ix_event_managers_id"
    )
    op.execute(
        "ALTER INDEX ix_user_availabilities_event_group_id RENAME TO ix_user_availabilities_event_id"
    )

    # Rename FK constraints. tasks.event_id FK was created with the old
    # table name — it's still named "events_event_group_id_fkey".
    op.execute(
        "ALTER TABLE tasks RENAME CONSTRAINT events_event_group_id_fkey TO tasks_event_id_fkey"
    )
    op.execute(
        "ALTER TABLE event_managers RENAME CONSTRAINT event_group_managers_event_group_id_fkey TO event_managers_event_id_fkey"
    )
    op.execute(
        "ALTER TABLE event_managers RENAME CONSTRAINT event_group_managers_user_id_fkey TO event_managers_user_id_fkey"
    )
    op.execute(
        "ALTER TABLE user_availabilities RENAME CONSTRAINT user_availabilities_event_group_id_fkey TO user_availabilities_event_id_fkey"
    )

    # Rename PKs and unique constraint
    op.execute("ALTER TABLE events RENAME CONSTRAINT event_groups_pkey TO events_pkey")
    op.execute(
        "ALTER TABLE event_managers RENAME CONSTRAINT event_group_managers_pkey TO event_managers_pkey"
    )
    op.execute(
        "ALTER TABLE event_managers RENAME CONSTRAINT uq_event_group_manager TO uq_event_manager"
    )

    # Data migration: scope_type + notification type codes (merge-aware — see step 1).
    op.execute(
        "UPDATE notification_subscriptions SET scope_type = 'event' WHERE scope_type = 'event_group'"
    )
    op.execute(
        """
        DO $$
        DECLARE
            old_id UUID;
            new_id UUID;
        BEGIN
            SELECT id INTO old_id FROM notification_types WHERE code = 'event_group.published';
            SELECT id INTO new_id FROM notification_types WHERE code = 'event.published';

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
                SET category = 'event',
                    name = 'Event Published',
                    description = 'Notification when a new event is published'
                WHERE id = new_id;
            ELSIF old_id IS NOT NULL THEN
                UPDATE notification_types
                SET code = 'event.published',
                    category = 'event',
                    name = 'Event Published',
                    description = 'Notification when a new event is published'
                WHERE id = old_id;
            END IF;
        END$$;
        """
    )
    op.execute(
        "UPDATE notification_types SET category = 'event' WHERE category = 'event_group'"
    )


def downgrade():
    op.execute(
        "UPDATE notification_types SET description = 'Notification when a new event group is published' WHERE code = 'event.published'"
    )
    op.execute(
        "UPDATE notification_types SET name = 'Event Group Published' WHERE code = 'event.published'"
    )
    op.execute(
        "UPDATE notification_types SET category = 'event_group' WHERE category = 'event'"
    )
    op.execute(
        "UPDATE notification_types SET code = 'event_group.published' WHERE code = 'event.published'"
    )
    op.execute(
        "UPDATE notification_subscriptions SET scope_type = 'event_group' WHERE scope_type = 'event'"
    )

    op.execute(
        "ALTER TABLE event_managers RENAME CONSTRAINT uq_event_manager TO uq_event_group_manager"
    )
    op.execute(
        "ALTER TABLE event_managers RENAME CONSTRAINT event_managers_pkey TO event_group_managers_pkey"
    )
    op.execute("ALTER TABLE events RENAME CONSTRAINT events_pkey TO event_groups_pkey")

    op.execute(
        "ALTER TABLE user_availabilities RENAME CONSTRAINT user_availabilities_event_id_fkey TO user_availabilities_event_group_id_fkey"
    )
    op.execute(
        "ALTER TABLE event_managers RENAME CONSTRAINT event_managers_user_id_fkey TO event_group_managers_user_id_fkey"
    )
    op.execute(
        "ALTER TABLE event_managers RENAME CONSTRAINT event_managers_event_id_fkey TO event_group_managers_event_group_id_fkey"
    )
    op.execute(
        "ALTER TABLE tasks RENAME CONSTRAINT tasks_event_id_fkey TO events_event_group_id_fkey"
    )

    op.execute(
        "ALTER INDEX ix_user_availabilities_event_id RENAME TO ix_user_availabilities_event_group_id"
    )
    op.execute(
        "ALTER INDEX ix_event_managers_id RENAME TO ix_event_group_managers_id"
    )
    op.execute(
        "ALTER INDEX ix_event_managers_user_id RENAME TO ix_event_group_managers_user_id"
    )
    op.execute(
        "ALTER INDEX ix_event_managers_event_id RENAME TO ix_event_group_managers_event_group_id"
    )
    op.execute(
        "ALTER INDEX ix_tasks_event_id RENAME TO ix_events_event_group_id"
    )

    op.alter_column("user_availabilities", "event_id", new_column_name="event_group_id")
    op.alter_column("event_managers", "event_id", new_column_name="event_group_id")
    op.alter_column("tasks", "event_id", new_column_name="event_group_id")

    op.rename_table("event_managers", "event_group_managers")
    op.rename_table("events", "event_groups")
