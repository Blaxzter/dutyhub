import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict


class DashboardTask(BaseModel):
    """Slim task for the dashboard calendar."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    status: str
    description: str | None = None
    location: str | None = None
    start_date: dt.date
    end_date: dt.date


class DashboardEvent(BaseModel):
    """Slim task group for the dashboard calendar."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    start_date: dt.date
    end_date: dt.date


class DashboardBookingItem(BaseModel):
    """Booking with inline shift info for calendar display — avoids N+1."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slot_id: uuid.UUID
    date: dt.date
    title: str
    start_time: dt.time | None = None
    end_time: dt.time | None = None


class DashboardFeedResponse(BaseModel):
    tasks: list[DashboardTask]
    task_count: int
    events: list[DashboardEvent]
    bookings: list[DashboardBookingItem]
    booking_count: int
    pending_user_count: int | None = None
