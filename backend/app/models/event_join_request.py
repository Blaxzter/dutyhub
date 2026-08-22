import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlmodel import Field

from app.models.base import Base


class EventJoinRequest(Base, table=True):
    """A user asking to be let into a public event.

    Kept separate from ``event_memberships`` on purpose: a pending request must
    never be mistakable for membership by a query that forgets a status filter.
    """

    __tablename__ = "event_join_requests"  # type: ignore[assignment]

    __table_args__ = (
        sa.UniqueConstraint("user_id", "event_id", name="uq_event_join_request"),
    )

    user_id: uuid.UUID = Field(
        sa_column=sa.Column(
            sa.Uuid,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    event_id: uuid.UUID = Field(
        sa_column=sa.Column(
            sa.Uuid,
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    status: str = Field(
        default="pending",
        sa_column=sa.Column(
            sa.String(16), nullable=False, server_default="pending", index=True
        ),
        description="One of: pending, approved, declined",
    )
    message: str | None = Field(
        default=None,
        sa_column=sa.Column(sa.Text, nullable=True),
        description="Optional note from the requester to the event admins",
    )
    # CASCADE rather than SET NULL, for the same reason as on invitations:
    # a SET NULL fired while the user's events are being cascaded away
    # re-checks event_id against a row that is already gone.
    decided_by_id: uuid.UUID | None = Field(
        default=None,
        sa_column=sa.Column(
            sa.Uuid,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    decided_at: datetime | None = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime, nullable=True),
    )
