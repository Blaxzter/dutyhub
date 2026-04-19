import uuid
from datetime import date, time
from typing import Any

import sqlalchemy as sa
from sqlmodel import Field, Relationship

from app.models.base import Base

if __name__ != "__main__":
    from app.models.shift import Shift  # noqa: F401

if __name__ != "__main__":
    from app.models.event import Event  # noqa: F401

if __name__ != "__main__":
    from app.models.shift_batch import ShiftBatch  # noqa: F401


class Task(Base, table=True):
    __tablename__ = "tasks"  # type: ignore[assignment]

    name: str = Field(sa_column=sa.Column(sa.String, nullable=False, index=True))
    description: str | None = Field(
        default=None, sa_column=sa.Column(sa.Text, nullable=True)
    )
    start_date: date = Field(sa_column=sa.Column(sa.Date, nullable=False, index=True))
    end_date: date = Field(sa_column=sa.Column(sa.Date, nullable=False, index=True))
    status: str = Field(
        default="draft", sa_column=sa.Column(sa.String, nullable=False, index=True)
    )
    created_by_id: uuid.UUID | None = Field(
        default=None,
        sa_column=sa.Column(
            sa.Uuid,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )
    event_id: uuid.UUID | None = Field(
        default=None,
        sa_column=sa.Column(
            sa.Uuid,
            sa.ForeignKey("events.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # Generation config fields (stored for re-generation)
    location: str | None = Field(
        default=None, sa_column=sa.Column(sa.String, nullable=True)
    )
    category: str | None = Field(
        default=None, sa_column=sa.Column(sa.String, nullable=True)
    )
    shift_duration_minutes: int | None = Field(
        default=None, sa_column=sa.Column(sa.Integer, nullable=True)
    )
    default_start_time: time | None = Field(
        default=None, sa_column=sa.Column(sa.Time, nullable=True)
    )
    default_end_time: time | None = Field(
        default=None, sa_column=sa.Column(sa.Time, nullable=True)
    )
    people_per_shift: int | None = Field(
        default=None, sa_column=sa.Column(sa.Integer, nullable=True)
    )
    schedule_overrides: list[dict[str, Any]] | None = Field(
        default=None, sa_column=sa.Column(sa.JSON, nullable=True)
    )

    shifts: list["Shift"] = Relationship(
        back_populates="task",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    shift_batches: list["ShiftBatch"] = Relationship(
        back_populates="task",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    event: "Event" = Relationship(back_populates="tasks")
