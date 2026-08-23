"""Local auth: rename users.auth0_sub to subject, add password columns, auth_sessions and user_tokens

Auth0 contributed exactly one thing to this schema — a validated subject
string — so this migration replaces an *issuer*, not the authorisation model.
Event memberships, roles and every permission check are untouched.

Four things happen to ``users``:

* ``auth0_sub`` becomes ``subject``. Leaving a departed provider's name on the
  column is how its idioms get copied into new code months later. The rename is
  catalog-only — ``ALTER TABLE ... RENAME COLUMN`` plus ``ALTER INDEX ... RENAME
  TO`` — so the unique index is never rebuilt and the column is never left
  unindexed, not even briefly inside this transaction.
* ``password_hash`` arrives nullable. Every row that exists today was
  provisioned by Auth0 and has no password, and demo/test accounts never will;
  a NOT NULL column would have nothing honest to put in them.
* ``nickname`` and ``bio`` become real columns. They were Auth0-only profile
  fields that ``PATCH /users/me`` faked back into its own response; with Auth0
  gone they would be writes into nothing.
* email becomes the login credential, so it finally gains a unique index. It
  stays nullable, so the index is partial, and it is built on ``lower(email)``
  because no one types their address the same way twice and a login form must
  not care.

That last step is the only one that can fail on real data: ``users.email`` has
never been unique. Rather than pick a winner and mangle the rest, the migration
refuses to run and names the addresses involved so a human can decide which
account is real. It runs first, before anything has been altered, and an empty
or already-clean database passes it trivially.

Both new tables cascade from ``users``. ``SET NULL`` on a user foreign key is
forbidden in this schema: deleting a user cascades to the events they own, and
Postgres applies the cascade and the SET NULL in the same statement, so the SET
NULL's row-level re-check runs against an already-deleted event and raises a
foreign-key violation nowhere near its cause.

Revision ID: 20260823_0001
Revises: 20260821_0001
Create Date: 2026-08-23 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "20260823_0001"
down_revision = "20260821_0001"
branch_labels = None
depends_on = None


def _reject_duplicate_emails() -> None:
    """Abort before touching anything if two accounts share an address.

    ``crud_user.get_by_email`` ends in ``.first()``, so today a duplicate merely
    means an arbitrary row wins a lookup. Once email is the login credential the
    same duplicate decides *whose account* a password opens, which is not a
    decision a migration gets to make silently — and neither deleting nor
    renaming somebody's account is one it gets to make at all. So this fails
    loudly and names the addresses instead.
    """
    duplicates = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT lower(email) AS address, count(*) AS occurrences "
                "FROM users "
                "WHERE email IS NOT NULL "
                "GROUP BY lower(email) "
                "HAVING count(*) > 1 "
                "ORDER BY lower(email)"
            )
        )
        .all()
    )
    if not duplicates:
        return

    listed = ", ".join(
        f"{row.address} ({row.occurrences} accounts)" for row in duplicates
    )
    raise RuntimeError(
        "Cannot make users.email unique — these addresses are held by more "
        f"than one account: {listed}. Merge or clear the duplicates by hand, "
        "then re-run this migration. Nothing has been changed."
    )


def upgrade():
    # ── guard: email is about to become a credential ───────────────
    _reject_duplicate_emails()

    # ── users: auth0_sub -> subject, catalog only ──────────────────
    op.alter_column("users", "auth0_sub", new_column_name="subject")
    op.execute("ALTER INDEX ix_users_auth0_sub RENAME TO ix_users_subject")

    # ── users: password and the two ex-Auth0 profile fields ────────
    op.add_column("users", sa.Column("password_hash", sa.String(), nullable=True))
    op.add_column("users", sa.Column("nickname", sa.String(50), nullable=True))
    op.add_column("users", sa.Column("bio", sa.Text(), nullable=True))

    # ── users: case-insensitive unique email ───────────────────────
    # Partial, because email stays nullable and a NULL is not a credential.
    op.execute(
        "CREATE UNIQUE INDEX ix_users_email_lower "
        "ON users (lower(email)) WHERE email IS NOT NULL"
    )

    # ── auth_sessions ──────────────────────────────────────────────
    op.create_table(
        "auth_sessions",
        # id / created_at / updated_at come from the Base mixin. Alembic has no
        # idea that mixin exists, so all three are spelled out by hand here, as
        # in every other create_table in this directory.
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        # CASCADE, not SET NULL — see the module docstring.
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_sessions_id", "auth_sessions", ["id"])
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index(
        "ix_auth_sessions_refresh_token_hash",
        "auth_sessions",
        ["refresh_token_hash"],
        unique=True,
    )

    # ── user_tokens ────────────────────────────────────────────────
    op.create_table(
        "user_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_tokens_id", "user_tokens", ["id"])
    op.create_index("ix_user_tokens_user_id", "user_tokens", ["user_id"])
    op.create_index(
        "ix_user_tokens_token_hash", "user_tokens", ["token_hash"], unique=True
    )


def downgrade():
    op.drop_index("ix_user_tokens_token_hash", table_name="user_tokens")
    op.drop_index("ix_user_tokens_user_id", table_name="user_tokens")
    op.drop_index("ix_user_tokens_id", table_name="user_tokens")
    op.drop_table("user_tokens")

    op.drop_index("ix_auth_sessions_refresh_token_hash", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")

    op.drop_index("ix_users_email_lower", table_name="users")

    # Password hashes exist nowhere else, so downgrading really does discard
    # them — that is the honest reverse of adding the column.
    op.drop_column("users", "bio")
    op.drop_column("users", "nickname")
    op.drop_column("users", "password_hash")

    # Reverse of the catalog-only rename; index name first, so the column and
    # its index never disagree at any point in between.
    op.execute("ALTER INDEX ix_users_subject RENAME TO ix_users_auth0_sub")
    op.alter_column("users", "subject", new_column_name="auth0_sub")
