"""Self-service events: memberships, invitations, join requests, visibility

Turns each event into its own tenancy. The flat ``event_managers`` table
becomes ``event_memberships`` with a role, events gain a public/private
setting plus a superadmin-curated ``is_featured`` flag, and two new tables
carry invitations and join requests.

Backfill is written to preserve every existing user's access:

* current managers become ``admin``; each event's ``created_by_id`` becomes
  ``owner`` (falling back to the first manager, then to a superadmin, so no
  event is left ownerless);
* anyone who ever booked a shift or submitted availability in an event
  becomes a ``member`` there — before this change any active account could
  see every published event, so without this they would silently lose access;
* existing events are marked ``public`` and, if published, ``is_featured``,
  so the home screen looks the same the moment this lands;
* the retired global ``task_manager`` role is converted into an ``admin``
  membership on every event, because that is what it granted in practice.

Revision ID: 20260821_0001
Revises: 20260803_0001
Create Date: 2026-08-21 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "20260821_0001"
down_revision = "20260803_0001"
branch_labels = None
depends_on = None


def upgrade():
    # ── events: visibility + curation ──────────────────────────────
    op.add_column(
        "events",
        sa.Column(
            "visibility",
            sa.String(16),
            nullable=False,
            server_default="private",
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "is_featured",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index("ix_events_visibility", "events", ["visibility"])
    op.create_index("ix_events_is_featured", "events", ["is_featured"])

    # Everything that exists today was visible to every signed-in user, so
    # keep it that way rather than hiding it behind the new private default.
    op.execute("UPDATE events SET visibility = 'public'")
    op.execute("UPDATE events SET is_featured = true WHERE status = 'published'")

    # ── event_managers -> event_memberships ────────────────────────
    op.rename_table("event_managers", "event_memberships")
    op.add_column(
        "event_memberships",
        sa.Column("role", sa.String(16), nullable=False, server_default="member"),
    )
    op.create_index("ix_event_memberships_role", "event_memberships", ["role"])

    op.execute(
        "ALTER INDEX ix_event_managers_event_id "
        "RENAME TO ix_event_memberships_event_id"
    )
    op.execute(
        "ALTER INDEX ix_event_managers_user_id "
        "RENAME TO ix_event_memberships_user_id"
    )
    op.execute("ALTER INDEX ix_event_managers_id RENAME TO ix_event_memberships_id")
    op.execute(
        "ALTER TABLE event_memberships RENAME CONSTRAINT "
        "event_managers_pkey TO event_memberships_pkey"
    )
    op.execute(
        "ALTER TABLE event_memberships RENAME CONSTRAINT "
        "uq_event_manager TO uq_event_membership"
    )
    op.execute(
        "ALTER TABLE event_memberships RENAME CONSTRAINT "
        "event_managers_event_id_fkey TO event_memberships_event_id_fkey"
    )
    op.execute(
        "ALTER TABLE event_memberships RENAME CONSTRAINT "
        "event_managers_user_id_fkey TO event_memberships_user_id_fkey"
    )

    # Everyone already in the table was a manager.
    op.execute("UPDATE event_memberships SET role = 'admin'")

    # ── new tables ─────────────────────────────────────────────────
    op.create_table(
        "event_invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("role", sa.String(16), nullable=False, server_default="member"),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("invited_by_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("accepted_by_id", sa.Uuid(), nullable=True),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        # CASCADE, not SET NULL: a SET NULL on the inviter fires in the same
        # statement that cascades away the events they own, and its row-level
        # re-check of event_id then fails against an already-deleted event.
        sa.ForeignKeyConstraint(["invited_by_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["accepted_by_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_invitations_id", "event_invitations", ["id"])
    op.create_index("ix_event_invitations_event_id", "event_invitations", ["event_id"])
    op.create_index("ix_event_invitations_email", "event_invitations", ["email"])
    op.create_index(
        "ix_event_invitations_token", "event_invitations", ["token"], unique=True
    )
    op.create_index(
        "ix_event_invitations_invited_by_id", "event_invitations", ["invited_by_id"]
    )
    op.create_index(
        "ix_event_invitations_event_email", "event_invitations", ["event_id", "email"]
    )

    op.create_table(
        "event_join_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("decided_by_id", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decided_by_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "event_id", name="uq_event_join_request"),
    )
    op.create_index("ix_event_join_requests_id", "event_join_requests", ["id"])
    op.create_index("ix_event_join_requests_user_id", "event_join_requests", ["user_id"])
    op.create_index(
        "ix_event_join_requests_event_id", "event_join_requests", ["event_id"]
    )
    op.create_index("ix_event_join_requests_status", "event_join_requests", ["status"])

    # ── backfill memberships ───────────────────────────────────────

    # 1. Global task_managers held, in effect, admin over every event.
    op.execute(
        """
        INSERT INTO event_memberships (id, created_at, updated_at, user_id, event_id, role)
        SELECT gen_random_uuid(), now(), now(), u.id, e.id, 'admin'
        FROM users u
        CROSS JOIN events e
        WHERE u.roles @> '["task_manager"]'::jsonb
        ON CONFLICT ON CONSTRAINT uq_event_membership DO NOTHING
        """
    )

    # 2. Anyone with a booking in an event was implicitly participating.
    op.execute(
        """
        INSERT INTO event_memberships (id, created_at, updated_at, user_id, event_id, role)
        SELECT DISTINCT gen_random_uuid(), now(), now(), b.user_id, t.event_id, 'member'
        FROM bookings b
        JOIN shifts s ON s.id = b.shift_id
        JOIN tasks t ON t.id = s.task_id
        WHERE t.event_id IS NOT NULL
        ON CONFLICT ON CONSTRAINT uq_event_membership DO NOTHING
        """
    )

    # 3. Same for anyone who submitted availability.
    op.execute(
        """
        INSERT INTO event_memberships (id, created_at, updated_at, user_id, event_id, role)
        SELECT DISTINCT gen_random_uuid(), now(), now(), a.user_id, a.event_id, 'member'
        FROM user_availabilities a
        WHERE a.event_id IS NOT NULL
        ON CONFLICT ON CONSTRAINT uq_event_membership DO NOTHING
        """
    )

    # 4. The recorded creator becomes owner, upgrading any weaker row.
    op.execute(
        """
        INSERT INTO event_memberships (id, created_at, updated_at, user_id, event_id, role)
        SELECT gen_random_uuid(), now(), now(), e.created_by_id, e.id, 'owner'
        FROM events e
        WHERE e.created_by_id IS NOT NULL
        ON CONFLICT ON CONSTRAINT uq_event_membership
        DO UPDATE SET role = 'owner'
        """
    )

    # 5. Events with no creator on record: promote an existing admin.
    op.execute(
        """
        UPDATE event_memberships m
        SET role = 'owner'
        WHERE m.id IN (
            SELECT DISTINCT ON (em.event_id) em.id
            FROM event_memberships em
            WHERE em.event_id NOT IN (
                SELECT event_id FROM event_memberships WHERE role = 'owner'
            )
            ORDER BY em.event_id, em.created_at
        )
        """
    )

    # 6. Anything still ownerless goes to a superadmin, so every event has
    #    someone who can administer it after the cutover.
    op.execute(
        """
        INSERT INTO event_memberships (id, created_at, updated_at, user_id, event_id, role)
        SELECT gen_random_uuid(), now(), now(), u.id, e.id, 'owner'
        FROM events e
        CROSS JOIN LATERAL (
            SELECT id FROM users
            WHERE roles @> '["admin"]'::jsonb
            ORDER BY created_at
            LIMIT 1
        ) u
        WHERE e.id NOT IN (SELECT event_id FROM event_memberships WHERE role = 'owner')
        ON CONFLICT ON CONSTRAINT uq_event_membership
        DO UPDATE SET role = 'owner'
        """
    )

    # 7. Keep created_by_id consistent with whoever ended up owning it.
    op.execute(
        """
        UPDATE events e
        SET created_by_id = m.user_id
        FROM event_memberships m
        WHERE m.event_id = e.id
          AND m.role = 'owner'
          AND e.created_by_id IS DISTINCT FROM m.user_id
        """
    )

    # ── open signup ────────────────────────────────────────────────
    # Nobody is left sitting in the retired approval queue. Accounts that were
    # explicitly rejected stay inactive — that was a moderation decision, not
    # a pending one.
    op.execute(
        "UPDATE users SET is_active = true "
        "WHERE is_active = false AND rejection_reason IS NULL"
    )

    # The global task_manager role is retired; its grants now live in
    # event_memberships (step 1 above).
    op.execute(
        "UPDATE users SET roles = roles - 'task_manager' "
        "WHERE roles @> '[\"task_manager\"]'::jsonb"
    )

    # The site_settings singleton only ever held the approval password — a
    # workaround for the approval queue this migration removes.
    op.drop_index("ix_site_settings_id", table_name="site_settings")
    op.drop_table("site_settings")

    op.alter_column("events", "visibility", server_default=None)
    op.alter_column("event_memberships", "role", server_default=None)


def downgrade():
    op.create_table(
        "site_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("approval_password", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_site_settings_id", "site_settings", ["id"], unique=False)

    op.drop_index("ix_event_join_requests_status", table_name="event_join_requests")
    op.drop_index("ix_event_join_requests_event_id", table_name="event_join_requests")
    op.drop_index("ix_event_join_requests_user_id", table_name="event_join_requests")
    op.drop_index("ix_event_join_requests_id", table_name="event_join_requests")
    op.drop_table("event_join_requests")

    op.drop_index("ix_event_invitations_event_email", table_name="event_invitations")
    op.drop_index("ix_event_invitations_invited_by_id", table_name="event_invitations")
    op.drop_index("ix_event_invitations_token", table_name="event_invitations")
    op.drop_index("ix_event_invitations_email", table_name="event_invitations")
    op.drop_index("ix_event_invitations_event_id", table_name="event_invitations")
    op.drop_index("ix_event_invitations_id", table_name="event_invitations")
    op.drop_table("event_invitations")

    # Only managers existed before; plain members were implicit.
    op.execute("DELETE FROM event_memberships WHERE role = 'member'")
    op.drop_index("ix_event_memberships_role", table_name="event_memberships")
    op.drop_column("event_memberships", "role")

    op.execute(
        "ALTER TABLE event_memberships RENAME CONSTRAINT "
        "event_memberships_user_id_fkey TO event_managers_user_id_fkey"
    )
    op.execute(
        "ALTER TABLE event_memberships RENAME CONSTRAINT "
        "event_memberships_event_id_fkey TO event_managers_event_id_fkey"
    )
    op.execute(
        "ALTER TABLE event_memberships RENAME CONSTRAINT "
        "uq_event_membership TO uq_event_manager"
    )
    op.execute(
        "ALTER TABLE event_memberships RENAME CONSTRAINT "
        "event_memberships_pkey TO event_managers_pkey"
    )
    op.execute("ALTER INDEX ix_event_memberships_id RENAME TO ix_event_managers_id")
    op.execute(
        "ALTER INDEX ix_event_memberships_user_id "
        "RENAME TO ix_event_managers_user_id"
    )
    op.execute(
        "ALTER INDEX ix_event_memberships_event_id "
        "RENAME TO ix_event_managers_event_id"
    )
    op.rename_table("event_memberships", "event_managers")

    op.drop_index("ix_events_is_featured", table_name="events")
    op.drop_index("ix_events_visibility", table_name="events")
    op.drop_column("events", "is_featured")
    op.drop_column("events", "visibility")
