import datetime as dt
import uuid
from typing import Any, Literal, cast

from sqlalchemy import CursorResult, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
from sqlmodel import col

from app.crud.base import CRUDBase
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
        date_from: dt.date | None = None,
        date_to: dt.date | None = None,
        is_expired: bool | None = None,
        also_include_ids: list[uuid.UUID] | None = None,
    ) -> Select[Any]:
        if search:
            query = query.where(
                col(Event.name).ilike(f"%{search}%")
                | col(Event.description).ilike(f"%{search}%")
            )
        if status:
            status_filter = col(Event.status) == status
            if also_include_ids:
                status_filter = or_(status_filter, col(Event.id).in_(also_include_ids))
            query = query.where(status_filter)
        if date_from:
            query = query.where(col(Event.end_date) >= date_from)
        if date_to:
            query = query.where(col(Event.start_date) <= date_to)
        if is_expired is not None:
            today = dt.date.today()
            if is_expired:
                query = query.where(col(Event.end_date) < today)
            else:
                query = query.where(col(Event.end_date) >= today)
        return query

    async def get_multi_filtered(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        status: str | None = None,
        date_from: dt.date | None = None,
        date_to: dt.date | None = None,
        is_expired: bool | None = None,
        sort_by: EventSortField = "start_date",
        sort_dir: Literal["asc", "desc"] = "asc",
        also_include_ids: list[uuid.UUID] | None = None,
    ) -> list[Event]:
        query = select(Event)
        query = self._apply_common_filters(
            query,
            search=search,
            status=status,
            date_from=date_from,
            date_to=date_to,
            is_expired=is_expired,
            also_include_ids=also_include_ids,
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
        date_from: dt.date | None = None,
        date_to: dt.date | None = None,
        is_expired: bool | None = None,
        also_include_ids: list[uuid.UUID] | None = None,
    ) -> int:
        query = select(func.count()).select_from(Event)
        query = self._apply_common_filters(
            query,
            search=search,
            status=status,
            date_from=date_from,
            date_to=date_to,
            is_expired=is_expired,
            also_include_ids=also_include_ids,
        )
        result = await db.execute(query)
        return result.scalar_one()

    async def count_owned_by(self, db: AsyncSession, *, user_id: uuid.UUID) -> int:
        """Count events created by the given user."""
        result = await db.execute(
            select(func.count())
            .select_from(Event)
            .where(col(Event.created_by_id) == user_id)
        )
        return result.scalar_one()

    async def reassign_owner(
        self,
        db: AsyncSession,
        *,
        from_user_id: uuid.UUID,
        to_user_id: uuid.UUID,
    ) -> int:
        """Reassign all events created by one user to another. Returns row count."""
        result = cast(
            CursorResult[Any],
            await db.execute(
                update(Event)
                .where(col(Event.created_by_id) == from_user_id)
                .values(created_by_id=to_user_id)
            ),
        )
        return result.rowcount if result.rowcount > 0 else 0


event = CRUDEvent(Event)
