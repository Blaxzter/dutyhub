import uuid
from typing import Any, Literal

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.crud.base import CRUDBase
from app.models.shift import Shift
from app.models.task import Task
from app.schemas.shift import ShiftCreate, ShiftUpdate

ShiftSortField = Literal["title", "date", "start_time", "category", "created_at"]


class CRUDShift(CRUDBase[Shift, ShiftCreate, ShiftUpdate]):
    @staticmethod
    def _apply_event_scope(
        query: Select[Any],
        *,
        restrict_to_event_ids: list[uuid.UUID] | None,
    ) -> Select[Any]:
        """Limit a shift query to the events the caller may see.

        Shifts carry no event of their own, so the scope has to come through
        their task. ``None`` means unrestricted - the platform superadmin -
        and even then demo tasks are excluded, because a sandbox belongs to one
        guest and nobody else, superadmin included.

        An empty list means "nothing", and must never be allowed to degrade to
        "everything": that is the difference between a new account seeing no
        shifts and seeing every shift in the database.
        """
        query = query.join(Task, col(Shift.task_id) == col(Task.id))
        if restrict_to_event_ids is None:
            return query.where(col(Task.is_sandbox).is_(False))
        return query.where(col(Task.event_id).in_(restrict_to_event_ids))

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
        restrict_to_event_ids: list[uuid.UUID] | None = None,
    ) -> list[Shift]:
        query = self._apply_event_scope(
            select(Shift), restrict_to_event_ids=restrict_to_event_ids
        )
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
        restrict_to_event_ids: list[uuid.UUID] | None = None,
    ) -> int:
        query = self._apply_event_scope(
            select(func.count()).select_from(Shift),
            restrict_to_event_ids=restrict_to_event_ids,
        )
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
