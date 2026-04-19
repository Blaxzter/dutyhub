"""Unit tests for Booking CRUD operations."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.booking import booking as crud_booking
from app.models.booking import Booking
from app.models.shift import Shift
from app.models.user import User
from app.schemas.booking import BookingBase, BookingUpdate


@pytest.mark.asyncio
class TestCRUDBooking:
    """Test suite for Booking CRUD operations."""

    async def test_create_booking(
        self, db_session: AsyncSession, test_shift: Shift, test_user: User
    ):
        """Test creating a new booking."""
        booking_in = BookingBase(
            shift_id=test_shift.id,
            user_id=test_user.id,
        )
        booking = await crud_booking.create(db_session, obj_in=booking_in)  # type: ignore[arg-type]

        assert booking.status == "confirmed"
        assert booking.user_id == test_user.id
        assert booking.shift_id == test_shift.id
        assert booking.id is not None

    async def test_get_by_shift_and_user(
        self, db_session: AsyncSession, test_booking: Booking
    ):
        """Test finding a booking by shift and user."""
        assert test_booking.shift_id is not None
        found = await crud_booking.get_by_shift_and_user(
            db_session,
            shift_id=test_booking.shift_id,
            user_id=test_booking.user_id,
        )

        assert found is not None
        assert found.id == test_booking.id

    async def test_get_by_shift_and_user_not_found(
        self, db_session: AsyncSession, test_shift: Shift, test_admin_user: User
    ):
        """Test searching for a non-existent booking by shift and user."""
        found = await crud_booking.get_by_shift_and_user(
            db_session,
            shift_id=test_shift.id,
            user_id=test_admin_user.id,
        )

        assert found is None

    async def test_get_confirmed_count(
        self, db_session: AsyncSession, test_booking: Booking
    ):
        """Test counting confirmed bookings for a shift."""
        assert test_booking.shift_id is not None
        count = await crud_booking.get_confirmed_count(
            db_session, shift_id=test_booking.shift_id
        )

        assert count == 1

    async def test_cancel_booking(
        self, db_session: AsyncSession, test_booking: Booking
    ):
        """Test cancelling a booking and verifying confirmed count."""
        updated = await crud_booking.update(
            db_session,
            db_obj=test_booking,
            obj_in=BookingUpdate(status="cancelled"),
        )

        assert updated.status == "cancelled"

        assert test_booking.shift_id is not None
        count = await crud_booking.get_confirmed_count(
            db_session, shift_id=test_booking.shift_id
        )
        assert count == 0

    async def test_get_multi_by_user(
        self, db_session: AsyncSession, test_booking: Booking, test_user: User
    ):
        """Test getting bookings for a specific user."""
        bookings = await crud_booking.get_multi_by_user(
            db_session, user_id=test_user.id
        )

        assert len(bookings) >= 1
        assert all(b.user_id == test_user.id for b in bookings)

    async def test_count_by_user(
        self, db_session: AsyncSession, test_booking: Booking, test_user: User
    ):
        """Test counting bookings for a specific user."""
        count = await crud_booking.count_by_user(db_session, user_id=test_user.id)

        assert count >= 1
