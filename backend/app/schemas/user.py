import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    auth0_sub: str = Field(..., description="Auth0 subject identifier")
    email: EmailStr | None = Field(default=None, description="User's email address")
    name: str | None = Field(default=None, description="User's display name")
    email_verified: bool = Field(
        default=False, description="Whether the user's email is verified"
    )
    roles: list[str] = Field(
        default_factory=list, description="List of role identifiers"
    )
    is_active: bool = Field(default=True, description="Whether the user is active")
    preferred_language: str = Field(default="en", description="Preferred language")
    time_format: str = Field(
        default="locale", description="Display preference for times"
    )


class UserUpdate(BaseModel):
    email: EmailStr | None = Field(default=None, description="User's email address")
    name: str | None = Field(default=None, description="User's display name")
    roles: list[str] | None = Field(
        default=None, description="List of role identifiers"
    )
    is_active: bool | None = Field(
        default=None, description="Whether the user is active"
    )
    rejection_reason: str | None = Field(
        default=None, description="Reason for account rejection"
    )
    preferred_language: str | None = Field(
        default=None, description="Preferred language"
    )
    time_format: str | None = Field(
        default=None, description="Display preference for times"
    )


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    auth0_sub: str
    email: EmailStr | None = None
    name: str | None = None
    avatar_etag: str | None = None
    phone_number: str | None = None
    preferred_language: str = "en"
    time_format: str = "locale"
    roles: list[str]
    is_active: bool
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class UserCounts(BaseModel):
    all: int
    active: int
    pending: int
    rejected: int


class UserListResponse(BaseModel):
    items: list[UserRead]
    skip: int
    limit: int
    counts: UserCounts
