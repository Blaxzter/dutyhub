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
    """FastAPI app with test dependency overrides."""

    async def override_get_db():
        yield db_session

    async def override_current_user():
        return test_user

    fastapi_app.dependency_overrides[deps_module.get_db] = override_get_db
    fastapi_app.dependency_overrides[
        get_args(deps_module.CurrentUser)[1].dependency
    ] = override_current_user

    # CurrentSuperuser and CurrentManager raise 403 by default — use as_admin or
    # as_event_manager fixtures to grant access in tests that require those roles.
    async def override_deny():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    fastapi_app.dependency_overrides[
        get_args(deps_module.CurrentSuperuser)[1].dependency
    ] = override_deny
    fastapi_app.dependency_overrides[
        get_args(deps_module.CurrentGlobalManager)[1].dependency
    ] = override_deny
    fastapi_app.dependency_overrides[
        get_args(deps_module.CurrentManager)[1].dependency
    ] = override_deny

    yield fastapi_app

    fastapi_app.dependency_overrides = {}


@pytest_asyncio.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def as_admin(app: FastAPI, test_admin_user: User) -> AsyncGenerator[None, None]:
    """Temporarily override CurrentUser, CurrentManager, CurrentGlobalManager and CurrentSuperuser to return an admin user."""
    user_dep: Any = get_args(deps_module.CurrentUser)[1].dependency
    manager_dep: Any = get_args(deps_module.CurrentManager)[1].dependency
    global_manager_dep: Any = get_args(deps_module.CurrentGlobalManager)[1].dependency
    superuser_dep: Any = get_args(deps_module.CurrentSuperuser)[1].dependency
    originals = {
        dep: app.dependency_overrides.get(dep)
        for dep in (user_dep, manager_dep, global_manager_dep, superuser_dep)
    }

    async def override_current_user():
        return test_admin_user

    for dep in (user_dep, manager_dep, global_manager_dep, superuser_dep):
        app.dependency_overrides[dep] = override_current_user
    yield
    for dep, original in originals.items():
        if original:
            app.dependency_overrides[dep] = original
        else:
            app.dependency_overrides.pop(dep, None)


@pytest_asyncio.fixture
async def as_event_manager(
    app: FastAPI, test_event_manager_user: User
) -> AsyncGenerator[None, None]:
    """Temporarily override CurrentUser, CurrentManager, CurrentGlobalManager to return an event_manager user.

    CurrentSuperuser is overridden to raise 403 because event_managers are not admins.
    """
    user_dep: Any = get_args(deps_module.CurrentUser)[1].dependency
    manager_dep: Any = get_args(deps_module.CurrentManager)[1].dependency
    global_manager_dep: Any = get_args(deps_module.CurrentGlobalManager)[1].dependency
    superuser_dep: Any = get_args(deps_module.CurrentSuperuser)[1].dependency
    manager_deps = (user_dep, manager_dep, global_manager_dep)
    originals = {
        dep: app.dependency_overrides.get(dep) for dep in (*manager_deps, superuser_dep)
    }

    async def override():
        return test_event_manager_user

    async def override_superuser():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    for dep in manager_deps:
        app.dependency_overrides[dep] = override
    app.dependency_overrides[superuser_dep] = override_superuser
    yield
    for dep, original in originals.items():
        if original:
            app.dependency_overrides[dep] = original
        else:
            app.dependency_overrides.pop(dep, None)
