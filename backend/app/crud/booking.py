import datetime as dt
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col

from app.crud.base import CRUDBase
from app.models.booking import Booking
from app.models.shift import Shift
from app.schemas.booking import BookingCreate, BookingUpdate


class CRUDBooking(CRUDBase[Booking, BookingCreate, BookingUpdate]):
    async def get_by_shift_and_user(
        self,
        db: AsyncSession,
        *,
        shift_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Booking | None:
        query = select(Booking).where(
            col(Booking.shift_id) == shift_id,
            col(Booking.user_id) == user_id,
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_confirmed_count(
        self,
        db: AsyncSession,
        *,
        shift_id: uuid.UUID,
    ) -> int:
        query = (
            select(func.count())
            .select_from(Booking)
            .where(
                col(Booking.shift_id) == shift_id,
                col(Booking.status) == "confirmed",
            )
        )
        result = await db.execute(query)
        return result.scalar_one()

    async def get_multi_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
        with_shift: bool = False,
        date_from: dt.date | None = None,
        date_to: dt.date | None = None,
    ) -> list[Booking]:
        query = select(Booking).where(col(Booking.user_id) == user_id)
        if status:
            query = query.where(col(Booking.status) == status)
        if date_from or date_to:
            query = query.outerjoin(Shift, col(Booking.shift_id) == col(Shift.id))
            if date_from:
                query = query.where(
                    or_(
                        col(Shift.date) >= date_from,
                        col(Booking.cancelled_shift_date) >= date_from,
                    )
                )
            if date_to:
                query = query.where(
                    or_(
                        col(Shift.date) <= date_to,
                        col(Booking.cancelled_shift_date) <= date_to,
                    )
                )
        if with_shift:
            query = query.options(
                selectinload(Booking.shift).selectinload(Shift.task)  # type: ignore[arg-type]
            )
        query = query.order_by(col(Booking.created_at).desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        status: str | None = None,
        date_from: dt.date | None = None,
        date_to: dt.date | None = None,
    ) -> int:
        query = (
            select(func.count())
            .select_from(Booking)
            .where(col(Booking.user_id) == user_id)
        )
        if status:
            query = query.where(col(Booking.status) == status)
        if date_from or date_to:
            query = query.outerjoin(Shift, col(Booking.shift_id) == col(Shift.id))
            if date_from:
                query = query.where(
                    or_(
                        col(Shift.date) >= date_from,
                        col(Booking.cancelled_shift_date) >= date_from,
                    )
                )
            if date_to:
                query = query.where(
                    or_(
                        col(Shift.date) <= date_to,
                        col(Booking.cancelled_shift_date) <= date_to,
                    )
                )
        result = await db.execute(query)
        return result.scalar_one()

    async def get_multi_by_shift(
        self,
        db: AsyncSession,
        *,
        shift_id: uuid.UUID,
        status: str | None = None,
        with_user: bool = False,
    ) -> list[Booking]:
        query = select(Booking).where(col(Booking.shift_id) == shift_id)
        if status:
            query = query.where(col(Booking.status) == status)
        if with_user:
            query = query.options(selectinload(Booking.user))  # type: ignore[arg-type]
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_confirmed_by_task(
        self,
        db: AsyncSession,
        *,
        task_id: uuid.UUID,
    ) -> list[Booking]:
        """Get all confirmed bookings for every shift belonging to an task, with user data."""
        query = (
            select(Booking)
            .join(Shift, col(Booking.shift_id) == col(Shift.id))
            .where(col(Shift.task_id) == task_id)
            .where(col(Booking.status) == "confirmed")
            .options(selectinload(Booking.user))  # type: ignore[arg-type]
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def cancel_bookings_for_shifts(
        self,
        db: AsyncSession,
        *,
        slot_ids: list[uuid.UUID],
        task_name: str | None = None,
        cancellation_reason: str | None = None,
    ) -> int:
        """Cancel all confirmed bookings for the given shift IDs.

        Stores snapshot info from the shift so cancelled bookings remain
        meaningful after the shift is deleted (shift_id becomes NULL).
        Returns the number of bookings cancelled.
        """
        if not slot_ids:
            return 0

        # Load confirmed bookings with their shift info
        query = (
            select(Booking)
            .where(
                col(Booking.shift_id).in_(slot_ids),
                col(Booking.status) == "confirmed",
            )
            .options(selectinload(Booking.shift))  # type: ignore[arg-type]
        )
        result = await db.execute(query)
        bookings = list(result.scalars().all())

        for b in bookings:
            shift: Shift | None = b.shift
            if shift is None:
                continue
            b.status = "cancelled"
            b.cancellation_reason = cancellation_reason
            b.cancelled_shift_title = shift.title
            b.cancelled_shift_date = shift.date
            b.cancelled_shift_start_time = shift.start_time
            b.cancelled_shift_end_time = shift.end_time
            b.cancelled_task_name = task_name
            db.add(b)

        if bookings:
            await db.flush()

        return len(bookings)

    async def count_confirmed_for_shifts(
        self,
        db: AsyncSession,
        *,
        slot_ids: list[uuid.UUID],
    ) -> int:
        """Count confirmed bookings across multiple shifts."""
        if not slot_ids:
            return 0
        query = (
            select(func.count())
            .select_from(Booking)
            .where(
                col(Booking.shift_id).in_(slot_ids),
                col(Booking.status) == "confirmed",
            )
        )
        result = await db.execute(query)
        return result.scalar_one()


booking = CRUDBooking(Booking)
