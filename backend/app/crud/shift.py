from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.crud.base import CRUDBase
from app.models.shift import Shift
from app.schemas.shift import ShiftCreate, ShiftUpdate

ShiftSortField = Literal["title", "date", "start_time", "category", "created_at"]


class CRUDShift(CRUDBase[Shift, ShiftCreate, ShiftUpdate]):
    async def get_multi_filtered(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        task_id: str | None = None,
        category: str | None = None,
        search: str | None = None,
        sort_by: ShiftSortField = "date",
        sort_dir: Literal["asc", "desc"] = "asc",
    ) -> list[Shift]:
        query = select(Shift)
        if task_id:
            query = query.where(col(Shift.task_id) == task_id)
        if category:
            query = query.where(col(Shift.category) == category)
        if search:
            query = query.where(
                col(Shift.title).ilike(f"%{search}%")
                | col(Shift.description).ilike(f"%{search}%")
            )
        order_col = getattr(Shift, sort_by)
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
        task_id: str | None = None,
        category: str | None = None,
        search: str | None = None,
    ) -> int:
        query = select(func.count()).select_from(Shift)
        if task_id:
            query = query.where(col(Shift.task_id) == task_id)
        if category:
            query = query.where(col(Shift.category) == category)
        if search:
            query = query.where(
                col(Shift.title).ilike(f"%{search}%")
                | col(Shift.description).ilike(f"%{search}%")
            )
        result = await db.execute(query)
        return result.scalar_one()


shift = CRUDShift(Shift)
