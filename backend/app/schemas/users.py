import uuid
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field

TimeFormat = Literal["locale", "h12", "h24"]
Theme = Literal["default", "classic"]


class ProfileInit(BaseModel):
    """Profile data from Auth0 ID token for user initialization."""

    email: EmailStr | None = None
    name: str | None = None
    nickname: str | None = None
    picture: str | None = None
    email_verified: bool | None = None
    preferred_language: str | None = None


class UserProfileUpdate(BaseModel):
    name: str | None = Field(None, max_length=100, description="User's display name")
    nickname: str | None = Field(None, max_length=50, description="User's nickname")
    bio: str | None = Field(None, max_length=500, description="User's biography")
    phone_number: str | None = Field(
        None, max_length=30, description="User's phone number"
    )
    preferred_language: str | None = Field(
        None, pattern="^(en|de)$", description="Preferred language for notifications"
    )
    time_format: TimeFormat | None = Field(
        None, description="Display preference for times"
    )
    theme: Theme | None = Field(None, description="Selected color palette")


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    sub: str = Field(validation_alias=AliasChoices("sub", "auth0_sub"))
    name: str | None = None
    nickname: str | None = None
    email: str | None = None
    avatar_etag: str | None = None
    bio: str | None = None
    phone_number: str | None = None
    preferred_language: str = "en"
    time_format: TimeFormat = "locale"
    theme: Theme = "default"
    email_verified: bool = False
    roles: list[str] = Field(default_factory=list, description="User's roles")
    is_admin: bool = Field(default=False, description="Whether user has admin role")
    is_task_manager: bool = Field(
        default=False, description="Whether user has task_manager role"
    )
    is_active: bool = Field(default=True, description="Whether user is active")
    rejection_reason: str | None = Field(
        default=None, description="Reason for account rejection"
    )
    managed_event_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="IDs of events this user manages (via event_managers)",
    )
    selected_event_id: uuid.UUID | None = Field(
        default=None,
        description="Event currently selected as the user's dashboard scope",
    )


class SelectedEventUpdate(BaseModel):
    """Request body for PUT /users/me/selected-event."""

    selected_event_id: uuid.UUID | None = None
