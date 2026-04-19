import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.models.event_manager import EventManager


class CRUDEventManager:
    async def is_manager(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        event_id: uuid.UUID,
    ) -> bool:
        result = await session.execute(
            select(EventManager).where(
                col(EventManager.user_id) == user_id,
                col(EventManager.event_id) == event_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_by_group(
        self,
        session: AsyncSession,
        *,
        event_id: uuid.UUID,
    ) -> list[EventManager]:
        result = await session.execute(
            select(EventManager).where(col(EventManager.event_id) == event_id)
        )
        return list(result.scalars().all())

    async def assign(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        event_id: uuid.UUID,
    ) -> EventManager:
        existing = await session.execute(
            select(EventManager).where(
                col(EventManager.user_id) == user_id,
                col(EventManager.event_id) == event_id,
            )
        )
        obj = existing.scalar_one_or_none()
        if obj:
            return obj
        obj = EventManager(user_id=user_id, event_id=event_id)
        session.add(obj)
        await session.flush()
        await session.refresh(obj)
        return obj

    async def remove(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        event_id: uuid.UUID,
    ) -> bool:
        result = await session.execute(
            delete(EventManager).where(
                col(EventManager.user_id) == user_id,
                col(EventManager.event_id) == event_id,
            )
        )
        return result.rowcount > 0  # type: ignore[return-value]


event_manager = CRUDEventManager()
