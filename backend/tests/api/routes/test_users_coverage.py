"""Coverage gap tests for User endpoints (own profile, delete, export with data)."""

from datetime import date, time
from typing import Any, get_args

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps as deps_module
from app.models.booking import Booking
from app.models.shift import Shift
from app.models.task import Task
from app.models.user import User
from app.models.user_availability import UserAvailability


@pytest.mark.asyncio
class TestGetOwnProfile:
    """``GET /users/me`` — the one endpoint a suspended account may still use.

    It used to be a POST carrying the identity provider's ID token, which the
    route wrote onto the row before answering. Registration supplies those
    fields now, so nothing is upserted and the verb finally matches the work.

    The dependency is ``AnyUser`` rather than ``CurrentUser`` on purpose, and
    that is what these tests pin down: the profile response is how the UI knows
    to explain *why* everything else is being refused, so an account that
    moderation switched off must still be able to read it.
    """

    async def test_returns_the_callers_own_row(
        self,
        async_client: AsyncClient,
        test_user: User,
    ):
        """Test that the profile is served from the database, not from a token."""
        r = await async_client.get("/api/v1/users/me")

        assert r.status_code == 200
        data = r.json()
        assert data["id"] == str(test_user.id)
        assert data["sub"] == test_user.subject
        assert data["email"] == test_user.email

    async def test_suspended_account_can_still_read_its_own_profile(
        self,
        app: FastAPI,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_inactive_user: User,
    ):
        """Test that ``AnyUser`` lets a suspended account see why it is blocked."""
        test_inactive_user.rejection_reason = "Suspended pending review"
        db_session.add(test_inactive_user)
        await db_session.flush()

        dep: Any = get_args(deps_module.AnyUser)[1].dependency

        async def override_any_user():
            return test_inactive_user

        app.dependency_overrides[dep] = override_any_user
        try:
            r = await async_client.get("/api/v1/users/me")

            assert r.status_code == 200
            data = r.json()
            assert data["is_active"] is False
            assert data["rejection_reason"] == "Suspended pending review"
        finally:
            app.dependency_overrides.pop(dep, None)


@pytest.mark.asyncio
class TestDeleteCurrentUser:
    """Test DELETE /me endpoint."""

    async def test_delete_current_user(
        self,
        app: FastAPI,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test deleting the current user's account."""
        # Create a user to delete (don't delete the fixture user)
        deletable_user = User(
            subject="local|deletable_user",
            email="deletable@example.com",
            name="Deletable User",
            is_active=True,
        )
        db_session.add(deletable_user)
        await db_session.flush()
        await db_session.refresh(deletable_user)

        dep: Any = get_args(deps_module.AnyUser)[1].dependency

        async def override_any_user():
            return deletable_user

        app.dependency_overrides[dep] = override_any_user
        try:
            r = await async_client.delete("/api/v1/users/me")
            assert r.status_code == 204
        finally:
            app.dependency_overrides.pop(dep, None)


@pytest.mark.asyncio
class TestUserProfileUpdate:
    """Test PATCH /me endpoint."""

    async def test_update_profile_nickname(self, async_client: AsyncClient):
        """Test updating user nickname (avatar updates go through /me/avatar)."""
        r = await async_client.patch(
            "/api/v1/users/me",
            json={"nickname": "Updated"},
        )

        assert r.status_code == 200

    async def test_update_profile_language(self, async_client: AsyncClient):
        """Test updating user preferred language."""
        r = await async_client.patch(
            "/api/v1/users/me",
            json={"preferred_language": "de"},
        )

        assert r.status_code == 200

    async def test_update_profile_phone(self, async_client: AsyncClient):
        """Test updating user phone number."""
        r = await async_client.patch(
            "/api/v1/users/me",
            json={"phone_number": "+49123456789"},
        )

        assert r.status_code == 200


@pytest.mark.asyncio
class TestExportWithData:
    """Test GET /me/export with actual data in the database."""

    async def test_export_with_bookings(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_task: Task,
    ):
        """Test export includes user's bookings."""
        shift = Shift(
            task_id=test_task.id,
            title="Export Test Shift",
            date=date(2026, 6, 1),
            start_time=time(8, 0),
            end_time=time(12, 0),
        )
        db_session.add(shift)
        await db_session.flush()

        booking = Booking(
            shift_id=shift.id,
            user_id=test_user.id,
            status="confirmed",
            notes="Export test",
        )
        db_session.add(booking)
        await db_session.flush()

        r = await async_client.get("/api/v1/users/me/export")

        assert r.status_code == 200
        data = r.json()
        assert len(data["bookings"]) >= 1
        assert any(b["notes"] == "Export test" for b in data["bookings"])

    async def test_export_with_availabilities(
        self,
        async_client: AsyncClient,
        test_user_availability_with_dates: UserAvailability,
    ):
        """Test export includes the user's stated availability and its dates.

        The availability block is assembled by a nested loop rather than a
        single query, so an export written for a user who happens to have none
        never runs it. GDPR exports are the one response where a silently empty
        section is a compliance problem rather than a cosmetic one.
        """
        r = await async_client.get("/api/v1/users/me/export")

        assert r.status_code == 200
        availabilities = r.json()["availabilities"]
        assert len(availabilities) == 1
        assert availabilities[0]["availability_type"] == "specific_dates"
        assert availabilities[0]["notes"] == "Only free Wednesday and Thursday"
        assert sorted(d["date"] for d in availabilities[0]["dates"]) == [
            "2026-06-10",
            "2026-06-11",
        ]


@pytest.mark.asyncio
class TestAdminUserManagement:
    """Admin suspension controls. Signup is open, so these are moderation."""

    async def test_admin_approve_user_triggers_notification(
        self,
        async_client: AsyncClient,
        as_admin: None,
        db_session: AsyncSession,
    ):
        """Reinstating a suspended account flips is_active back on."""
        user = User(
            subject="local|approve_notif_test",
            email="approve_notif@example.com",
            name="Approve Notif User",
            is_active=False,
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)

        r = await async_client.patch(
            f"/api/v1/users/{user.id}",
            json={"is_active": True},
        )

        assert r.status_code == 200
        assert r.json()["is_active"] is True

    async def test_admin_reject_user_triggers_notification(
        self,
        async_client: AsyncClient,
        as_admin: None,
        db_session: AsyncSession,
    ):
        """Recording a suspension reason is persisted on the account."""
        user = User(
            subject="local|reject_notif_test",
            email="reject_notif@example.com",
            name="Reject Notif User",
            is_active=False,
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)

        r = await async_client.patch(
            f"/api/v1/users/{user.id}",
            json={"rejection_reason": "Not eligible for this role"},
        )

        assert r.status_code == 200
        assert r.json()["rejection_reason"] == "Not eligible for this role"

    async def test_admin_delete_user(
        self,
        async_client: AsyncClient,
        as_admin: None,
        db_session: AsyncSession,
    ):
        """Test admin deleting a user by ID."""
        user = User(
            subject="local|admin_delete_target",
            email="admin_delete@example.com",
            name="Admin Delete Target",
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)

        r = await async_client.delete(f"/api/v1/users/{user.id}")

        assert r.status_code == 200
        assert r.json()["id"] == str(user.id)
