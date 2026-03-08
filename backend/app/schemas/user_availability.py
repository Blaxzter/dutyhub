import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict

AvailabilityType = Literal["fully_available", "specific_dates"]


class UserAvailabilityDateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    slot_date: dt.date


class UserAvailabilityBase(BaseModel):
    availability_type: AvailabilityType
    notes: str | None = None


class UserAvailabilityCreate(UserAvailabilityBase):
    dates: list[dt.date] = []


class UserAvailabilityUpdate(BaseModel):
    availability_type: AvailabilityType | None = None
    notes: str | None = None
    dates: list[dt.date] | None = None


class UserAvailabilityRead(UserAvailabilityBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    event_group_id: uuid.UUID
    available_dates: list[UserAvailabilityDateRead] = []
    created_at: dt.datetime
    updated_at: dt.datetime


class UserAvailabilityWithUser(UserAvailabilityRead):
    """Extended read schema for admin view — includes basic user info."""

    user_full_name: str | None = None
    user_email: str | None = None
