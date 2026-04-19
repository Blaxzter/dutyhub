"""Route tests for Reporting endpoints."""

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.event import Event
from app.models.user import User


@pytest.mark.asyncio
class TestReportingRoutes:
    """Test suite for /reporting/ routes (admin only)."""

    async def test_reporting_overview(self, async_client: AsyncClient, as_admin: None):
        """Test the reporting overview endpoint."""
        r = await async_client.get("/api/v1/reporting/overview")

        assert r.status_code == 200
        data = r.json()
        assert "overview" in data
        assert "bookings_trend" in data
        assert "top_volunteers" in data
        assert "category_breakdown" in data
        assert "bookings_by_hour" in data
        assert "task_fill_rates" in data

    async def test_reporting_overview_stats_structure(
        self, async_client: AsyncClient, as_admin: None
    ):
        """Test that the overview stats have the expected fields."""
        r = await async_client.get("/api/v1/reporting/overview")

        assert r.status_code == 200
        overview = r.json()["overview"]
        assert "total_bookings" in overview
        assert "confirmed_bookings" in overview
        assert "cancelled_bookings" in overview
        assert "cancellation_rate" in overview
        assert "total_tasks" in overview
        assert "total_shifts" in overview
        assert "total_shift_capacity" in overview
        assert "filled_shifts" in overview
        assert "fill_rate" in overview
        assert "active_volunteers" in overview
        assert "total_volunteers" in overview

    async def test_reporting_overview_with_booking_data(
        self,
        async_client: AsyncClient,
        as_admin: None,
        test_booking: Booking,
    ):
        """Test that reporting overview includes booking data."""
        r = await async_client.get("/api/v1/reporting/overview")

        assert r.status_code == 200
        overview = r.json()["overview"]
        assert overview["total_bookings"] >= 1
        assert overview["confirmed_bookings"] >= 1

    async def test_reporting_overview_with_date_filter(
        self, async_client: AsyncClient, as_admin: None
    ):
        """Test the reporting overview with date filters."""
        r = await async_client.get(
            "/api/v1/reporting/overview",
            params={"date_from": "2026-01-01", "date_to": "2026-12-31"},
        )

        assert r.status_code == 200
        data = r.json()
        assert "overview" in data

    async def test_reporting_export_csv(
        self, async_client: AsyncClient, as_admin: None
    ):
        """Test the CSV export endpoint."""
        r = await async_client.get("/api/v1/reporting/export")

        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        assert "bookings-report.csv" in r.headers.get("content-disposition", "")

    async def test_reporting_export_csv_has_header_row(
        self, async_client: AsyncClient, as_admin: None
    ):
        """Test that the CSV export has the expected header row."""
        r = await async_client.get("/api/v1/reporting/export")

        assert r.status_code == 200
        lines = r.text.strip().split("\n")
        assert len(lines) >= 1  # at least header
        header = lines[0]
        assert "Booking ID" in header
        assert "Status" in header
        assert "Volunteer Name" in header

    async def test_reporting_export_csv_with_data(
        self,
        async_client: AsyncClient,
        as_admin: None,
        test_booking: Booking,
    ):
        """Test that the CSV export includes booking data."""
        r = await async_client.get("/api/v1/reporting/export")

        assert r.status_code == 200
        lines = r.text.strip().split("\n")
        assert len(lines) >= 2  # header + at least one data row

    async def test_reporting_export_with_date_filter(
        self, async_client: AsyncClient, as_admin: None
    ):
        """Test CSV export with date filters."""
        r = await async_client.get(
            "/api/v1/reporting/export",
            params={"date_from": "2026-01-01", "date_to": "2026-12-31"},
        )

        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]


@pytest.mark.asyncio
class TestReportingTaskManagerRole:
    """Test task_manager scoped access to /reporting/ endpoints."""

    async def test_reporting_overview_accessible_as_task_manager(
        self,
        async_client: AsyncClient,
        as_task_manager: None,
    ):
        """Test that a task_manager can access the reporting overview."""
        r = await async_client.get("/api/v1/reporting/overview")

        assert r.status_code == 200
        data = r.json()
        assert "overview" in data
        assert "task_fill_rates" in data

    async def test_reporting_export_accessible_as_task_manager(
        self,
        async_client: AsyncClient,
        as_task_manager: None,
    ):
        """Test that a task_manager can access the CSV export."""
        r = await async_client.get("/api/v1/reporting/export")

        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]

    async def test_reporting_blocked_for_normal_user(
        self,
        async_client: AsyncClient,
    ):
        """Test that a plain user cannot access reporting endpoints."""
        r = await async_client.get("/api/v1/reporting/overview")

        assert r.status_code == 403

    async def test_reporting_export_blocked_for_normal_user(
        self,
        async_client: AsyncClient,
    ):
        """Test that a plain user cannot access reporting CSV export."""
        r = await async_client.get("/api/v1/reporting/export")

        assert r.status_code == 403

    async def test_task_manager_sees_only_own_tasks_in_stats(
        self,
        async_client: AsyncClient,
        app: FastAPI,
        db_session: AsyncSession,
        test_task_manager_user: User,
        test_event: Event,
    ):
        """Test that task_manager overview stats only count tasks they manage."""
        from datetime import date
        from typing import Any, get_args

        from app.api import deps as deps_module
        from app.models.task import Task as TaskModel

        # Create a task owned by the task_manager user in the managed group
        task = TaskModel(
            name="Manager's Task",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 1),
            status="published",
            created_by_id=test_task_manager_user.id,
            event_id=test_event.id,
        )
        db_session.add(task)
        await db_session.flush()

        # Override deps to return the task_manager user
        user_dep: Any = get_args(deps_module.CurrentUser)[1].dependency
        manager_dep: Any = get_args(deps_module.CurrentManager)[1].dependency

        async def override():
            return test_task_manager_user

        app.dependency_overrides[user_dep] = override
        app.dependency_overrides[manager_dep] = override

        r = await async_client.get("/api/v1/reporting/overview")

        app.dependency_overrides.pop(user_dep, None)
        app.dependency_overrides.pop(manager_dep, None)

        assert r.status_code == 200
        # The task_manager only sees tasks they created or groups they manage
        overview = r.json()["overview"]
        assert "total_tasks" in overview
        # Their own task should be counted
        assert overview["total_tasks"] >= 1
