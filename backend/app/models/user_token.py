import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlmodel import Field

from app.models.base import Base


class UserToken(Base, table=True):
    """A single-use secret that arrived by email: verify this address, or reset
    this password.

    Modelled on ``EventInvitation`` — one row per outstanding token, hashed at
    rest, explicitly expired and explicitly consumed. A table rather than a
    pair of columns on ``users`` for three reasons: it keeps a hot, already
    twenty-column-wide row from growing two more unique indexes; it allows more
    than one token to be outstanding at a time, so a "resend" does not
    invalidate the mail already sitting in someone's inbox; and it leaves an
    audit trail of what was issued and when it was used.

    Only the sha256 of the value in the link is stored, so this table read on
    its own does not let anyone take over an account. Consuming a token stamps
    ``consumed_at`` instead of deleting the row, which is what lets a second
    click on the same link be answered with "already used" rather than the far
    more alarming "invalid token".
    """

    __tablename__ = "user_tokens"  # type: ignore[assignment]

    # CASCADE for the same reason as auth_sessions.user_id — see that model.
    user_id: uuid.UUID = Field(
        sa_column=sa.Column(
            sa.Uuid,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        description="Account the token acts on",
    )
    purpose: str = Field(
        sa_column=sa.Column(sa.String(32), nullable=False),
        description=(
            "What the token authorises: 'verify_email' or 'reset_password'. A "
            "token is only ever accepted by the flow that matches its purpose"
        ),
    )
    token_hash: str = Field(
        sa_column=sa.Column(sa.String(64), nullable=False, unique=True, index=True),
        description="sha256 hexdigest (64 chars) of the secret carried in the link",
    )
    expires_at: datetime = Field(
        sa_column=sa.Column(sa.DateTime, nullable=False),
        description="When the token stops being accepted (naive UTC)",
    )
    consumed_at: datetime | None = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime, nullable=True),
        description="When the token was redeemed; NULL while outstanding (naive UTC)",
    )
