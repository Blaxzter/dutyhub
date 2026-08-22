import uuid
from datetime import date, time
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlmodel import Field, Relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.user_availability import UserAvailability


class Event(Base, table=True):
    __tablename__ = "events"  # type: ignore[assignment]

    name: str = Field(sa_column=sa.Column(sa.String, nullable=False, index=True))
    description: str | None = Field(
        default=None, sa_column=sa.Column(sa.Text, nullable=True)
    )
    start_date: date = Field(sa_column=sa.Column(sa.Date, nullable=False))
    end_date: date = Field(sa_column=sa.Column(sa.Date, nullable=False))
    default_start_time: time | None = Field(
        default=None, sa_column=sa.Column(sa.Time, nullable=True)
    )
    default_end_time: time | None = Field(
        default=None, sa_column=sa.Column(sa.Time, nullable=True)
    )
    status: str = Field(
        default="draft", sa_column=sa.Column(sa.String, nullable=False, index=True)
    )
    visibility: str = Field(
        default="private",
        sa_column=sa.Column(
            sa.String(16), nullable=False, server_default="private", index=True
        ),
        description=(
            "'public' — listed in Discover, anyone may request to join. "
            "'private' — invitation only, invisible to non-members."
        ),
    )
    is_featured: bool = Field(
        default=False,
        sa_column=sa.Column(
            sa.Boolean, nullable=False, server_default=sa.text("false"), index=True
        ),
        description="Superadmin-curated: surfaced on the home screen",
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

    tasks: list["Task"] = Relationship(back_populates="event")
    availabilities: list["UserAvailability"] = Relationship(
        back_populates="event",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    @property
    def is_expired(self) -> bool:
        """Whether the event's end date is in the past."""
        from datetime import date as _date

        return self.end_date < _date.today()
