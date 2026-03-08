from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.crud.base import CRUDBase
from app.models.event_group import EventGroup
from app.schemas.event_group import EventGroupCreate, EventGroupUpdate

EventGroupSortField = Literal["name", "start_date", "end_date", "status", "created_at"]


class CRUDEventGroup(CRUDBase[EventGroup, EventGroupCreate, EventGroupUpdate]):
    async def get_multi_filtered(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        status: str | None = None,
        sort_by: EventGroupSortField = "start_date",
        sort_dir: Literal["asc", "desc"] = "asc",
    ) -> list[EventGroup]:
        query = select(EventGroup)
        if search:
            query = query.where(
                col(EventGroup.name).ilike(f"%{search}%")
                | col(EventGroup.description).ilike(f"%{search}%")
            )
        if status:
            query = query.where(col(EventGroup.status) == status)
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
    ) -> int:
        query = select(func.count()).select_from(EventGroup)
        if search:
            query = query.where(
                col(EventGroup.name).ilike(f"%{search}%")
                | col(EventGroup.description).ilike(f"%{search}%")
            )
        if status:
            query = query.where(col(EventGroup.status) == status)
        result = await db.execute(query)
        return result.scalar_one()


event_group = CRUDEventGroup(EventGroup)
