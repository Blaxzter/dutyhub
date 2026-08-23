import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlmodel import Field

from app.models.base import Base


class AuthSession(Base, table=True):
    """One signed-in device, and the server-side half of its refresh token.

    Access tokens are short-lived HS256 JWTs that are never stored anywhere;
    this row is the thing that makes a *long* session revocable, which is the
    one capability a stateless token cannot provide on its own. The client
    holds the opaque refresh token in an httpOnly cookie and only its sha256
    lands here, so read access to this table cannot be replayed as a login.

    The name is ``AuthSession`` and not ``Session`` on purpose: ``session``
    already means ``AsyncSession`` in the signature of every route, CRUD method
    and logic function in this codebase, and a second meaning for the same word
    would shadow the first in exactly the places that matter.

    Rotation revokes this row and inserts a successor that inherits the
    device's ``created_at``, rather than swapping the hash in place. That costs
    a row per refresh and buys the property this design exists for: after
    rotation the spent digest still matches something, and what it matches is a
    dead session. Revocation likewise stamps ``revoked_at`` and keeps the row,
    both so the Security settings list can still show the device and so that
    presenting an already-revoked token is distinguishable from presenting a
    token that never existed — the former is treated as theft and revokes every
    session belonging to that user.
    """

    __tablename__ = "auth_sessions"  # type: ignore[assignment]

    # CASCADE, never SET NULL. Deleting a user cascades to the events they own,
    # and Postgres applies that cascade and any SET NULL on the same user
    # within one statement, so the SET NULL's row-level re-check would run
    # against an already-deleted parent. A session has no meaning without its
    # user in any case.
    user_id: uuid.UUID = Field(
        sa_column=sa.Column(
            sa.Uuid,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        description="Account this session signs in as",
    )
    refresh_token_hash: str = Field(
        sa_column=sa.Column(sa.String(64), nullable=False, unique=True, index=True),
        description="sha256 hexdigest (64 chars) of the opaque refresh token",
    )
    expires_at: datetime = Field(
        sa_column=sa.Column(sa.DateTime, nullable=False),
        description="When the refresh token stops being accepted (naive UTC)",
    )
    revoked_at: datetime | None = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime, nullable=True),
        description=(
            "Set on logout, password change or reuse detection; a revoked "
            "session is kept rather than deleted (naive UTC)"
        ),
    )
    last_used_at: datetime | None = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime, nullable=True),
        description="Last successful refresh through this session (naive UTC)",
    )
    user_agent: str | None = Field(
        default=None,
        sa_column=sa.Column(sa.String(255), nullable=True),
        description="User-Agent at sign-in, so the owner can recognise the device",
    )
    ip_address: str | None = Field(
        default=None,
        sa_column=sa.Column(sa.String(45), nullable=True),
        description=(
            "Client address at sign-in; 45 characters is the longest an "
            "IPv4-mapped IPv6 literal can be"
        ),
    )
