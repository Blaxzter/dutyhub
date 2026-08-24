"""Sandbox demos: throwaway events, throwaway guests, a deadline on both

Backs the "check out a test event" button. A visitor who clicks it gets a
guest account and one seeded event, both hard-deleted once the deadline
passes — so the promise this feature makes is that the tables it writes to do
not grow, and these four columns are what makes that promise keepable.

Two of them look redundant and are not:

* ``users.is_sandbox`` alongside the ``sandbox|`` subject prefix. The prefix is
  what the notification channels test, matching the ``demo|`` and ``test|``
  prefixes already in use; the column is what every ``WHERE`` clause filters
  on, because a prefix match cannot use an index.
* ``tasks.is_sandbox`` alongside ``events.is_sandbox``. ``tasks.event_id`` is
  ``ON DELETE SET NULL``, so a task can outlive its event with a NULL
  ``event_id`` — and a NULL matches no ``IN (...)``, which is the shape every
  event-scoped filter in this application has. A task orphaned that way would
  become visible to everyone and manageable by nobody. This flag survives the
  SET NULL and keeps the exclusion in the WHERE clause.

``sandbox_expires_at`` is naive UTC, matching ``Base.created_at`` and every
other timestamp here. It is indexed because the sweep that reclaims expired
demos orders by it on every new sandbox.

The ``false`` server defaults stay in place, matching ``events.is_featured``
above them: they are what lets the ``NOT NULL`` be added to tables that already
have rows, and every model here declares the same default, so the database and
the application agree about what an unspecified value means.

Revision ID: 20260824_0001
Revises: 20260823_0001
Create Date: 2026-08-24 12:52:55.942256

"""

import sqlalchemy as sa
from alembic import op

revision = "20260824_0001"
down_revision = "20260823_0001"
branch_labels = None
depends_on = None


def upgrade():
    # ── events: the demo itself, and its deadline ──────────────────
    op.add_column(
        "events",
        sa.Column(
            "is_sandbox",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "events",
        sa.Column("sandbox_expires_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_events_is_sandbox", "events", ["is_sandbox"])
    op.create_index(
        "ix_events_sandbox_expires_at", "events", ["sandbox_expires_at"]
    )

    # ── tasks: denormalised, to survive the SET NULL ───────────────
    op.add_column(
        "tasks",
        sa.Column(
            "is_sandbox",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index("ix_tasks_is_sandbox", "tasks", ["is_sandbox"])

    # ── users: the guest accounts ──────────────────────────────────
    op.add_column(
        "users",
        sa.Column(
            "is_sandbox",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index("ix_users_is_sandbox", "users", ["is_sandbox"])


def downgrade():
    op.drop_index("ix_users_is_sandbox", table_name="users")
    op.drop_column("users", "is_sandbox")
    op.drop_index("ix_tasks_is_sandbox", table_name="tasks")
    op.drop_column("tasks", "is_sandbox")
    op.drop_index("ix_events_sandbox_expires_at", table_name="events")
    op.drop_index("ix_events_is_sandbox", table_name="events")
    op.drop_column("events", "sandbox_expires_at")
    op.drop_column("events", "is_sandbox")
