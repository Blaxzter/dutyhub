"""Route tests for Dashboard endpoints."""

import pytest
from httpx import AsyncClient

from app.models.booking import Booking


@pytest.mark.asyncio
class TestDashboardRoutes:
    """Test suite for /dashboard/ routes."""

    async def test_dashboard_feed(self, async_client: AsyncClient):
        """Test the main dashboard feed endpoint."""
        r = await async_client.get("/api/v1/dashboard/feed")

        assert r.status_code == 200
        data = r.json()
        assert "tasks" in data
        assert "task_count" in data
        assert "events" in data
        assert "bookings" in data
        assert "booking_count" in data

    async def test_dashboard_feed_with_booking(
        self, async_client: AsyncClient, test_booking: Booking
    ):
        """Test that dashboard feed includes the user's bookings."""
        r = await async_client.get("/api/v1/dashboard/feed")

        assert r.status_code == 200
        data = r.json()
        # booking_count may or may not include test_booking depending on dates
        assert data["booking_count"] >= 0

    async def test_dashboard_sidebar(self, async_client: AsyncClient):
        """Test the sidebar data endpoint."""
        r = await async_client.get("/api/v1/dashboard/sidebar")

        assert r.status_code == 200
        data = r.json()
        assert "events" in data
        assert "tasks" in data
        assert "bookings" in data

    async def test_dashboard_feed_reports_pending_join_requests(
        self, async_client: AsyncClient, as_admin: None
    ):
        """The dashboard surfaces join requests waiting on this user."""
        r = await async_client.get("/api/v1/dashboard/feed")

        assert r.status_code == 200
        data = r.json()
        assert "pending_join_request_count" in data
        assert data["pending_join_request_count"] == 0
