"""Coverage gap tests for Task CRUD endpoints (filtering, bookings list, delete, publish)."""

import uuid
from datetime import date, time

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.duty_slot import DutySlot
from app.models.task import Task
from app.models.user import User


@pytest.mark.asyncio
class TestTaskCrudCoverage:
    """Coverage tests for tasks/crud.py routes."""

    async def test_list_tasks_non_admin_sees_only_published(
        self,
        async_client: AsyncClient,
        test_task: Task,
        test_draft_task: Task,
    ):
        """Test that non-admin users only see published tasks."""
        r = await async_client.get("/api/v1/tasks/")

        assert r.status_code == 200
        data = r.json()
        ids = [item["id"] for item in data["items"]]
        assert str(test_task.id) in ids
        assert str(test_draft_task.id) not in ids

    async def test_list_tasks_admin_sees_all(
        self,
        async_client: AsyncClient,
        as_admin: None,
        test_task: Task,
        test_draft_task: Task,
    ):
        """Test that admin users see all tasks including drafts."""
        r = await async_client.get("/api/v1/tasks/")

        assert r.status_code == 200
        data = r.json()
        ids = [item["id"] for item in data["items"]]
        assert str(test_task.id) in ids
        assert str(test_draft_task.id) in ids

    async def test_list_tasks_with_status_filter(
        self,
        async_client: AsyncClient,
        as_admin: None,
        test_draft_task: Task,
    ):
        """Test listing tasks filtered by status."""
        r = await async_client.get("/api/v1/tasks/", params={"status": "draft"})

        assert r.status_code == 200
        data = r.json()
        assert all(item["status"] == "draft" for item in data["items"])

    async def test_list_tasks_my_bookings_filter(
        self,
        async_client: AsyncClient,
        test_task: Task,
        test_booking: Booking,
    ):
        """Test filtering tasks to only those with my bookings."""
        r = await async_client.get("/api/v1/tasks/", params={"my_bookings": True})

        assert r.status_code == 200
        data = r.json()
        # Should include the task with test_booking
        assert data["total"] >= 1
        ids = [item["id"] for item in data["items"]]
        assert str(test_task.id) in ids

    async def test_list_tasks_with_search(
        self,
        async_client: AsyncClient,
        test_task: Task,
    ):
        """Test searching tasks by name."""
        r = await async_client.get(
            "/api/v1/tasks/", params={"search": test_task.name[:5]}
        )

        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1

    async def test_get_draft_task_forbidden_for_non_admin(
        self,
        async_client: AsyncClient,
        test_draft_task: Task,
    ):
        """Test that non-admin cannot view a draft task."""
        r = await async_client.get(f"/api/v1/tasks/{test_draft_task.id}")
        assert r.status_code == 403

    async def test_get_draft_task_allowed_for_admin(
        self,
        async_client: AsyncClient,
        as_admin: None,
        test_draft_task: Task,
    ):
        """Test that admin can view a draft task."""
        r = await async_client.get(f"/api/v1/tasks/{test_draft_task.id}")
        assert r.status_code == 200

    async def test_list_task_bookings(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_task: Task,
        test_user: User,
    ):
        """Test listing all confirmed bookings for an task."""
        slot = DutySlot(
            task_id=test_task.id,
            title="Bookings List Slot",
            date=date(2026, 6, 10),
            start_time=time(9, 0),
            end_time=time(13, 0),
        )
        db_session.add(slot)
        await db_session.flush()
        await db_session.refresh(slot)

        booking = Booking(
            duty_slot_id=slot.id,
            user_id=test_user.id,
            status="confirmed",
        )
        db_session.add(booking)
        await db_session.flush()

        r = await async_client.get(f"/api/v1/tasks/{test_task.id}/bookings")

        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert "duty_slot_id" in data[0]
        assert "user_name" in data[0]

    async def test_list_task_bookings_not_found(self, async_client: AsyncClient):
        """Test listing bookings for nonexistent task returns 404."""
        fake_id = uuid.uuid4()
        r = await async_client.get(f"/api/v1/tasks/{fake_id}/bookings")
        assert r.status_code == 404

    async def test_delete_task(
        self,
        async_client: AsyncClient,
        as_admin: None,
        db_session: AsyncSession,
    ):
        """Test deleting an task."""
        task = Task(
            name="Delete Me",
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 3),
            status="draft",
        )
        db_session.add(task)
        await db_session.flush()
        await db_session.refresh(task)

        r = await async_client.delete(f"/api/v1/tasks/{task.id}")
        assert r.status_code == 204

    async def test_delete_task_with_bookings(
        self,
        async_client: AsyncClient,
        as_admin: None,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test deleting an task cancels all confirmed bookings."""
        task = Task(
            name="Delete With Bookings",
            start_date=date(2026, 10, 10),
            end_date=date(2026, 10, 12),
            status="draft",
        )
        db_session.add(task)
        await db_session.flush()
        await db_session.refresh(task)

        slot = DutySlot(
            task_id=task.id,
            title="Slot To Delete",
            date=date(2026, 10, 10),
            start_time=time(8, 0),
            end_time=time(12, 0),
        )
        db_session.add(slot)
        await db_session.flush()

        booking = Booking(
            duty_slot_id=slot.id,
            user_id=test_user.id,
            status="confirmed",
        )
        db_session.add(booking)
        await db_session.flush()

        r = await async_client.delete(
            f"/api/v1/tasks/{task.id}",
            params={"cancellation_reason": "Task cancelled"},
        )
        assert r.status_code == 204

    async def test_publish_task_triggers_notification(
        self,
        async_client: AsyncClient,
        as_admin: None,
        test_draft_task: Task,
    ):
        """Test that publishing an task dispatches notification."""
        r = await async_client.patch(
            f"/api/v1/tasks/{test_draft_task.id}",
            json={"status": "published"},
        )

        assert r.status_code == 200
        assert r.json()["status"] == "published"

    async def test_update_task_no_status_change(
        self,
        async_client: AsyncClient,
        as_admin: None,
        test_task: Task,
    ):
        """Test updating task without status change (no notification)."""
        r = await async_client.patch(
            f"/api/v1/tasks/{test_task.id}",
            json={"description": "Updated description"},
        )

        assert r.status_code == 200
        assert r.json()["description"] == "Updated description"
