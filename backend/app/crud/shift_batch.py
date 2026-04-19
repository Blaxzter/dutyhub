from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.crud.base import CRUDBase
from app.models.shift_batch import ShiftBatch
from app.schemas.shift_batch import ShiftBatchCreate, ShiftBatchUpdate


class CRUDShiftBatch(CRUDBase[ShiftBatch, ShiftBatchCreate, ShiftBatchUpdate]):
    async def get_by_task(
        self,
        db: AsyncSession,
        *,
        task_id: str,
    ) -> list[ShiftBatch]:
        query = (
            select(ShiftBatch)
            .where(col(ShiftBatch.task_id) == task_id)
            .order_by(col(ShiftBatch.created_at).asc())
        )
        result = await db.execute(query)
        return list(result.scalars().all())


shift_batch = CRUDShiftBatch(ShiftBatch)
