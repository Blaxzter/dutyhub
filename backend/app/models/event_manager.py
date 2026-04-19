import uuid

import sqlalchemy as sa
from sqlmodel import Field

from app.models.base import Base


class EventManager(Base, table=True):
    __tablename__ = "event_managers"  # type: ignore[assignment]

    __table_args__ = (
        sa.UniqueConstraint("user_id", "event_id", name="uq_event_manager"),
    )

    user_id: uuid.UUID = Field(
        sa_column=sa.Column(
            sa.Uuid,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    event_id: uuid.UUID = Field(
        sa_column=sa.Column(
            sa.Uuid,
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
