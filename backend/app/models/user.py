import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from app.models.base import Base


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
    picture: str | None = Field(
        default=None,
        sa_column=sa.Column(sa.String, nullable=True),
        description="URL to user's profile picture",
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

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return "admin" in self.roles
