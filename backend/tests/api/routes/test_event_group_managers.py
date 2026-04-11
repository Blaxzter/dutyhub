"""Route tests for EventGroup manager assignment endpoints."""

import pytest
from httpx import AsyncClient

from app.models.event_group import EventGroup
from app.models.user import User


@pytest.mark.asyncio
class TestEventGroupManagerEndpoints:
    """Test suite for /event-groups/{id}/managers endpoints."""

    async def test_list_managers_as_admin(
        self,
        async_client: AsyncClient,
        test_event_group: EventGroup,
        as_admin: None,
    ):
        """Test that an admin can list managers for a group (empty initially)."""
        r = await async_client.get(
            f"/api/v1/event-groups/{test_event_group.id}/managers"
        )

        assert r.status_code == 200
        assert r.json() == []

    async def test_list_managers_as_event_manager(
        self,
        async_client: AsyncClient,
        test_event_group: EventGroup,
        as_event_manager: None,
    ):
        """Test that an event_manager can list managers for a group."""
        r = await async_client.get(
            f"/api/v1/event-groups/{test_event_group.id}/managers"
        )

        assert r.status_code == 200

    async def test_list_managers_blocked_for_normal_user(
        self,
        async_client: AsyncClient,
        test_event_group: EventGroup,
    ):
        """Test that a plain user cannot list managers."""
        r = await async_client.get(
            f"/api/v1/event-groups/{test_event_group.id}/managers"
        )

        assert r.status_code == 403

    async def test_assign_manager_as_admin(
        self,
        async_client: AsyncClient,
        test_event_group: EventGroup,
        test_event_manager_user: User,
        as_admin: None,
    ):
        """Test that an admin can assign a user as group manager."""
        r = await async_client.post(
            f"/api/v1/event-groups/{test_event_group.id}/managers/{test_event_manager_user.id}"
        )

        assert r.status_code == 201
        data = r.json()
        assert data["id"] == str(test_event_manager_user.id)
        assert data["email"] == test_event_manager_user.email

    async def test_assign_manager_idempotent(
        self,
        async_client: AsyncClient,
        test_event_group: EventGroup,
        test_event_manager_user: User,
        as_admin: None,
    ):
        """Test that assigning the same user twice is idempotent (returns 201 both times)."""
        r1 = await async_client.post(
            f"/api/v1/event-groups/{test_event_group.id}/managers/{test_event_manager_user.id}"
        )
        r2 = await async_client.post(
            f"/api/v1/event-groups/{test_event_group.id}/managers/{test_event_manager_user.id}"
        )

        assert r1.status_code == 201
        assert r2.status_code == 201

    async def test_assign_manager_as_event_manager_raises_403(
        self,
        async_client: AsyncClient,
        test_event_group: EventGroup,
        test_user: User,
        as_event_manager: None,
    ):
        """Test that an event_manager cannot assign group managers (admin only)."""
        r = await async_client.post(
            f"/api/v1/event-groups/{test_event_group.id}/managers/{test_user.id}"
        )

        assert r.status_code == 403

    async def test_assign_manager_as_normal_user_raises_403(
        self,
        async_client: AsyncClient,
        test_event_group: EventGroup,
        test_user: User,
    ):
        """Test that a plain user cannot assign group managers."""
        r = await async_client.post(
            f"/api/v1/event-groups/{test_event_group.id}/managers/{test_user.id}"
        )

        assert r.status_code == 403

    async def test_remove_manager_as_admin(
        self,
        async_client: AsyncClient,
        test_event_group: EventGroup,
        test_event_manager_user: User,
        as_admin: None,
    ):
        """Test that an admin can remove a group manager assignment."""
        # First assign
        await async_client.post(
            f"/api/v1/event-groups/{test_event_group.id}/managers/{test_event_manager_user.id}"
        )

        # Then remove
        r = await async_client.delete(
            f"/api/v1/event-groups/{test_event_group.id}/managers/{test_event_manager_user.id}"
        )

        assert r.status_code == 204

    async def test_remove_manager_as_event_manager_raises_403(
        self,
        async_client: AsyncClient,
        test_event_group: EventGroup,
        test_user: User,
        as_event_manager: None,
    ):
        """Test that an event_manager cannot remove group manager assignments."""
        r = await async_client.delete(
            f"/api/v1/event-groups/{test_event_group.id}/managers/{test_user.id}"
        )

        assert r.status_code == 403

    async def test_assigned_manager_appears_in_list(
        self,
        async_client: AsyncClient,
        test_event_group: EventGroup,
        test_event_manager_user: User,
        as_admin: None,
    ):
        """Test that after assignment the user appears in the managers list."""
        await async_client.post(
            f"/api/v1/event-groups/{test_event_group.id}/managers/{test_event_manager_user.id}"
        )

        r = await async_client.get(
            f"/api/v1/event-groups/{test_event_group.id}/managers"
        )

        assert r.status_code == 200
        ids = [m["id"] for m in r.json()]
        assert str(test_event_manager_user.id) in ids

    async def test_removed_manager_disappears_from_list(
        self,
        async_client: AsyncClient,
        test_event_group: EventGroup,
        test_event_manager_user: User,
        as_admin: None,
    ):
        """Test that after removal the user no longer appears in the managers list."""
        await async_client.post(
            f"/api/v1/event-groups/{test_event_group.id}/managers/{test_event_manager_user.id}"
        )
        await async_client.delete(
            f"/api/v1/event-groups/{test_event_group.id}/managers/{test_event_manager_user.id}"
        )

        r = await async_client.get(
            f"/api/v1/event-groups/{test_event_group.id}/managers"
        )

        assert r.status_code == 200
        ids = [m["id"] for m in r.json()]
        assert str(test_event_manager_user.id) not in ids

    async def test_assign_nonexistent_user_raises_404(
        self,
        async_client: AsyncClient,
        test_event_group: EventGroup,
        as_admin: None,
    ):
        """Test that assigning a non-existent user raises 404."""
        import uuid

        r = await async_client.post(
            f"/api/v1/event-groups/{test_event_group.id}/managers/{uuid.uuid4()}"
        )

        assert r.status_code == 404

    async def test_assign_to_nonexistent_group_raises_404(
        self,
        async_client: AsyncClient,
        test_event_manager_user: User,
        as_admin: None,
    ):
        """Test that assigning to a non-existent group raises 404."""
        import uuid

        r = await async_client.post(
            f"/api/v1/event-groups/{uuid.uuid4()}/managers/{test_event_manager_user.id}"
        )

        assert r.status_code == 404
