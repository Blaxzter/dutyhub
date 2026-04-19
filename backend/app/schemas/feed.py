import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel

from app.schemas.task import TaskRead

FeedView = Literal["list", "cards", "calendar"]
FeedFocusMode = Literal["today", "first_available"]


class FeedSlotEntry(BaseModel):
    """Lightweight slot for the feed — no title/description, just booking info."""

    id: uuid.UUID
    date: dt.date
    start_time: dt.time | None = None
    end_time: dt.time | None = None
    max_bookings: int = 1
    current_bookings: int = 0
    is_booked_by_me: bool = False


class FeedTaskItem(TaskRead):
    """Task with view-dependent embedded data."""

    # List view: embedded slots for the visible 5-day window
    slots: list[FeedSlotEntry] | None = None
    slot_window_start: dt.date | None = None

    # Cards / calendar view: aggregated stats
    total_slots: int | None = None
    available_slots: int | None = None


class TaskFeedResponse(BaseModel):
    items: list[FeedTaskItem]
    total: int
    skip: int
    limit: int


class SlotWindowResponse(BaseModel):
    """Response for the slot-window endpoint (next/prev day navigation)."""

    slots: list[FeedSlotEntry]
    start_date: dt.date
    days: int
