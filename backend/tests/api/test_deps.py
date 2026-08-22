# pyright: reportPrivateUsage=false
"""Unit tests for authentication dependencies."""

from collections.abc import Callable, Coroutine
from contextlib import AsyncExitStack
from types import SimpleNamespace
from typing import Any, cast, get_args
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps as deps_module
from app.api.deps import (
    _get_user_from_query_token,
    current_user,
    get_db,
    get_or_create_user,
)
from app.core.config import settings
from app.crud.user import user as crud_user
from app.models.user import User


@pytest.mark.asyncio
class TestGetOrCreateUser:
    """Test suite for get_or_create_user helper function."""

    async def test_get_existing_user(
        self,
        db_session: AsyncSession,
        test_user: User,
        mock_auth0_claims: dict[str, Any],
    ):
        """Test getting an existing user."""
        user = await get_or_create_user(db_session, mock_auth0_claims)

        assert user.id == test_user.id
        assert user.auth0_sub == test_user.auth0_sub
        assert user.email == test_user.email

    async def test_create_new_user_from_claims(
        self,
        db_session: AsyncSession,
        mock_auth0_new_user_claims: dict[str, Any],
    ):
        """Test creating a new user from Auth0 claims."""
        user = await get_or_create_user(db_session, mock_auth0_new_user_claims)

        assert user.auth0_sub == "auth0|newuser456"
        assert user.email == "newuser@example.com"
        assert user.name == "New User"
        assert user.is_active is True  # signup is open; membership is the gate
        assert user.roles == []

        # Verify user was persisted
        persisted_user = await crud_user.get_by_auth0_sub(
            db_session, auth0_sub="auth0|newuser456"
        )
        assert persisted_user is not None
        assert persisted_user.id == user.id

    async def test_create_new_user_with_profile_data(
        self,
        db_session: AsyncSession,
        mock_auth0_new_user_claims: dict[str, Any],
    ):
        """Test creating a new user with profile data from frontend."""
        profile_data = {
            "email": "frontend@example.com",
            "name": "Frontend User",
        }

        user = await get_or_create_user(
            db_session, mock_auth0_new_user_claims, profile_data
        )

        # Should use profile_data over claims
        assert user.email == "frontend@example.com"
        assert user.name == "Frontend User"

    async def test_create_new_user_with_nickname(
        self,
        db_session: AsyncSession,
    ):
        """Test creating a new user using nickname when name is absent."""
        claims = {
            "sub": "auth0|nickname123",
            "email": "nickname@example.com",
            "nickname": "nicknameuser",
        }

        user = await get_or_create_user(db_session, claims)

        assert user.name == "nicknameuser"

    async def test_missing_sub_raises_error(
        self,
        db_session: AsyncSession,
        mock_auth0_claims_no_sub: dict[str, Any],
    ):
        """Test that missing 'sub' in claims raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            await get_or_create_user(db_session, mock_auth0_claims_no_sub)

        assert exc_info.value.status_code == 401
        assert "Invalid authentication payload" in str(exc_info.value.detail)


@pytest.mark.asyncio
class TestCurrentUserDependency:
    """Test suite for current_user dependency."""

    async def test_current_user_success(
        self,
        db_session: AsyncSession,
        test_user: User,
        mock_auth0_claims: dict[str, Any],
        mock_request: MagicMock,
    ):
        """Test successful user authentication."""
        # Create the dependency function
        dependency = current_user()

        # Call the dependency with mocked claims
        user = await dependency(
            request=mock_request, session=db_session, claims=mock_auth0_claims
        )

        assert user.id == test_user.id
        assert user.is_active is True

    async def test_current_user_inactive_raises_error(
        self,
        db_session: AsyncSession,
        test_inactive_user: User,
        mock_request: MagicMock,
    ):
        """Test that inactive user raises 403 error."""
        claims = {
            "sub": test_inactive_user.auth0_sub,
            "email": test_inactive_user.email,
        }

        dependency = current_user()

        with pytest.raises(HTTPException) as exc_info:
            await dependency(request=mock_request, session=db_session, claims=claims)

        assert exc_info.value.status_code == 403
        assert "Inactive user" in str(exc_info.value.detail)

    async def test_current_user_with_role_check_success(
        self,
        db_session: AsyncSession,
        test_admin_user: User,
        mock_request: MagicMock,
    ):
        """Test role-based access control with valid role."""
        claims = {
            "sub": test_admin_user.auth0_sub,
            "email": test_admin_user.email,
        }

        # Require admin role
        dependency = current_user(required_roles="admin")

        user = await dependency(request=mock_request, session=db_session, claims=claims)

        assert user.id == test_admin_user.id
        assert "admin" in user.roles

    async def test_current_user_with_role_check_failure(
        self,
        db_session: AsyncSession,
        test_user: User,
        mock_request: MagicMock,
    ):
        """Test role-based access control with missing role."""
        claims = {
            "sub": test_user.auth0_sub,
            "email": test_user.email,
        }

        # Require admin role (test_user doesn't have it)
        dependency = current_user(required_roles="admin")

        with pytest.raises(HTTPException) as exc_info:
            await dependency(request=mock_request, session=db_session, claims=claims)

        assert exc_info.value.status_code == 403
        assert "Not enough permissions" in str(exc_info.value.detail)

    async def test_current_user_with_multiple_roles(
        self,
        db_session: AsyncSession,
        mock_request: MagicMock,
    ):
        """Test role check with multiple required roles."""
        # Create user with multiple roles
        user = User(
            auth0_sub="auth0|multirole123",
            email="multirole@example.com",
            name="Multi Role User",
            roles=["admin", "moderator"],
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)

        claims = {
            "sub": user.auth0_sub,
            "email": user.email,
        }

        # Require admin role (user has it)
        dependency = current_user(required_roles=["admin", "moderator"])

        result_user = await dependency(
            request=mock_request, session=db_session, claims=claims
        )

        assert result_user.id == user.id

    async def test_current_user_with_multiple_roles_missing_one(
        self,
        db_session: AsyncSession,
        test_admin_user: User,
        mock_request: MagicMock,
    ):
        """Test role check when user is missing one of the required roles."""
        claims = {
            "sub": test_admin_user.auth0_sub,
            "email": test_admin_user.email,
        }

        # Require both admin and moderator (user only has admin)
        dependency = current_user(required_roles=["admin", "moderator"])

        with pytest.raises(HTTPException) as exc_info:
            await dependency(request=mock_request, session=db_session, claims=claims)

        assert exc_info.value.status_code == 403
        assert "Not enough permissions" in str(exc_info.value.detail)

    async def test_current_user_admits_brand_new_user(
        self,
        db_session: AsyncSession,
        mock_auth0_new_user_claims: dict[str, Any],
        mock_request: MagicMock,
    ):
        """Signup is open: a first-time caller is provisioned and let through.

        The account grants nothing on its own — every event is still gated by
        membership — so there is no approval queue to hold them in.
        """
        existing_user = await crud_user.get_by_auth0_sub(
            db_session, auth0_sub=mock_auth0_new_user_claims["sub"]
        )
        assert existing_user is None

        dependency = current_user()

        user = await dependency(
            request=mock_request,
            session=db_session,
            claims=mock_auth0_new_user_claims,
        )

        assert user.is_active is True
        assert user.roles == []

        created_user = await crud_user.get_by_auth0_sub(
            db_session, auth0_sub=mock_auth0_new_user_claims["sub"]
        )
        assert created_user is not None
        assert created_user.id == user.id

    async def test_current_user_rejects_suspended_user(
        self,
        db_session: AsyncSession,
        test_inactive_user: User,
        mock_request: MagicMock,
    ):
        """``is_active`` is now a moderation switch, and it still bars entry."""
        dependency = current_user()
        claims = {
            "sub": test_inactive_user.auth0_sub,
            "email": test_inactive_user.email,
        }

        with pytest.raises(HTTPException) as exc_info:
            await dependency(request=mock_request, session=db_session, claims=claims)

        assert exc_info.value.status_code == 403
        assert "Inactive user" in str(exc_info.value.detail)


@pytest.mark.asyncio
class TestCurrentUserAnnotated:
    """Test suite for CurrentUser and CurrentSuperuser typed dependencies."""

    async def test_current_user_annotated(
        self,
        db_session: AsyncSession,
        test_user: User,
        mock_auth0_claims: dict[str, Any],
        mock_request: MagicMock,
    ):
        """Test CurrentUser typed dependency."""
        from app.api.deps import CurrentUser

        # Extract the dependency function from the Annotated type
        # In practice, FastAPI does this automatically
        dependency_metadata = get_args(CurrentUser)[1]
        dependency = dependency_metadata.dependency

        user = await dependency(
            request=mock_request, session=db_session, claims=mock_auth0_claims
        )

        assert user.id == test_user.id
        assert isinstance(user, User)

    async def test_current_superuser_annotated(
        self,
        db_session: AsyncSession,
        test_admin_user: User,
        mock_request: MagicMock,
    ):
        """Test CurrentSuperuser typed dependency."""
        from app.api.deps import CurrentSuperuser

        claims = {
            "sub": test_admin_user.auth0_sub,
            "email": test_admin_user.email,
        }

        dependency_metadata = get_args(CurrentSuperuser)[1]
        dependency = dependency_metadata.dependency

        user = await dependency(request=mock_request, session=db_session, claims=claims)

        assert user.id == test_admin_user.id
        assert user.is_admin is True

    async def test_current_superuser_with_non_admin_fails(
        self,
        db_session: AsyncSession,
        test_user: User,
        mock_request: MagicMock,
    ):
        """Test CurrentSuperuser rejects non-admin users."""
        from app.api.deps import CurrentSuperuser

        claims = {
            "sub": test_user.auth0_sub,
            "email": test_user.email,
        }

        dependency_metadata = get_args(CurrentSuperuser)[1]
        dependency = dependency_metadata.dependency

        with pytest.raises(HTTPException) as exc_info:
            await dependency(request=mock_request, session=db_session, claims=claims)

        assert exc_info.value.status_code == 403
        assert "Not enough permissions" in str(exc_info.value.detail)


class TestRoleNormalization:
    """Test suite for _normalize_required_roles helper."""

    def test_normalize_none(self):
        """Test normalizing None to empty list."""
        from app.api.deps import (
            _normalize_required_roles,  # type: ignore[reportPrivateUsage]
        )

        result = _normalize_required_roles(None)
        assert result == []

    def test_normalize_string(self):
        """Test normalizing single string to list."""
        from app.api.deps import (
            _normalize_required_roles,  # type: ignore[reportPrivateUsage]
        )

        result = _normalize_required_roles("admin")
        assert result == ["admin"]

    def test_normalize_list(self):
        """Test normalizing list of strings."""
        from app.api.deps import (
            _normalize_required_roles,  # type: ignore[reportPrivateUsage]
        )

        result = _normalize_required_roles(["admin", "moderator"])
        assert result == ["admin", "moderator"]

    def test_normalize_iterable(self):
        """Test normalizing tuple to list."""
        from app.api.deps import (
            _normalize_required_roles,  # type: ignore[reportPrivateUsage]
        )

        result = _normalize_required_roles(("admin", "user"))
        assert result == ["admin", "user"]


@pytest.mark.asyncio
class TestCurrentUserAnyOfRoles:
    """Test suite for any_of_roles OR-semantics in current_user dependency."""

    async def test_first_role_matches(
        self,
        db_session: AsyncSession,
        test_admin_user: User,
        mock_request: MagicMock,
    ):
        """Test that first matching role grants access."""
        claims = {"sub": test_admin_user.auth0_sub, "email": test_admin_user.email}
        dependency = current_user(any_of_roles=["admin", "moderator"])

        user = await dependency(request=mock_request, session=db_session, claims=claims)

        assert user.id == test_admin_user.id

    async def test_second_role_matches(
        self,
        db_session: AsyncSession,
        mock_request: MagicMock,
    ):
        """Test that second matching role grants access."""
        moderator = await _make_user(
            db_session,
            email="moderator@example.com",
            auth0_sub="auth0|moderator",
            roles=["moderator"],
            is_active=True,
        )
        claims = {"sub": moderator.auth0_sub, "email": moderator.email}
        dependency = current_user(any_of_roles=["admin", "moderator"])

        user = await dependency(request=mock_request, session=db_session, claims=claims)

        assert user.id == moderator.id

    async def test_neither_role_matches_raises_403(
        self,
        db_session: AsyncSession,
        test_user: User,
        mock_request: MagicMock,
    ):
        """Test that user with no matching role is rejected."""
        claims = {"sub": test_user.auth0_sub, "email": test_user.email}
        dependency = current_user(any_of_roles=["admin", "moderator"])

        with pytest.raises(HTTPException) as exc_info:
            await dependency(request=mock_request, session=db_session, claims=claims)

        assert exc_info.value.status_code == 403
        assert "Not enough permissions" in str(exc_info.value.detail)


# ── helpers for the suites below ──────────────────────────────────

_VERIFY_REQUEST = "app.api.deps.auth0.api_client.verify_request"

_AuthDep = Callable[[Request], Coroutine[Any, Any, dict[str, Any]]]


class _FakeBegin:
    """Async context manager standing in for ``async_session.begin()``.

    A real ``begin()`` COMMITs on exit, which would escape the ``db_session``
    fixture's outer transaction and leave rows behind for the next test. Exiting
    here is therefore a deliberate no-op; exceptions still propagate.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, *args: object) -> bool:
        return False


