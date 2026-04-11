import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.models.event_group_manager import EventGroupManager


class CRUDEventGroupManager:
    async def is_manager(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        event_group_id: uuid.UUID,
    ) -> bool:
        result = await session.execute(
            select(EventGroupManager).where(
                col(EventGroupManager.user_id) == user_id,
                col(EventGroupManager.event_group_id) == event_group_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_by_group(
        self,
        session: AsyncSession,
        *,
        event_group_id: uuid.UUID,
    ) -> list[EventGroupManager]:
        result = await session.execute(
            select(EventGroupManager).where(
                col(EventGroupManager.event_group_id) == event_group_id
            )
        )
        return list(result.scalars().all())

    async def assign(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        event_group_id: uuid.UUID,
    ) -> EventGroupManager:
        existing = await session.execute(
            select(EventGroupManager).where(
                col(EventGroupManager.user_id) == user_id,
                col(EventGroupManager.event_group_id) == event_group_id,
            )
        )
        obj = existing.scalar_one_or_none()
        if obj:
            return obj
        obj = EventGroupManager(user_id=user_id, event_group_id=event_group_id)
        session.add(obj)
        await session.flush()
        await session.refresh(obj)
        return obj

    async def remove(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        event_group_id: uuid.UUID,
    ) -> bool:
        result = await session.execute(
            delete(EventGroupManager).where(
                col(EventGroupManager.user_id) == user_id,
                col(EventGroupManager.event_group_id) == event_group_id,
            )
        )
        return result.rowcount > 0  # type: ignore[return-value]


event_group_manager = CRUDEventGroupManager()
