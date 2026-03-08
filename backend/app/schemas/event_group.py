import datetime as dt
import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

EventGroupStatus = Literal["draft", "published", "archived"]


class EventGroupBase(BaseModel):
    name: str
    description: str | None = None
    start_date: dt.date
    end_date: dt.date
    status: EventGroupStatus = "draft"

    @field_validator("end_date")
    @classmethod
    def end_date_after_start(cls, v: dt.date, info: Any) -> dt.date:
        start = info.data.get("start_date")
        if start and v < start:
            msg = "end_date must be on or after start_date"
            raise ValueError(msg)
        return v


class EventGroupCreate(EventGroupBase):
    created_by_id: uuid.UUID | None = None


class EventGroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    status: EventGroupStatus | None = None


class EventGroupRead(EventGroupBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_by_id: uuid.UUID | None = None
    created_at: dt.datetime
    updated_at: dt.datetime


class EventGroupListResponse(BaseModel):
    items: list[EventGroupRead]
    total: int
    skip: int
    limit: int
