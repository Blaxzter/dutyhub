import datetime as dt
import uuid
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.shift import Shift
    from app.models.user import User


class BookingReminder(Base, table=True):
    """Scheduled reminder for a booking, dispatched by the background poller."""

    __tablename__ = "booking_reminders"  # type: ignore[assignment]
    __table_args__ = (
        sa.Index(
            "ix_booking_reminders_poll",
            "status",
            "remind_at",
        ),
        sa.UniqueConstraint(
            "booking_id",
            "offset_minutes",
            name="uq_reminder_booking_offset",
        ),
    )

    booking_id: uuid.UUID = Field(
        sa_column=sa.Column(
            sa.Uuid,
            sa.ForeignKey("bookings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    user_id: uuid.UUID = Field(
        sa_column=sa.Column(
            sa.Uuid,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        description="Denormalized for fast per-user queries",
    )
    shift_id: uuid.UUID | None = Field(
        default=None,
        sa_column=sa.Column(
            sa.Uuid,
            sa.ForeignKey("shifts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        description="For joining to shift start times; nullable if shift deleted",
    )

    remind_at: dt.datetime = Field(
        sa_column=sa.Column(sa.DateTime, nullable=False),
        description="When to fire the reminder (UTC). Computed as slot_start - offset.",
    )
    offset_minutes: int = Field(
        sa_column=sa.Column(sa.Integer, nullable=False),
        description="Minutes before shift start (e.g. 15, 60, 1440)",
    )
    status: str = Field(
        default="pending",
        sa_column=sa.Column(sa.String, nullable=False, server_default="pending"),
        description="pending | sent | cancelled | expired",
    )
    channels: list[str] = Field(
        default_factory=lambda: ["push"],
        sa_column=sa.Column(JSONB, nullable=False, server_default='["push"]'),
        description="Channels to deliver this reminder through (email, push, telegram)",
    )

    booking: Optional["Booking"] = Relationship()
    user: Optional["User"] = Relationship()
    shift: Optional["Shift"] = Relationship()
