import uuid

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from app.logic.utils.pydantic_jsonb import PydanticJSONB
from app.models.base import Base
from app.schemas.booking_reminder import ReminderOffsetEntry


class User(Base, table=True):
    """Database model for application users."""

    __tablename__ = "users"  # type: ignore[assignment]

    auth0_sub: str = Field(
        sa_column=sa.Column(sa.String, unique=True, index=True),
        description="Auth0 subject identifier",
    )
    email: str | None = Field(
        default=None,
        sa_column=sa.Column(sa.String, index=True),
        description="User's email address",
    )
    name: str | None = Field(default=None, description="User's display name")
    avatar_etag: str | None = Field(
        default=None,
        sa_column=sa.Column(sa.String(64), nullable=True),
        description="sha256 of the locally stored avatar; null when no avatar is set",
    )
    email_verified: bool = Field(
        default=False,
        description="Whether the user's email is verified",
    )

    roles: list[str] = Field(
        default_factory=list,
        sa_column=sa.Column(JSONB, nullable=False, server_default="[]"),
        description="List of role identifiers",
    )
    is_active: bool = Field(default=True, description="Whether the user is active")
    rejection_reason: str | None = Field(
        default=None,
        sa_column=sa.Column(sa.String, nullable=True),
        description="Reason for account rejection",
    )

    phone_number: str | None = Field(
        default=None,
        sa_column=sa.Column(sa.String, nullable=True),
        description="User's phone number for contact purposes",
    )

    preferred_language: str = Field(
        default="en",
        sa_column=sa.Column(sa.String(5), nullable=False, server_default="en"),
        description="User's preferred language for notifications (e.g., 'en', 'de')",
    )

    time_format: str = Field(
        default="locale",
        sa_column=sa.Column(sa.String(10), nullable=False, server_default="locale"),
        description="Display preference for times: 'locale' | 'h12' | 'h24'",
    )

    theme: str = Field(
        default="default",
        sa_column=sa.Column(sa.String(20), nullable=False, server_default="default"),
        description="Selected color palette: 'default' | 'classic'",
    )

    selected_event_id: uuid.UUID | None = Field(
        default=None,
        sa_column=sa.Column(
            sa.Uuid,
            sa.ForeignKey("events.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        description="Event that scopes this user's dashboard experience",
    )

    # Global notification channel kill switches
    notify_email: bool = Field(
        default=True,
        description="Global toggle: allow email notifications",
    )
    notify_push: bool = Field(
        default=True,
        description="Global toggle: allow push notifications",
    )
    notify_telegram: bool = Field(
        default=True,
        description="Global toggle: allow Telegram notifications",
    )

    # Default reminder offsets applied when creating new bookings
    default_reminder_offsets: list[ReminderOffsetEntry] = Field(
        default_factory=lambda: [
            ReminderOffsetEntry(offset_minutes=15, channels=["push"]),
            ReminderOffsetEntry(offset_minutes=1440, channels=["email"]),
        ],
        sa_column=sa.Column(
            PydanticJSONB(ReminderOffsetEntry, is_list=True),
            nullable=False,
            server_default="[]",
        ),
        description="Default reminders, e.g. [{offset_minutes: 60, channels: ['push']}]",
    )

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return "admin" in self.roles

    @property
    def is_task_manager(self) -> bool:
        """Check if user has task_manager role."""
        return "task_manager" in self.roles

    @property
    def is_manager(self) -> bool:
        """Check if user has admin or task_manager role."""
        return self.is_admin or self.is_task_manager
