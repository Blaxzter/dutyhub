import datetime as dt
import uuid
from typing import Any, Literal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
from sqlmodel import col

from app.crud.base import CRUDBase
from app.models.event_group import EventGroup
from app.schemas.event_group import EventGroupCreate, EventGroupUpdate

EventGroupSortField = Literal["name", "start_date", "end_date", "status", "created_at"]


class CRUDEventGroup(CRUDBase[EventGroup, EventGroupCreate, EventGroupUpdate]):
    def _apply_common_filters(
        self,
        query: Select[Any],
        *,
        search: str | None = None,
        status: str | None = None,
        date_from: dt.date | None = None,
        date_to: dt.date | None = None,
        also_include_ids: list[uuid.UUID] | None = None,
    ) -> Select[Any]:
        if search:
            query = query.where(
                col(EventGroup.name).ilike(f"%{search}%")
                | col(EventGroup.description).ilike(f"%{search}%")
            )
        if status:
            status_filter = col(EventGroup.status) == status
            if also_include_ids:
                status_filter = or_(
                    status_filter, col(EventGroup.id).in_(also_include_ids)
                )
            query = query.where(status_filter)
        if date_from:
            query = query.where(col(EventGroup.end_date) >= date_from)
        if date_to:
            query = query.where(col(EventGroup.start_date) <= date_to)
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
        sort_by: EventGroupSortField = "start_date",
        sort_dir: Literal["asc", "desc"] = "asc",
        also_include_ids: list[uuid.UUID] | None = None,
    ) -> list[EventGroup]:
        query = select(EventGroup)
        query = self._apply_common_filters(
            query,
            search=search,
            status=status,
            date_from=date_from,
            date_to=date_to,
            also_include_ids=also_include_ids,
        )
        order_col = getattr(EventGroup, sort_by)
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
        also_include_ids: list[uuid.UUID] | None = None,
    ) -> int:
        query = select(func.count()).select_from(EventGroup)
        query = self._apply_common_filters(
            query,
            search=search,
            status=status,
            date_from=date_from,
            date_to=date_to,
            also_include_ids=also_include_ids,
        )
        result = await db.execute(query)
        return result.scalar_one()


event_group = CRUDEventGroup(EventGroup)
