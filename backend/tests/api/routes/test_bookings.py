"""Route tests for Booking endpoints."""

from datetime import date, time

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.shift import Shift
from app.models.task import Task
from app.models.user import User


@pytest.mark.asyncio
class TestBookingsRoutes:
    """Test suite for /bookings/ routes."""

    async def test_create_booking(self, async_client: AsyncClient, test_shift: Shift):
        """Test creating a new booking."""
        r = await async_client.post(
            "/api/v1/bookings/",
            json={"shift_id": str(test_shift.id)},
        )

        assert r.status_code == 201
        assert r.json()["status"] == "confirmed"
        assert r.json()["shift_id"] == str(test_shift.id)

    async def test_double_booking_prevented(
        self, async_client: AsyncClient, test_booking: Booking, test_shift: Shift
    ):
        """Test that a user cannot double-book the same shift."""
        r = await async_client.post(
            "/api/v1/bookings/",
            json={"shift_id": str(test_shift.id)},
        )

        assert r.status_code == 409

    async def test_list_my_bookings(
        self, async_client: AsyncClient, test_booking: Booking
    ):
        """Test listing the current user's bookings."""
        r = await async_client.get("/api/v1/bookings/me")

        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert any(item["id"] == str(test_booking.id) for item in data["items"])

    async def test_get_booking(self, async_client: AsyncClient, test_booking: Booking):
        """Test getting a specific booking."""
        r = await async_client.get(f"/api/v1/bookings/{test_booking.id}")

        assert r.status_code == 200
        assert r.json()["id"] == str(test_booking.id)

    async def test_cancel_booking(
        self, async_client: AsyncClient, test_booking: Booking
    ):
        """Test cancelling a booking via DELETE."""
        r = await async_client.delete(f"/api/v1/bookings/{test_booking.id}")

        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"

    async def test_update_booking_notes(
        self, async_client: AsyncClient, test_booking: Booking
    ):
        """Test updating booking notes."""
        r = await async_client.patch(
            f"/api/v1/bookings/{test_booking.id}",
            json={"notes": "Updated notes"},
        )

        assert r.status_code == 200
        assert r.json()["notes"] == "Updated notes"

    async def test_shift_capacity_enforced(
        self, async_client: AsyncClient, db_session: AsyncSession, test_task: Task
    ):
        """Test that bookings are rejected when a shift is full."""
        shift = Shift(
            task_id=test_task.id,
            title="Limited Shift",
            date=date(2026, 5, 24),
            start_time=time(14, 0),
            end_time=time(18, 0),
            max_bookings=1,
        )
        db_session.add(shift)
        await db_session.flush()
        await db_session.refresh(shift)

        other_user = User(
            auth0_sub="auth0|other_user_cap_test",
            email="other@example.com",
            name="Other",
            roles=[],
        )
        db_session.add(other_user)
        await db_session.flush()

        existing = Booking(
            shift_id=shift.id,
            user_id=other_user.id,
            status="confirmed",
        )
        db_session.add(existing)
        await db_session.flush()

        r = await async_client.post(
            "/api/v1/bookings/",
            json={"shift_id": str(shift.id)},
        )

        assert r.status_code == 409

    async def test_get_nonexistent_booking(self, async_client: AsyncClient):
        """Test getting a non-existent booking returns 404."""
        import uuid

        fake_id = uuid.uuid4()
        r = await async_client.get(f"/api/v1/bookings/{fake_id}")

        assert r.status_code == 404
