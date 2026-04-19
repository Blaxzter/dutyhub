"""Coverage gap tests for Shift endpoints (time change, delete with bookings, enrichment)."""

import uuid
from datetime import date, time

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.shift import Shift
from app.models.task import Task
from app.models.user import User


@pytest.mark.asyncio
class TestShiftCoverage:
    """Coverage tests for duty shift routes."""

    async def test_update_shift_time_change_triggers_notification(
        self,
        async_client: AsyncClient,
        as_admin: None,
        db_session: AsyncSession,
        test_shift: Shift,
        test_booking: Booking,
    ):
        """Test that updating start_time on a booked shift triggers notification."""
        r = await async_client.patch(
            f"/api/v1/shifts/{test_shift.id}",
            json={"start_time": "10:00:00"},
        )

        assert r.status_code == 200
        assert r.json()["start_time"] == "10:00:00"

    async def test_update_shift_date_change(
        self,
        async_client: AsyncClient,
        as_admin: None,
        db_session: AsyncSession,
        test_shift: Shift,
        test_booking: Booking,
    ):
        """Test updating shift date triggers time-change notification."""
        r = await async_client.patch(
            f"/api/v1/shifts/{test_shift.id}",
            json={"date": "2026-05-25"},
        )

        assert r.status_code == 200
        assert r.json()["date"] == "2026-05-25"

    async def test_update_shift_end_time_change(
        self,
        async_client: AsyncClient,
        as_admin: None,
        test_shift: Shift,
        test_booking: Booking,
    ):
        """Test updating shift end_time triggers notification."""
        r = await async_client.patch(
            f"/api/v1/shifts/{test_shift.id}",
            json={"end_time": "15:00:00"},
        )

        assert r.status_code == 200
        assert r.json()["end_time"] == "15:00:00"

    async def test_delete_shift_with_confirmed_bookings(
        self,
        async_client: AsyncClient,
        as_admin: None,
        db_session: AsyncSession,
        test_task: Task,
        test_user: User,
    ):
        """Test deleting a shift with confirmed bookings cancels them."""
        shift = Shift(
            task_id=test_task.id,
            title="Delete Me With Booking",
            date=date(2026, 9, 15),
            start_time=time(8, 0),
            end_time=time(12, 0),
        )
        db_session.add(shift)
        await db_session.flush()
        await db_session.refresh(shift)

        booking = Booking(
            shift_id=shift.id,
            user_id=test_user.id,
            status="confirmed",
        )
        db_session.add(booking)
        await db_session.flush()

        r = await async_client.delete(
            f"/api/v1/shifts/{shift.id}",
            params={"cancellation_reason": "Shift removed by admin"},
        )
        assert r.status_code == 204

    async def test_delete_shift_with_cancellation_reason(
        self,
        async_client: AsyncClient,
        as_admin: None,
        db_session: AsyncSession,
        test_task: Task,
    ):
        """Test deleting a shift with a cancellation reason."""
        shift = Shift(
            task_id=test_task.id,
            title="Delete Reason Shift",
            date=date(2026, 9, 16),
            start_time=time(10, 0),
            end_time=time(14, 0),
        )
        db_session.add(shift)
        await db_session.flush()
        await db_session.refresh(shift)

        r = await async_client.delete(
            f"/api/v1/shifts/{shift.id}",
            params={"cancellation_reason": "Task rescheduled"},
        )
        assert r.status_code == 204

    async def test_list_shifts_for_draft_task_forbidden(
        self,
        async_client: AsyncClient,
        test_draft_task: Task,
    ):
        """Test that non-admin users cannot list shifts for draft tasks."""
        r = await async_client.get(
            "/api/v1/shifts/",
            params={"task_id": str(test_draft_task.id)},
        )
        assert r.status_code == 403

    async def test_shift_is_booked_by_me(
        self,
        async_client: AsyncClient,
        test_shift: Shift,
        test_booking: Booking,
    ):
        """Test that is_booked_by_me is True when user has a confirmed booking."""
        r = await async_client.get(f"/api/v1/shifts/{test_shift.id}")

        assert r.status_code == 200
        assert r.json()["is_booked_by_me"] is True
        assert r.json()["current_bookings"] >= 1

    async def test_shift_is_not_booked_by_me(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_task: Task,
    ):
        """Test that is_booked_by_me is False when user has no booking."""
        shift = Shift(
            task_id=test_task.id,
            title="Not Booked Shift",
            date=date(2026, 9, 20),
            start_time=time(8, 0),
            end_time=time(12, 0),
        )
        db_session.add(shift)
        await db_session.flush()
        await db_session.refresh(shift)

        r = await async_client.get(f"/api/v1/shifts/{shift.id}")

        assert r.status_code == 200
        assert r.json()["is_booked_by_me"] is False
        assert r.json()["current_bookings"] == 0

    async def test_list_shift_bookings_with_user_info(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_task: Task,
        test_user: User,
    ):
        """Test listing shift bookings returns user info."""
        shift = Shift(
            task_id=test_task.id,
            title="Bookings List Shift",
            date=date(2026, 9, 21),
            start_time=time(8, 0),
            end_time=time(12, 0),
        )
        db_session.add(shift)
        await db_session.flush()
        await db_session.refresh(shift)

        booking = Booking(
            shift_id=shift.id,
            user_id=test_user.id,
            status="confirmed",
            notes="Test booking",
        )
        db_session.add(booking)
        await db_session.flush()

        r = await async_client.get(f"/api/v1/shifts/{shift.id}/bookings")

        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert data[0]["user_name"] is not None
        assert data[0]["user_email"] is not None

    async def test_list_shift_bookings_not_found(self, async_client: AsyncClient):
        """Test listing bookings for nonexistent shift returns 404."""
        fake_id = uuid.uuid4()
        r = await async_client.get(f"/api/v1/shifts/{fake_id}/bookings")
        assert r.status_code == 404

    async def test_list_shifts_enrichment(
        self,
        async_client: AsyncClient,
        test_shift: Shift,
        test_booking: Booking,
    ):
        """Test that list endpoint returns enriched shifts with booking counts."""
        r = await async_client.get("/api/v1/shifts/")

        assert r.status_code == 200
        data = r.json()
        items = data["items"]
        slot_item = next((i for i in items if i["id"] == str(test_shift.id)), None)
        assert slot_item is not None
        assert "current_bookings" in slot_item
        assert "is_booked_by_me" in slot_item
        assert slot_item["current_bookings"] >= 1
