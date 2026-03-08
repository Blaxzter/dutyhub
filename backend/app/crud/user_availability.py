import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col

from app.crud.base import CRUDBase
from app.models.user_availability import UserAvailability, UserAvailabilityDate
from app.schemas.user_availability import UserAvailabilityCreate, UserAvailabilityUpdate


class CRUDUserAvailability(
    CRUDBase[UserAvailability, UserAvailabilityCreate, UserAvailabilityUpdate]
):
    async def get_by_user_and_group(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        event_group_id: uuid.UUID,
    ) -> UserAvailability | None:
        query = (
            select(UserAvailability)
            .where(
                col(UserAvailability.user_id) == user_id,
                col(UserAvailability.event_group_id) == event_group_id,
            )
            .options(selectinload(UserAvailability.available_dates))  # type: ignore[arg-type]
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi_by_group(
        self,
        db: AsyncSession,
        *,
        event_group_id: uuid.UUID,
        skip: int = 0,
        limit: int = 200,
    ) -> list[UserAvailability]:
        query = (
            select(UserAvailability)
            .where(col(UserAvailability.event_group_id) == event_group_id)
            .options(selectinload(UserAvailability.available_dates))  # type: ignore[arg-type]
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def upsert_for_user(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        event_group_id: uuid.UUID,
        obj_in: UserAvailabilityCreate,
    ) -> UserAvailability:
        existing = await self.get_by_user_and_group(
            db, user_id=user_id, event_group_id=event_group_id
        )
        if existing:
            # Update fields
            existing.availability_type = obj_in.availability_type
            existing.notes = obj_in.notes
            # Replace dates
            for d in list(existing.available_dates):
                await db.delete(d)
            await db.flush()
            existing.available_dates = []
            for day in obj_in.dates:
                db.add(UserAvailabilityDate(availability_id=existing.id, slot_date=day))
            db.add(existing)
            await db.flush()
            await db.refresh(existing)
            # Re-load dates
            existing = await self.get_by_user_and_group(
                db, user_id=user_id, event_group_id=event_group_id
            )
            return existing  # type: ignore[return-value]
        else:
            avail = UserAvailability(
                user_id=user_id,
                event_group_id=event_group_id,
                availability_type=obj_in.availability_type,
                notes=obj_in.notes,
            )
            db.add(avail)
            await db.flush()
            await db.refresh(avail)
            for day in obj_in.dates:
                db.add(UserAvailabilityDate(availability_id=avail.id, slot_date=day))
            await db.flush()
            # Load with dates
            result = await self.get_by_user_and_group(
                db, user_id=user_id, event_group_id=event_group_id
            )
            return result  # type: ignore[return-value]

    async def delete_for_user(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        event_group_id: uuid.UUID,
    ) -> bool:
        existing = await self.get_by_user_and_group(
            db, user_id=user_id, event_group_id=event_group_id
        )
        if not existing:
            return False
        await db.delete(existing)
        await db.flush()
        return True


user_availability = CRUDUserAvailability(UserAvailability)
