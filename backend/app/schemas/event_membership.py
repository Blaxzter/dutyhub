import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict

EventRole = Literal["owner", "admin", "member"]
"""Role a user holds within one event. Ordered weakest → strongest."""

AssignableEventRole = Literal["admin", "member"]
"""Roles that may be handed out directly. Ownership moves via transfer only."""


class EventMembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    event_id: uuid.UUID
    role: EventRole
    created_at: dt.datetime


class EventMemberRead(BaseModel):
    """A membership joined with the display fields of its user."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    event_id: uuid.UUID
    role: EventRole
    joined_at: dt.datetime
    name: str | None = None
    email: str | None = None
    avatar_etag: str | None = None


class EventMemberRoleUpdate(BaseModel):
    role: AssignableEventRole


class EventOwnershipTransfer(BaseModel):
    """Hand ownership of an event to another member.

    The outgoing owner is demoted to ``admin`` so they keep working access.
    """

    new_owner_id: uuid.UUID
