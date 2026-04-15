import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.users import get_current_user_profile, update_user_profile
from app.crud.user import user as crud_user
from app.models.user import User
from app.schemas.users import UserProfileUpdate


@pytest.mark.asyncio
class TestUserRoutes:
    async def test_list_users(
        self, async_client: AsyncClient, test_user: User, as_admin: None
    ):
        response = await async_client.get("/api/v1/users/")
        assert response.status_code == 200
        data = response.json()
        assert any(item["id"] == str(test_user.id) for item in data["items"])
        assert data["counts"]["all"] >= 1

    async def test_list_users_search(
        self, async_client: AsyncClient, test_user: User, as_admin: None
    ):
        assert test_user.email is not None
        q = test_user.email.split("@")[0]
        response = await async_client.get(f"/api/v1/users/?q={q}")
        assert response.status_code == 200
        data = response.json()
        assert data["counts"]["all"] >= 1
        assert all(
            q.lower() in (item["email"] or "").lower()
            or q.lower() in (item["name"] or "").lower()
            for item in data["items"]
        )

    async def test_list_users_status_filter_and_counts(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        as_admin: None,
    ):
        pending = User(
            auth0_sub="auth0|pending_filter_test",
            email="pending-filter@example.com",
            name="Pending Filter",
            is_active=False,
            rejection_reason=None,
        )
        rejected = User(
            auth0_sub="auth0|rejected_filter_test",
            email="rejected-filter@example.com",
            name="Rejected Filter",
            is_active=False,
            rejection_reason="spam",
        )
        db_session.add_all([pending, rejected])
        await db_session.commit()

        r_pending = await async_client.get("/api/v1/users/?status_filter=pending")
        assert r_pending.status_code == 200
        pending_body = r_pending.json()
        pending_ids = {item["id"] for item in pending_body["items"]}
        assert str(pending.id) in pending_ids
        assert str(rejected.id) not in pending_ids
        # counts ignore status_filter — they reflect all statuses
        assert pending_body["counts"]["pending"] >= 1
        assert pending_body["counts"]["rejected"] >= 1
        assert pending_body["counts"]["active"] >= 1
        assert pending_body["counts"]["all"] == (
            pending_body["counts"]["active"]
            + pending_body["counts"]["pending"]
            + pending_body["counts"]["rejected"]
        )

        r_rejected = await async_client.get("/api/v1/users/?status_filter=rejected")
        rejected_ids = {item["id"] for item in r_rejected.json()["items"]}
        assert str(rejected.id) in rejected_ids
        assert str(pending.id) not in rejected_ids

    async def test_list_users_pagination(
        self, async_client: AsyncClient, as_admin: None
    ):
        response = await async_client.get("/api/v1/users/?skip=0&limit=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 1
        assert data["skip"] == 0
        assert data["limit"] == 1

    async def test_get_user(
        self, async_client: AsyncClient, test_user: User, as_admin: None
    ):
        response = await async_client.get(f"/api/v1/users/{test_user.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_user.id)
        assert data["email"] == test_user.email

    async def test_create_user(self, async_client: AsyncClient, as_admin: None):
        payload = {
            "auth0_sub": "auth0|created123",
            "email": "created@example.com",
            "name": "Created User",
            "roles": ["user"],
            "is_active": True,
        }
        response = await async_client.post("/api/v1/users/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["auth0_sub"] == payload["auth0_sub"]
        assert data["email"] == payload["email"]
        assert data["name"] == payload["name"]
        assert data["roles"] == ["user"]

    async def test_update_user(
        self, async_client: AsyncClient, test_user: User, as_admin: None
    ):
        payload = {"name": "Updated User", "email": "updated@example.com"}
        response = await async_client.patch(
            f"/api/v1/users/{test_user.id}",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_user.id)
        assert data["name"] == "Updated User"
        assert data["email"] == "updated@example.com"

    async def test_delete_user(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        as_admin: None,
    ):
        response = await async_client.delete(f"/api/v1/users/{test_user.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_user.id)

        deleted = await crud_user.get(db_session, id=test_user.id)
        assert deleted is None

    async def test_get_auth0_management_url(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/users/auth0-management-url")
        assert response.status_code == 200
        data = response.json()
        assert "management_url" in data
        assert "note" in data


@pytest.mark.asyncio
class TestUserRouteHelpers:
    async def test_get_current_user_profile(
        self,
        db_session: AsyncSession,
        test_user: User,
        mock_auth0_claims: dict[str, str],
    ):
        profile = await get_current_user_profile(
            user=test_user,
            profile_init=None,
            session=db_session,
        )
        assert profile.sub == mock_auth0_claims["sub"]
        assert profile.email == mock_auth0_claims["email"]
        assert profile.roles == test_user.roles
        assert profile.is_admin is False

    async def test_update_user_profile(
        self,
        monkeypatch: pytest.MonkeyPatch,
        db_session: AsyncSession,
        test_user: User,
    ):
        called = {}

        async def fake_update_auth0_user(user_id: str, update_data: UserProfileUpdate):
            called["user_id"] = user_id
            called["update_data"] = update_data
            return True

        monkeypatch.setattr(
            "app.api.routes.users.update_auth0_user",
            fake_update_auth0_user,
        )

        update = UserProfileUpdate(name="Updated Name", nickname="updated")  # type: ignore[reportCallIssue]
        profile = await update_user_profile(
            user_update=update,
            current_user=test_user,
            session=db_session,
        )

        assert profile.name == "Updated Name"
        assert profile.nickname == "updated"
        assert profile.roles == test_user.roles
