import datetime as dt
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
from sqlmodel import col

from app.crud.base import CRUDBase
from app.models.booking import Booking
from app.models.duty_slot import DutySlot
from app.models.event import Event
from app.schemas.event import EventCreate, EventUpdate

EventSortField = Literal["name", "start_date", "end_date", "status", "created_at"]


class CRUDEvent(CRUDBase[Event, EventCreate, EventUpdate]):
    def _apply_common_filters(
        self,
        query: Select[Any],
        *,
        search: str | None = None,
        status: str | None = None,
        created_by_id: str | None = None,
        booked_by_user_id: str | None = None,
        date_from: dt.date | None = None,
        date_to: dt.date | None = None,
    ) -> Select[Any]:
        if search:
            query = query.where(
                col(Event.name).ilike(f"%{search}%")
                | col(Event.description).ilike(f"%{search}%")
            )
        if status:
            query = query.where(col(Event.status) == status)
        if created_by_id:
            query = query.where(col(Event.created_by_id) == created_by_id)
        if booked_by_user_id:
            query = query.where(
                col(Event.id).in_(
                    select(col(DutySlot.event_id))
                    .join(Booking, col(Booking.duty_slot_id) == col(DutySlot.id))
                    .where(
                        col(Booking.user_id) == booked_by_user_id,
                        col(Booking.status) == "confirmed",
                    )
                )
            )
        if date_from:
            query = query.where(col(Event.end_date) >= date_from)
        if date_to:
            query = query.where(col(Event.start_date) <= date_to)
        return query

    async def get_multi_filtered(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        status: str | None = None,
        created_by_id: str | None = None,
        booked_by_user_id: str | None = None,
        date_from: dt.date | None = None,
        date_to: dt.date | None = None,
        sort_by: EventSortField = "start_date",
        sort_dir: Literal["asc", "desc"] = "asc",
    ) -> list[Event]:
        query = select(Event)
        query = self._apply_common_filters(
            query,
            search=search,
            status=status,
            created_by_id=created_by_id,
            booked_by_user_id=booked_by_user_id,
            date_from=date_from,
            date_to=date_to,
        )
        order_col = getattr(Event, sort_by)
        query = query.order_by(
            col(order_col).asc() if sort_dir == "asc" else col(order_col).desc()
        )
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_count_filtered(
        self,
        db: AsyncSession,
        *,
        search: str | None = None,
        status: str | None = None,
        created_by_id: str | None = None,
        booked_by_user_id: str | None = None,
        date_from: dt.date | None = None,
        date_to: dt.date | None = None,
    ) -> int:
        query = select(func.count()).select_from(Event)
        query = self._apply_common_filters(
            query,
            search=search,
            status=status,
            created_by_id=created_by_id,
            booked_by_user_id=booked_by_user_id,
            date_from=date_from,
            date_to=date_to,
        )
        result = await db.execute(query)
        return result.scalar_one()


event = CRUDEvent(Event)
