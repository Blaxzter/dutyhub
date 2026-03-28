import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict

ReminderStatus = Literal["pending", "sent", "cancelled", "expired"]

# Allowed offsets in minutes (prevent abuse)
ALLOWED_OFFSETS = {15, 30, 60, 120, 180, 360, 720, 1440, 2880}
ALLOWED_CHANNELS = {"email", "push", "telegram"}
MAX_REMINDERS_PER_BOOKING = 5


class BookingReminderCreate(BaseModel):
    """User provides the offset and channels; remind_at is computed server-side."""

    offset_minutes: int
    channels: list[str] = ["push"]


class BookingReminderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    booking_id: uuid.UUID
    offset_minutes: int
    channels: list[str]
    remind_at: dt.datetime
    status: ReminderStatus
    created_at: dt.datetime


class BookingReminderListResponse(BaseModel):
    items: list[BookingReminderRead]


class ReminderOffsetEntry(BaseModel):
    """A single default reminder: offset + which channels to use."""

    offset_minutes: int
    channels: list[str] = ["push"]


class DefaultReminderOffsetsRead(BaseModel):
    default_reminder_offsets: list[ReminderOffsetEntry]


class DefaultReminderOffsetsUpdate(BaseModel):
    default_reminder_offsets: list[ReminderOffsetEntry]
