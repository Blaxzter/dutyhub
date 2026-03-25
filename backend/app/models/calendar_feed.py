import secrets
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from sqlmodel import Field, Relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User  # noqa: F401


class CalendarFeedToken(Base, table=True):
    """Per-user secret token for iCalendar (.ics) subscription feed."""

    __tablename__ = "calendar_feed_tokens"  # type: ignore[assignment]

    user_id: uuid.UUID = Field(
        sa_column=sa.Column(
            sa.Uuid,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        )
    )
    token: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        sa_column=sa.Column(sa.String, unique=True, nullable=False, index=True),
    )
    is_enabled: bool = Field(default=True)
    last_accessed_at: datetime | None = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime, nullable=True),
    )

    user: Optional["User"] = Relationship()
