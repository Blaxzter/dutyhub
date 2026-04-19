from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.crud.base import CRUDBase
from app.models.slot_batch import SlotBatch
from app.schemas.slot_batch import SlotBatchCreate, SlotBatchUpdate


class CRUDSlotBatch(CRUDBase[SlotBatch, SlotBatchCreate, SlotBatchUpdate]):
    async def get_by_task(
        self,
        db: AsyncSession,
        *,
        task_id: str,
    ) -> list[SlotBatch]:
        query = (
            select(SlotBatch)
            .where(col(SlotBatch.task_id) == task_id)
            .order_by(col(SlotBatch.created_at).asc())
        )
        result = await db.execute(query)
        return list(result.scalars().all())


slot_batch = CRUDSlotBatch(SlotBatch)
