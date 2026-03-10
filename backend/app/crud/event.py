from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
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
        query,
        *,
        search: str | None = None,
        status: str | None = None,
        created_by_id: str | None = None,
        booked_by_user_id: str | None = None,
    ):
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
                Event.id.in_(  # type: ignore[attr-defined]
                    select(DutySlot.event_id)
                    .join(Booking, Booking.duty_slot_id == DutySlot.id)
                    .where(
                        Booking.user_id == booked_by_user_id,
                        Booking.status == "confirmed",
                    )
                )
            )
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
    ) -> int:
        query = select(func.count()).select_from(Event)
        query = self._apply_common_filters(
            query,
            search=search,
            status=status,
            created_by_id=created_by_id,
            booked_by_user_id=booked_by_user_id,
        )
        result = await db.execute(query)
        return result.scalar_one()


event = CRUDEvent(Event)
