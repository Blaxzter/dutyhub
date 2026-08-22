"""FastAPI app and client fixtures for testing."""

from collections.abc import AsyncGenerator
from typing import Any, get_args

import pytest_asyncio
from fastapi import FastAPI, HTTPException, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps as deps_module
from app.main import app as fastapi_app
from app.models.user import User


@pytest_asyncio.fixture
async def app(
    db_session: AsyncSession,
    test_user: User,
) -> AsyncGenerator[FastAPI, None]:
    """FastAPI app with test dependency overrides.

    Only two identity dependencies survive the self-service refactor:
    ``CurrentUser`` and ``CurrentSuperuser``. Everything that used to be a
    global manager role is now a per-event membership, so tests grant access
    by inserting an ``EventMembership`` rather than by swapping a dependency.
    """

    async def override_get_db():
        yield db_session

    async def override_current_user():
        return test_user

    fastapi_app.dependency_overrides[deps_module.get_db] = override_get_db
    fastapi_app.dependency_overrides[
        get_args(deps_module.CurrentUser)[1].dependency
    ] = override_current_user

    # CurrentSuperuser denies by default — use the as_admin fixture for the
    # handful of endpoints that are still platform-wide.
    async def override_deny():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    fastapi_app.dependency_overrides[
        get_args(deps_module.CurrentSuperuser)[1].dependency
    ] = override_deny

    yield fastapi_app

    fastapi_app.dependency_overrides = {}


@pytest_asyncio.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def _swap_identity(app: FastAPI, user: User, *, superuser: bool):
    """Point CurrentUser (and optionally CurrentSuperuser) at ``user``."""
    user_dep: Any = get_args(deps_module.CurrentUser)[1].dependency
    superuser_dep: Any = get_args(deps_module.CurrentSuperuser)[1].dependency
    originals = {
        dep: app.dependency_overrides.get(dep) for dep in (user_dep, superuser_dep)
    }

    async def override():
        return user

    async def override_deny():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    app.dependency_overrides[user_dep] = override
    app.dependency_overrides[superuser_dep] = override if superuser else override_deny
    return originals


def _restore(app: FastAPI, originals: dict[Any, Any]) -> None:
    for dep, original in originals.items():
        if original:
            app.dependency_overrides[dep] = original
        else:
            app.dependency_overrides.pop(dep, None)


@pytest_asyncio.fixture
async def as_admin(app: FastAPI, test_admin_user: User) -> AsyncGenerator[None, None]:
    """Act as the platform superadmin."""
    originals = _swap_identity(app, test_admin_user, superuser=True)
    yield
    _restore(app, originals)


@pytest_asyncio.fixture
async def as_event_admin(
    app: FastAPI, test_event_admin_user: User
) -> AsyncGenerator[None, None]:
    """Act as someone who administers the fixture events but holds no global role.

    Pair with ``test_event`` / ``test_draft_event``, which grant this user the
    ``admin`` membership. CurrentSuperuser still denies — an event admin is
    not a platform admin.
    """
    originals = _swap_identity(app, test_event_admin_user, superuser=False)
    yield
    _restore(app, originals)


@pytest_asyncio.fixture
async def as_outsider(
    app: FastAPI, test_outsider_user: User
) -> AsyncGenerator[None, None]:
    """Act as a signed-in user who belongs to no event at all."""
    originals = _swap_identity(app, test_outsider_user, superuser=False)
    yield
    _restore(app, originals)