class _FakeSessionFactory:
    """Drop-in for ``app.api.deps.async_session``.

    ``get_db`` and ``_get_user_from_query_token`` open their *own* sessions off
    the module-level factory rather than the injected one, so the factory has to
    be replaced for those code paths to run against the test transaction.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.begin_calls = 0

    def begin(self) -> _FakeBegin:
        self.begin_calls += 1
        return _FakeBegin(self._session)


def _make_request(
    *,
    query_string: str = "",
    headers: dict[str, str] | None = None,
    scope_extra: dict[str, Any] | None = None,
) -> Request:
    """Build a real Starlette ``Request``.

    ``MagicMock`` is not enough here: the deps under test read
    ``request.query_params``, ``request.headers`` and ``str(request.url)``, and
    ``get_db`` inspects ``request.scope``.
    """
    scope: dict[str, Any] = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
        "root_path": "",
        "path": "/api/v1/notifications/stream",
        "raw_path": b"/api/v1/notifications/stream",
        "query_string": query_string.encode("latin-1"),
        "headers": [
            (key.lower().encode("latin-1"), value.encode("latin-1"))
            for key, value in (headers or {}).items()
        ],
        # ``get_canonical_url`` in the Auth0 plugin reads ``request.app.state``.
        "app": SimpleNamespace(state=SimpleNamespace()),
    }
    if scope_extra:
        scope.update(scope_extra)
    return Request(scope)


async def _make_user(
    db_session: AsyncSession,
    *,
    email: str,
    auth0_sub: str,
    roles: list[str] | None = None,
    is_active: bool = False,
    email_verified: bool = False,
) -> User:
    """Persist a user with an exact email/role/active combination."""
    user = User(
        auth0_sub=auth0_sub,
        email=email,
        name="Fixture User",
        roles=roles if roles is not None else [],
        is_active=is_active,
        email_verified=email_verified,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
class TestSuperadminEscalation:
    """Superadmin auto-escalation in ``get_or_create_user``.

    This is the most privileged path in the application: an address listed in
    ``settings.SUPERADMIN_EMAILS`` is granted the ``admin`` role and activated on
    sight, on every login. The match is an exact ``in`` test against the stored
    email, and the negative cases below pin that down — a case variant, a
    superstring and a domain-suffix lookalike must all fail to escalate.
    """

    async def test_listed_email_gains_admin_and_is_activated(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Listed email on an existing inactive, role-less user escalates."""
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", ["boss@example.com"])
        await _make_user(
            db_session,
            email="boss@example.com",
            auth0_sub="auth0|boss",
            roles=[],
            is_active=False,
        )

        user = await get_or_create_user(db_session, {"sub": "auth0|boss"})

        assert user.roles == ["admin"]
        assert user.is_active is True

        # The escalation must be persisted, not just applied in memory.
        persisted = await crud_user.get_by_auth0_sub(db_session, auth0_sub="auth0|boss")
        assert persisted is not None
        assert persisted.roles == ["admin"]
        assert persisted.is_active is True

    async def test_listed_email_already_admin_is_not_duplicated(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A listed email that is already admin keeps a single 'admin' entry."""
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", ["boss@example.com"])
        await _make_user(
            db_session,
            email="boss@example.com",
            auth0_sub="auth0|boss",
            roles=["admin"],
            is_active=True,
        )

        user = await get_or_create_user(db_session, {"sub": "auth0|boss"})

        assert user.roles == ["admin"]
        assert user.roles.count("admin") == 1

    async def test_listed_email_only_reactivates_when_inactive(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """An already-admin but deactivated superadmin is reactivated."""
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", ["boss@example.com"])
        await _make_user(
            db_session,
            email="boss@example.com",
            auth0_sub="auth0|boss",
            roles=["admin"],
            is_active=False,
        )

        user = await get_or_create_user(db_session, {"sub": "auth0|boss"})

        assert user.roles == ["admin"]
        assert user.is_active is True

    @pytest.mark.parametrize(
        ("stored_email", "reason"),
        [
            ("Admin@Example.com", "an address differing only in case"),
            ("xadmin@example.com", "an address containing the listed one"),
            ("admin@example.com.evil.com", "a lookalike domain suffix"),
            ("admin@example.co", "a truncated domain"),
            ("someone@example.com", "an unrelated address"),
        ],
    )
    async def test_lookalike_emails_do_not_escalate(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
        stored_email: str,
        reason: str,
    ) -> None:
        """Only an exact match against SUPERADMIN_EMAILS may escalate."""
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", ["admin@example.com"])
        auth0_sub = f"auth0|{stored_email}"
        await _make_user(
            db_session,
            email=stored_email,
            auth0_sub=auth0_sub,
            roles=[],
            is_active=False,
        )

        user = await get_or_create_user(db_session, {"sub": auth0_sub})

        assert user.roles == [], f"{reason} must not gain the admin role"
        assert user.is_active is False, f"{reason} must not be activated"

    async def test_user_without_email_is_never_escalated(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A user row with a NULL email short-circuits the membership check."""
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", ["admin@example.com"])
        user = User(
            auth0_sub="auth0|noemail",
            email=None,
            name="No Email",
            roles=[],
            is_active=False,
        )
        db_session.add(user)
        await db_session.flush()

        result = await get_or_create_user(db_session, {"sub": "auth0|noemail"})

        assert result.roles == []
        assert result.is_active is False

    async def test_new_listed_user_is_created_active_with_admin_role(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A first-time login from a listed email is provisioned as admin."""
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", ["founder@example.com"])
        claims = {
            "sub": "auth0|founder",
            "email": "founder@example.com",
            "name": "Founder",
        }

        user = await get_or_create_user(db_session, claims)

        assert user.roles == ["admin"]
        assert user.is_active is True

    async def test_new_listed_user_matched_from_profile_data(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The superadmin check uses the frontend profile email when supplied."""
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", ["founder@example.com"])
        claims = {"sub": "auth0|founder", "email": "stale@example.com"}
        profile_data = {
            "email": "founder@example.com",
            "name": "Founder",
            "email_verified": True,
            "preferred_language": "de",
        }

        user = await get_or_create_user(db_session, claims, profile_data)

        assert user.email == "founder@example.com"
        assert user.roles == ["admin"]
        assert user.is_active is True
        assert user.email_verified is True
        assert user.preferred_language == "de"

    async def test_new_unlisted_user_is_created_active_without_roles(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """An unlisted first-time login is active but holds no global role.

        This is the shape of every ordinary signup now: usable account, zero
        authority until an event lets them in.
        """
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", ["founder@example.com"])
        claims = {
            "sub": "auth0|regular",
            "email": "regular@example.com",
            "name": "Regular",
        }

        user = await get_or_create_user(db_session, claims)

        assert user.roles == []
        assert user.is_active is True


@pytest.mark.asyncio
class TestAuth0ProfileSync:
    """``email_verified`` is re-synced from the Auth0 profile on every login."""

    async def test_email_verified_flips_false_to_true(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verifying the address in Auth0 propagates on the next login."""
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", [])
        await _make_user(
            db_session,
            email="sync@example.com",
            auth0_sub="auth0|sync",
            is_active=True,
            email_verified=False,
        )

        user = await get_or_create_user(
            db_session, {"sub": "auth0|sync"}, {"email_verified": True}
        )

        assert user.email_verified is True

        persisted = await crud_user.get_by_auth0_sub(db_session, auth0_sub="auth0|sync")
        assert persisted is not None
        assert persisted.email_verified is True

    async def test_email_verified_flips_true_to_false(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A revoked verification propagates too — the sync is bidirectional."""
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", [])
        await _make_user(
            db_session,
            email="sync@example.com",
            auth0_sub="auth0|sync",
            is_active=True,
            email_verified=True,
        )

        user = await get_or_create_user(
            db_session, {"sub": "auth0|sync"}, {"email_verified": False}
        )

        assert user.email_verified is False

        persisted = await crud_user.get_by_auth0_sub(db_session, auth0_sub="auth0|sync")
        assert persisted is not None
        assert persisted.email_verified is False

    async def test_profile_data_without_email_verified_is_a_noop(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A profile payload lacking the key must not clear the flag."""
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", [])
        await _make_user(
            db_session,
            email="sync@example.com",
            auth0_sub="auth0|sync",
            is_active=True,
            email_verified=True,
        )

        user = await get_or_create_user(
            db_session, {"sub": "auth0|sync"}, {"name": "Renamed"}
        )

        assert user.email_verified is True

    async def test_matching_email_verified_is_a_noop(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """An unchanged value leaves the user untouched."""
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", [])
        await _make_user(
            db_session,
            email="sync@example.com",
            auth0_sub="auth0|sync",
            is_active=True,
            email_verified=True,
        )

        user = await get_or_create_user(
            db_session, {"sub": "auth0|sync"}, {"email_verified": True}
        )

        assert user.email_verified is True

    async def test_no_profile_data_is_a_noop(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Logins without profile data skip the sync block entirely."""
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", [])
        await _make_user(
            db_session,
            email="sync@example.com",
            auth0_sub="auth0|sync",
            is_active=True,
            email_verified=True,
        )

        user = await get_or_create_user(db_session, {"sub": "auth0|sync"})

        assert user.email_verified is True


@pytest.mark.asyncio
class TestCurrentUserTestEmailHeader:
    """The TESTING-only ``X-Test-User-Email`` branch inside ``_current_user``.

    The E2E suite authenticates with this header instead of a JWT, so the branch
    still has to enforce the active check and the role check.
    """

    async def test_header_resolves_user_without_claims(
        self,
        db_session: AsyncSession,
        test_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A known test email is resolved without consulting the claims."""
        monkeypatch.setattr(settings, "TESTING", True)
        request = _make_request(headers={"X-Test-User-Email": "test@example.com"})
        dependency = current_user()

        user = await dependency(request=request, session=db_session, claims={})

        assert user.id == test_user.id

    async def test_unknown_header_email_raises_401(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """An unknown test email is rejected rather than auto-provisioned."""
        monkeypatch.setattr(settings, "TESTING", True)
        request = _make_request(headers={"X-Test-User-Email": "ghost@example.com"})
        dependency = current_user()

        with pytest.raises(HTTPException) as exc_info:
            await dependency(request=request, session=db_session, claims={})

        assert exc_info.value.status_code == 401
        assert "Test user not found: ghost@example.com" in str(exc_info.value.detail)

    async def test_header_inactive_user_raises_403(
        self,
        db_session: AsyncSession,
        test_inactive_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The active check is enforced on the header branch too."""
        monkeypatch.setattr(settings, "TESTING", True)
        request = _make_request(headers={"X-Test-User-Email": "inactive@example.com"})
        dependency = current_user()

        with pytest.raises(HTTPException) as exc_info:
            await dependency(request=request, session=db_session, claims={})

        assert exc_info.value.status_code == 403
        assert "Inactive user" in str(exc_info.value.detail)

    async def test_header_inactive_user_allowed_when_active_not_required(
        self,
        db_session: AsyncSession,
        test_inactive_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``require_active=False`` (AnyUser) lets pending accounts through."""
        monkeypatch.setattr(settings, "TESTING", True)
        request = _make_request(headers={"X-Test-User-Email": "inactive@example.com"})
        dependency = current_user(require_active=False)

        user = await dependency(request=request, session=db_session, claims={})

        assert user.id == test_inactive_user.id

    async def test_header_still_enforces_role_check(
        self,
        db_session: AsyncSession,
        test_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The header is an authentication bypass, not an authorization one."""
        monkeypatch.setattr(settings, "TESTING", True)
        request = _make_request(headers={"X-Test-User-Email": "test@example.com"})
        dependency = current_user(required_roles="admin")

        with pytest.raises(HTTPException) as exc_info:
            await dependency(request=request, session=db_session, claims={})

        assert exc_info.value.status_code == 403
        assert "Not enough permissions" in str(exc_info.value.detail)

    async def test_header_is_ignored_when_not_testing(
        self,
        db_session: AsyncSession,
        test_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Outside TESTING the header carries no authority at all."""
        monkeypatch.setattr(settings, "TESTING", False)
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", [])
        request = _make_request(headers={"X-Test-User-Email": "ghost@example.com"})
        dependency = current_user()

        user = await dependency(
            request=request,
            session=db_session,
            claims={"sub": test_user.auth0_sub, "email": test_user.email},
        )

        assert user.id == test_user.id


@pytest.mark.asyncio
class TestGetDb:
    """``get_db`` registers the transaction on the per-endpoint exit stack.

    Every route test runs with ``get_db`` overridden, so the real body is only
    exercised here. Both halves matter: the normal path (COMMIT before the
    response is sent) and the fallback for a FastAPI that stops exposing
    ``fastapi_function_astack``.
    """

    async def test_uses_endpoint_exit_stack_when_present(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The transaction is entered on the stack FastAPI put in the scope."""
        factory = _FakeSessionFactory(db_session)
        monkeypatch.setattr(deps_module, "async_session", factory)

        async with AsyncExitStack() as stack:
            request = _make_request(scope_extra={"fastapi_function_astack": stack})
            generator = get_db(request)

            session = await anext(generator)

            assert session is db_session
            assert factory.begin_calls == 1
            with pytest.raises(StopAsyncIteration):
                await anext(generator)

    async def test_falls_back_when_scope_has_no_stack(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Without the stack the dep owns the transaction itself."""
        factory = _FakeSessionFactory(db_session)
        monkeypatch.setattr(deps_module, "async_session", factory)
        request = _make_request()
        generator = get_db(request)

        session = await anext(generator)

        assert session is db_session
        assert factory.begin_calls == 1
        with pytest.raises(StopAsyncIteration):
            await anext(generator)

    async def test_falls_back_when_scope_entry_is_not_a_stack(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A scope entry of the wrong type is treated as absent, not trusted."""
        factory = _FakeSessionFactory(db_session)
        monkeypatch.setattr(deps_module, "async_session", factory)
        request = _make_request(scope_extra={"fastapi_function_astack": object()})
        generator = get_db(request)

        session = await anext(generator)

        assert session is db_session
        assert factory.begin_calls == 1
        with pytest.raises(StopAsyncIteration):
            await anext(generator)


@pytest.mark.asyncio
class TestGetUserFromQueryToken:
    """``_get_user_from_query_token`` — the SSE ``?token=…`` authentication dep.

    ``EventSource`` cannot send headers, so this dep is a second, independent
    entry point into the authorization boundary. It opens its own short-lived
    sessions off the module-level factory, which is why every test below
    redirects that factory at the transactional test session.
    """

    async def test_testing_query_param_resolves_user(
        self,
        db_session: AsyncSession,
        test_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``?test_email=`` resolves a real user while TESTING."""
        monkeypatch.setattr(settings, "TESTING", True)
        monkeypatch.setattr(
            deps_module, "async_session", _FakeSessionFactory(db_session)
        )
        request = _make_request(query_string="token=unused&test_email=test@example.com")

        user = await _get_user_from_query_token(request, token="unused")

        assert user.id == test_user.id

    async def test_testing_header_resolves_user(
        self,
        db_session: AsyncSession,
        test_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The X-Test-User-Email header is accepted as well as the query param."""
        monkeypatch.setattr(settings, "TESTING", True)
        monkeypatch.setattr(
            deps_module, "async_session", _FakeSessionFactory(db_session)
        )
        request = _make_request(
            query_string="token=unused",
            headers={"X-Test-User-Email": "test@example.com"},
        )

        user = await _get_user_from_query_token(request, token="unused")

        assert user.id == test_user.id

    async def test_testing_unknown_email_raises_401(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """An unknown test email is rejected instead of being provisioned."""
        monkeypatch.setattr(settings, "TESTING", True)
        monkeypatch.setattr(
            deps_module, "async_session", _FakeSessionFactory(db_session)
        )
        request = _make_request(
            query_string="token=unused&test_email=ghost@example.com"
        )

        with pytest.raises(HTTPException) as exc_info:
            await _get_user_from_query_token(request, token="unused")

        assert exc_info.value.status_code == 401
        assert "Test user not found: ghost@example.com" in str(exc_info.value.detail)

    async def test_testing_without_test_email_falls_through_to_token(
        self,
        db_session: AsyncSession,
        test_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """TESTING alone is not a bypass — without a test email the JWT is used."""
        monkeypatch.setattr(settings, "TESTING", True)
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", [])
        monkeypatch.setattr(
            deps_module, "async_session", _FakeSessionFactory(db_session)
        )
        request = _make_request(query_string="token=sse-token")
        claims = {"sub": test_user.auth0_sub, "email": test_user.email}

        with patch(_VERIFY_REQUEST, AsyncMock(return_value=claims)) as mock_verify:
            user = await _get_user_from_query_token(request, token="sse-token")

        assert user.id == test_user.id
        assert mock_verify.await_count == 1

    async def test_verified_token_returns_existing_user(
        self,
        db_session: AsyncSession,
        test_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Outside TESTING the query token is verified and mapped to a user."""
        monkeypatch.setattr(settings, "TESTING", False)
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", [])
        monkeypatch.setattr(
            deps_module, "async_session", _FakeSessionFactory(db_session)
        )
        request = _make_request(query_string="token=sse-token")
        claims = {"sub": test_user.auth0_sub, "email": test_user.email}

        with patch(_VERIFY_REQUEST, AsyncMock(return_value=claims)) as mock_verify:
            user = await _get_user_from_query_token(request, token="sse-token")

        assert user.id == test_user.id
        call = mock_verify.call_args
        assert call is not None
        assert call.kwargs["headers"] == {"authorization": "Bearer sse-token"}
        assert call.kwargs["http_method"] == "GET"

    async def test_verified_token_creates_unknown_user(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A verified token for an unseen sub provisions an inactive user."""
        monkeypatch.setattr(settings, "TESTING", False)
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", [])
        monkeypatch.setattr(
            deps_module, "async_session", _FakeSessionFactory(db_session)
        )
        request = _make_request(query_string="token=sse-token")
        claims = {"sub": "auth0|sse-newcomer", "email": "newcomer@example.com"}

        with patch(_VERIFY_REQUEST, AsyncMock(return_value=claims)):
            user = await _get_user_from_query_token(request, token="sse-token")

        assert user.auth0_sub == "auth0|sse-newcomer"
        assert user.is_active is True
        assert user.roles == []

    async def test_rejected_token_raises_401(
        self,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Any verification failure becomes a flat 401, never a 500."""
        monkeypatch.setattr(settings, "TESTING", False)
        monkeypatch.setattr(
            deps_module, "async_session", _FakeSessionFactory(db_session)
        )
        request = _make_request(query_string="token=expired")

        with patch(_VERIFY_REQUEST, AsyncMock(side_effect=RuntimeError("expired"))):
            with pytest.raises(HTTPException) as exc_info:
                await _get_user_from_query_token(request, token="expired")

        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in str(exc_info.value.detail)


@pytest.mark.asyncio
class TestTestAwareRequireAuth:
    """The TESTING-only ``require_auth`` wrapper installed at import time.

    It short-circuits JWT validation when ``X-Test-User-Email`` is present and
    otherwise delegates to the real Auth0 dependency, so real tokens still work
    in local development.
    """

    def _auth_dep(self) -> _AuthDep:
        if not settings.TESTING:
            pytest.skip(
                "the test-aware require_auth wrapper is only installed "
                "when settings.TESTING is true at import time"
            )
        # ``auth0`` comes from an untyped package, so the factory is cast rather
        # than annotated (an annotated assignment narrows back to the unknown
        # inferred type).
        factory = cast(Callable[[], _AuthDep], deps_module.auth0.require_auth)  # type: ignore[arg-type]
        return factory()

    async def test_test_header_short_circuits_validation(self) -> None:
        """With the header present no token is verified at all."""
        auth_dep = self._auth_dep()
        request = _make_request(headers={"X-Test-User-Email": "test@example.com"})

        with patch(_VERIFY_REQUEST, AsyncMock(side_effect=AssertionError)) as mock:
            claims = await auth_dep(request)

        assert claims == {"sub": "test|noop"}
        assert mock.await_count == 0

    async def test_without_header_delegates_to_auth0(self) -> None:
        """Without the header the real Auth0 dependency verifies the request."""
        auth_dep = self._auth_dep()
        request = _make_request(headers={"authorization": "Bearer real-token"})
        verified = {"sub": "auth0|real", "email": "real@example.com"}

        with patch(_VERIFY_REQUEST, AsyncMock(return_value=verified)) as mock:
            claims = await auth_dep(request)

        assert claims == verified
        assert mock.await_count == 1
