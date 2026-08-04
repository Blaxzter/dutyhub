"""Align index names with the terminology rename; make avatar user_id index unique

Revision ID: 20260803_0001
Revises: 20260430_0001
Create Date: 2026-08-03 22:24:00.216537

Closes the model/migration drift that `alembic check` reports on `dev`.

Two independent causes:

1. The 3-part terminology rename (20260419_0001..0003) used PG `rename_table`,
   which does not cascade to index names. Step 2 renamed the handful of indexes
   it noticed, but the plain per-column indexes were missed, so:
     - `events`  (was `event_groups`) still carried `ix_event_groups_*`
     - `tasks`   (was `events`)       still carried `ix_events_*`
   Renaming is done here with `ALTER INDEX ... RENAME TO` rather than the
   drop/create pair autogenerate emits — it is a catalog-only operation, so it
   avoids rebuilding each index and never leaves the column unindexed.

   Order matters: `tasks` currently squats on the `ix_events_*` names that
   `events` needs, and index names are unique per schema. Rename `tasks` first
   to free them, then rename `events` into them. The downgrade reverses that.

2. `user_avatars.user_id` is declared `unique=True, index=True`, which SQLAlchemy
   renders as a single UNIQUE index. The original migration instead created a
   separate UNIQUE *constraint* plus a non-unique index. Postgres has no
   `ALTER INDEX ... SET UNIQUE`, so this one genuinely needs drop/create.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260803_0001"
down_revision = "20260430_0001"
branch_labels = None
depends_on = None


# (old_name, new_name) — `tasks` first so the `ix_events_*` names are free by the
# time `events` claims them.
_TASK_INDEX_RENAMES = [
    ("ix_events_created_by_id", "ix_tasks_created_by_id"),
    ("ix_events_end_date", "ix_tasks_end_date"),
    ("ix_events_id", "ix_tasks_id"),
    ("ix_events_name", "ix_tasks_name"),
    ("ix_events_start_date", "ix_tasks_start_date"),
    ("ix_events_status", "ix_tasks_status"),
]

_EVENT_INDEX_RENAMES = [
    ("ix_event_groups_created_by_id", "ix_events_created_by_id"),
    ("ix_event_groups_id", "ix_events_id"),
    ("ix_event_groups_name", "ix_events_name"),
    ("ix_event_groups_status", "ix_events_status"),
]


def _rename_indexes(renames: list[tuple[str, str]]) -> None:
    for old, new in renames:
        op.execute(f"ALTER INDEX {old} RENAME TO {new}")


def upgrade():
    _rename_indexes(_TASK_INDEX_RENAMES)
    _rename_indexes(_EVENT_INDEX_RENAMES)

    # Collapse the redundant UNIQUE constraint + plain index into one UNIQUE index.
    op.drop_constraint("uq_user_avatars_user_id", "user_avatars", type_="unique")
    op.drop_index("ix_user_avatars_user_id", table_name="user_avatars")
    op.create_index(
        "ix_user_avatars_user_id", "user_avatars", ["user_id"], unique=True
    )


def downgrade():
    op.drop_index("ix_user_avatars_user_id", table_name="user_avatars")
    op.create_index(
        "ix_user_avatars_user_id", "user_avatars", ["user_id"], unique=False
    )
    op.create_unique_constraint(
        "uq_user_avatars_user_id", "user_avatars", ["user_id"]
    )

    # Reverse order: free the `ix_events_*` names before `tasks` reclaims them.
    _rename_indexes([(new, old) for old, new in _EVENT_INDEX_RENAMES])
    _rename_indexes([(new, old) for old, new in _TASK_INDEX_RENAMES])
