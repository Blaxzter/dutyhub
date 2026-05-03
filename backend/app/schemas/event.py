import datetime as dt
import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, computed_field, field_validator

EventStatus = Literal["draft", "published", "archived"]


class EventBase(BaseModel):
    name: str
    description: str | None = None
    start_date: dt.date
    end_date: dt.date
    default_start_time: dt.time | None = None
    default_end_time: dt.time | None = None
    status: EventStatus = "draft"

    @field_validator("end_date")
    @classmethod
    def end_date_after_start(cls, v: dt.date, info: Any) -> dt.date:
        start = info.data.get("start_date")
        if start and v < start:
            msg = "end_date must be on or after start_date"
            raise ValueError(msg)
        return v

    @field_validator("default_end_time")
    @classmethod
    def default_end_time_after_start(
        cls, v: dt.time | None, info: Any
    ) -> dt.time | None:
        start = info.data.get("default_start_time")
        if start is not None and v is not None and v <= start:
            msg = (
                "default_end_time must be after default_start_time. "
                "Overnight windows are not yet supported — leave both empty for "
                "events that span midnight."
            )
            raise ValueError(msg)
        return v


class EventCreate(EventBase):
    created_by_id: uuid.UUID | None = None


class EventUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    default_start_time: dt.time | None = None
    default_end_time: dt.time | None = None
    status: EventStatus | None = None


class EventRead(EventBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_by_id: uuid.UUID | None = None
    created_at: dt.datetime
    updated_at: dt.datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_expired(self) -> bool:
        return self.end_date < dt.date.today()


class EventListResponse(BaseModel):
    items: list[EventRead]
    total: int
    skip: int
    limit: int
