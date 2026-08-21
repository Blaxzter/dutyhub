import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

JoinRequestStatus = Literal["pending", "approved", "declined"]


class EventJoinRequestCreate(BaseModel):
    message: str | None = Field(default=None, max_length=500)


class EventJoinRequestDecision(BaseModel):
    approve: bool
    role: Literal["admin", "member"] = "member"


class EventJoinRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    user_id: uuid.UUID
    status: JoinRequestStatus
    message: str | None = None
    created_at: dt.datetime
    decided_at: dt.datetime | None = None
    user_name: str | None = None
    user_email: str | None = None
    user_avatar_etag: str | None = None
