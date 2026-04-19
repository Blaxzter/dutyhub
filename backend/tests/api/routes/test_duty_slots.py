"""Route tests for DutySlot endpoints."""

import uuid
from datetime import date, time

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.duty_slot import DutySlot
from app.models.task import Task


@pytest.mark.asyncio
class TestDutySlotRoutes:
    """Test suite for /duty-slots/ routes."""

    async def test_list_duty_slots(
        self, async_client: AsyncClient, test_duty_slot: DutySlot
    ):
        """Test listing duty slots."""
        r = await async_client.get("/api/v1/duty-slots/")

        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert any(item["id"] == str(test_duty_slot.id) for item in data["items"])

    async def test_list_duty_slots_filter_by_task(
        self, async_client: AsyncClient, test_duty_slot: DutySlot, test_task: Task
    ):
        """Test filtering duty slots by task_id."""
        r = await async_client.get(
            "/api/v1/duty-slots/", params={"task_id": str(test_task.id)}
        )

        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert all(item["task_id"] == str(test_task.id) for item in data["items"])

    async def test_list_duty_slots_search(
        self, async_client: AsyncClient, test_duty_slot: DutySlot
    ):
        """Test searching duty slots."""
        r = await async_client.get(
            "/api/v1/duty-slots/",
            params={"search": test_duty_slot.title[:5]},
        )

        assert r.status_code == 200
        assert r.json()["total"] >= 1

    async def test_get_duty_slot(
        self, async_client: AsyncClient, test_duty_slot: DutySlot
    ):
        """Test getting a specific duty slot."""
        r = await async_client.get(f"/api/v1/duty-slots/{test_duty_slot.id}")

        assert r.status_code == 200
        assert r.json()["id"] == str(test_duty_slot.id)
        assert "current_bookings" in r.json()
        assert "is_booked_by_me" in r.json()

    async def test_get_duty_slot_not_found(self, async_client: AsyncClient):
        """Test getting a nonexistent duty slot."""
        fake_id = uuid.uuid4()
        r = await async_client.get(f"/api/v1/duty-slots/{fake_id}")
        assert r.status_code == 404

    async def test_create_duty_slot(
        self,
        async_client: AsyncClient,
        as_admin: None,
        test_task: Task,
    ):
        """Test creating a duty slot (admin only)."""
        r = await async_client.post(
            "/api/v1/duty-slots/",
            json={
                "task_id": str(test_task.id),
                "title": "New Shift",
                "date": "2026-06-15",
                "start_time": "09:00:00",
                "end_time": "13:00:00",
                "max_bookings": 2,
            },
        )

        assert r.status_code == 201
        assert r.json()["title"] == "New Shift"
        assert r.json()["max_bookings"] == 2

    async def test_update_duty_slot(
        self,
        async_client: AsyncClient,
        as_admin: None,
        test_duty_slot: DutySlot,
    ):
        """Test updating a duty slot (admin only)."""
        r = await async_client.patch(
            f"/api/v1/duty-slots/{test_duty_slot.id}",
            json={"title": "Updated Shift Title"},
        )

        assert r.status_code == 200
        assert r.json()["title"] == "Updated Shift Title"

    async def test_delete_duty_slot(
        self,
        async_client: AsyncClient,
        as_admin: None,
        db_session: AsyncSession,
        test_task: Task,
    ):
        """Test deleting a duty slot (admin only)."""
        slot = DutySlot(
            task_id=test_task.id,
            title="To Delete",
            date=date(2026, 9, 1),
            start_time=time(10, 0),
            end_time=time(14, 0),
        )
        db_session.add(slot)
        await db_session.flush()
        await db_session.refresh(slot)

        r = await async_client.delete(f"/api/v1/duty-slots/{slot.id}")
        assert r.status_code == 204

    async def test_list_slot_bookings(
        self, async_client: AsyncClient, test_duty_slot: DutySlot
    ):
        """Test listing bookings for a specific slot."""
        r = await async_client.get(f"/api/v1/duty-slots/{test_duty_slot.id}/bookings")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


@pytest.mark.asyncio
class TestDutySlotsTaskManagerRole:
    """Test task_manager role access on /duty-slots/ routes."""

    async def test_create_duty_slot_as_task_manager(
        self,
        async_client: AsyncClient,
        as_task_manager: None,
        test_task: Task,
    ):
        """Test that an task_manager can create duty slots."""
        r = await async_client.post(
            "/api/v1/duty-slots/",
            json={
                "task_id": str(test_task.id),
                "title": "Manager Slot",
                "date": "2026-07-01",
                "start_time": "09:00:00",
                "end_time": "12:00:00",
            },
        )

        assert r.status_code == 201
        assert r.json()["title"] == "Manager Slot"

    async def test_create_duty_slot_as_normal_user_raises_403(
        self,
        async_client: AsyncClient,
        test_task: Task,
    ):
        """Test that a plain user cannot create duty slots."""
        r = await async_client.post(
            "/api/v1/duty-slots/",
            json={
                "task_id": str(test_task.id),
                "title": "Unauthorized Slot",
                "date": "2026-07-01",
                "start_time": "09:00:00",
                "end_time": "12:00:00",
            },
        )

        assert r.status_code == 403

    async def test_update_duty_slot_as_task_manager(
        self,
        async_client: AsyncClient,
        as_task_manager: None,
        test_duty_slot: DutySlot,
    ):
        """Test that an task_manager can update duty slots."""
        r = await async_client.patch(
            f"/api/v1/duty-slots/{test_duty_slot.id}",
            json={"title": "Updated by Manager"},
        )

        assert r.status_code == 200
        assert r.json()["title"] == "Updated by Manager"

    async def test_update_duty_slot_as_normal_user_raises_403(
        self,
        async_client: AsyncClient,
        test_duty_slot: DutySlot,
    ):
        """Test that a plain user cannot update duty slots."""
        r = await async_client.patch(
            f"/api/v1/duty-slots/{test_duty_slot.id}",
            json={"title": "Should Fail"},
        )

        assert r.status_code == 403

    async def test_delete_duty_slot_as_task_manager(
        self,
        async_client: AsyncClient,
        as_task_manager: None,
        db_session: AsyncSession,
        test_task: Task,
    ):
        """Test that an task_manager can delete duty slots."""
        slot = DutySlot(
            task_id=test_task.id,
            title="Manager Delete Me",
            date=date(2026, 9, 1),
            start_time=time(10, 0),
            end_time=time(14, 0),
        )
        db_session.add(slot)
        await db_session.flush()
        await db_session.refresh(slot)

        r = await async_client.delete(f"/api/v1/duty-slots/{slot.id}")
        assert r.status_code == 204

    async def test_delete_duty_slot_as_normal_user_raises_403(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_task: Task,
    ):
        """Test that a plain user cannot delete duty slots."""
        slot = DutySlot(
            task_id=test_task.id,
            title="Should Not Delete",
            date=date(2026, 9, 1),
            start_time=time(10, 0),
            end_time=time(14, 0),
        )
        db_session.add(slot)
        await db_session.flush()
        await db_session.refresh(slot)

        r = await async_client.delete(f"/api/v1/duty-slots/{slot.id}")
        assert r.status_code == 403
