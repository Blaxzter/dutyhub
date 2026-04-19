from pydantic import BaseModel, Field

DEMO_PREFIX = "[DEMO]"


class DemoDataParams(BaseModel):
    num_tasks: int = Field(default=10, ge=1, le=50)
    num_events: int = Field(default=3, ge=0, le=10)
    num_users: int = Field(default=5, ge=0, le=20)
    num_shifts_per_task: int = Field(default=4, ge=1, le=20)
    publish_tasks: bool = Field(default=True)


class DemoDataCreatedResponse(BaseModel):
    events_created: int
    tasks_created: int
    users_created: int
    shifts_created: int
    bookings_created: int


class DemoDataDeletedResponse(BaseModel):
    tasks_deleted: int
    events_deleted: int
    users_deleted: int
    shifts_deleted: int
    bookings_deleted: int
