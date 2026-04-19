"""Route tests for Task Feed endpoints."""

import pytest
from httpx import AsyncClient

from app.models.booking import Booking
from app.models.duty_slot import DutySlot
from app.models.task import Task


@pytest.mark.asyncio
class TestTaskFeedRoutes:
    """Test suite for /tasks/feed routes."""

    async def test_task_feed_list_view(
        self, async_client: AsyncClient, test_task: Task, test_duty_slot: DutySlot
    ):
        """Test the task feed in list view mode."""
        r = await async_client.get("/api/v1/tasks/feed", params={"view": "list"})

        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data

    async def test_task_feed_cards_view(
        self, async_client: AsyncClient, test_task: Task
    ):
        """Test the task feed in cards view mode."""
        r = await async_client.get("/api/v1/tasks/feed", params={"view": "cards"})

        assert r.status_code == 200
        data = r.json()
        assert "items" in data

    async def test_task_feed_calendar_view(
        self, async_client: AsyncClient, test_task: Task
    ):
        """Test the task feed in calendar view mode."""
        r = await async_client.get(
            "/api/v1/tasks/feed",
            params={
                "view": "calendar",
                "date_from": "2026-05-01",
                "date_to": "2026-05-31",
            },
        )

        assert r.status_code == 200
        data = r.json()
        assert "items" in data

    async def test_task_feed_with_search(
        self, async_client: AsyncClient, test_task: Task
    ):
        """Test the task feed with a search query."""
        r = await async_client.get(
            "/api/v1/tasks/feed",
            params={"search": test_task.name[:5]},
        )

        assert r.status_code == 200

    async def test_task_feed_my_bookings_filter(
        self, async_client: AsyncClient, test_booking: Booking
    ):
        """Test the my_bookings filter in task feed."""
        r = await async_client.get("/api/v1/tasks/feed", params={"my_bookings": True})

        assert r.status_code == 200

    async def test_task_feed_pagination(self, async_client: AsyncClient):
        """Test task feed pagination parameters."""
        r = await async_client.get(
            "/api/v1/tasks/feed",
            params={"skip": 0, "limit": 5},
        )

        assert r.status_code == 200
        data = r.json()
        assert data["skip"] == 0
        assert data["limit"] == 5

    async def test_task_feed_empty(self, async_client: AsyncClient):
        """Test task feed when no tasks match."""
        r = await async_client.get(
            "/api/v1/tasks/feed",
            params={"search": "zzz_nonexistent_zzz"},
        )

        assert r.status_code == 200
        assert r.json()["total"] == 0
        assert r.json()["items"] == []

    async def test_task_feed_focus_mode_first_available(
        self, async_client: AsyncClient, test_task: Task, test_duty_slot: DutySlot
    ):
        """Test the task feed with first_available focus mode."""
        r = await async_client.get(
            "/api/v1/tasks/feed",
            params={"view": "list", "focus_mode": "first_available"},
        )

        assert r.status_code == 200

    async def test_task_active_dates(
        self, async_client: AsyncClient, test_task: Task, test_duty_slot: DutySlot
    ):
        """Test the active dates endpoint."""
        r = await async_client.get(
            "/api/v1/tasks/active-dates",
            params={"date_from": "2026-01-01", "date_to": "2026-12-31"},
        )

        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_task_slot_window(
        self, async_client: AsyncClient, test_task: Task, test_duty_slot: DutySlot
    ):
        """Test the slot window endpoint for a specific task."""
        r = await async_client.get(
            f"/api/v1/tasks/{test_task.id}/slot-window",
            params={"start_date": "2026-05-01", "days": 7},
        )

        assert r.status_code == 200
        data = r.json()
        assert "slots" in data
        assert "start_date" in data
        assert "days" in data
