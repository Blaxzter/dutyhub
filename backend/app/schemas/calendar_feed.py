import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CalendarFeedRead(BaseModel):
    """Response for calendar feed management endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    feed_url: str
    is_enabled: bool
    last_accessed_at: datetime | None = None
    created_at: datetime


class CalendarFeedToggle(BaseModel):
    """Request to enable/disable the feed."""

    is_enabled: bool
