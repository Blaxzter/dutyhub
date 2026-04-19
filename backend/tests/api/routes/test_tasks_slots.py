"""Route tests for Task Shifts (generation/regeneration) endpoints."""

import pytest
from httpx import AsyncClient

from app.models.task import Task


@pytest.mark.asyncio
class TestTaskShiftsRoutes:
    """Test suite for task shift generation routes (admin only)."""

    async def test_create_task_with_shifts(
        self, async_client: AsyncClient, as_admin: None
    ):
        """Test creating a task with auto-generated shifts."""
        r = await async_client.post(
            "/api/v1/tasks/with-shifts",
            json={
                "name": "Generated Task",
                "description": "Auto-generated shifts",
                "start_date": "2026-07-01",
                "end_date": "2026-07-03",
                "schedule": {
                    "default_start_time": "09:00:00",
                    "default_end_time": "17:00:00",
                    "shift_duration_minutes": 240,
                    "people_per_shift": 2,
                    "overrides": [],
                },
            },
        )

        assert r.status_code == 201
        data = r.json()
        assert data["task"]["name"] == "Generated Task"
        assert data["shifts_created"] >= 1

    async def test_create_task_with_shifts_and_group(
        self, async_client: AsyncClient, as_admin: None
    ):
        """Test creating a task with a new event."""
        r = await async_client.post(
            "/api/v1/tasks/with-shifts",
            json={
                "name": "Grouped Task",
                "start_date": "2026-08-01",
                "end_date": "2026-08-02",
                "new_event": {
                    "name": "New Group",
                    "start_date": "2026-08-01",
                    "end_date": "2026-08-31",
                },
                "schedule": {
                    "default_start_time": "10:00:00",
                    "default_end_time": "14:00:00",
                    "shift_duration_minutes": 120,
                    "people_per_shift": 1,
                    "overrides": [],
                },
            },
        )

        assert r.status_code == 201
        data = r.json()
        assert data["event"] is not None
        assert data["event"]["name"] == "New Group"

    async def test_regenerate_shifts_dry_run(
        self, async_client: AsyncClient, as_admin: None, test_task: Task
    ):
        """Test regenerating shifts in dry run mode."""
        r = await async_client.post(
            f"/api/v1/tasks/{test_task.id}/regenerate-shifts",
            params={"dry_run": True},
            json={
                "schedule": {
                    "default_start_time": "08:00:00",
                    "default_end_time": "16:00:00",
                    "shift_duration_minutes": 240,
                    "people_per_shift": 1,
                    "overrides": [],
                },
            },
        )

        assert r.status_code == 200
        data = r.json()
        assert "shifts_added" in data
        assert "shifts_removed" in data
        assert "shifts_kept" in data
        assert "affected_bookings" in data

    async def test_regenerate_shifts(
        self, async_client: AsyncClient, as_admin: None, test_task: Task
    ):
        """Test actually regenerating shifts."""
        r = await async_client.post(
            f"/api/v1/tasks/{test_task.id}/regenerate-shifts",
            json={
                "schedule": {
                    "default_start_time": "09:00:00",
                    "default_end_time": "17:00:00",
                    "shift_duration_minutes": 480,
                    "people_per_shift": 3,
                    "overrides": [],
                },
            },
        )

        assert r.status_code == 200
        data = r.json()
        assert data["task"]["id"] == str(test_task.id)

    async def test_add_shifts_to_task(
        self, async_client: AsyncClient, as_admin: None, test_task: Task
    ):
        """Test adding a new batch of shifts to an existing task."""
        r = await async_client.post(
            f"/api/v1/tasks/{test_task.id}/add-shifts",
            json={
                "start_date": "2026-06-15",
                "end_date": "2026-06-17",
                "schedule": {
                    "default_start_time": "10:00:00",
                    "default_end_time": "14:00:00",
                    "shift_duration_minutes": 120,
                    "people_per_shift": 2,
                    "overrides": [],
                },
            },
        )

        assert r.status_code == 201
        data = r.json()
        assert data["shifts_added"] >= 1

    async def test_list_batches(self, async_client: AsyncClient, test_task: Task):
        """Test listing shift batches for a task."""
        r = await async_client.get(f"/api/v1/tasks/{test_task.id}/batches")

        assert r.status_code == 200
        assert isinstance(r.json(), list)
