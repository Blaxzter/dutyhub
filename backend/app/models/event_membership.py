import uuid

import sqlalchemy as sa
from sqlmodel import Field

from app.models.base import Base

# Ordered weakest → strongest. Used by app.logic.permissions to compare roles.
EVENT_ROLES = ("member", "admin", "owner")


class EventMembership(Base, table=True):
    """A user's role within a single event.

    Replaces the former flat ``event_managers`` table. Every event has exactly
    one ``owner`` (its creator, or whoever it was handed to); ``admin`` may
    manage tasks, shifts and members; ``member`` may see the event and book
    shifts in it.
    """

    __tablename__ = "event_memberships"  # type: ignore[assignment]

    __table_args__ = (
        sa.UniqueConstraint("user_id", "event_id", name="uq_event_membership"),
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
    role: str = Field(
        default="member",
        sa_column=sa.Column(
            sa.String(16), nullable=False, server_default="member", index=True
        ),
        description="One of: owner, admin, member",
    )
