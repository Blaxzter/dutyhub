"""User fixtures for testing."""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """A plain user. Holds no global role; event fixtures give them ``member``."""
    user = User(
        auth0_sub="auth0|test123",
        email="test@example.com",
        name="Test User",
        roles=[],
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin_user(db_session: AsyncSession) -> User:
    """The platform superadmin — the only remaining global role."""
    user = User(
        auth0_sub="auth0|admin123",
        email="admin@example.com",
        name="Admin User",
        roles=["admin"],
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_event_admin_user(db_session: AsyncSession) -> User:
    """A user who runs an event without holding any global role.

    Event fixtures grant this user ``admin`` on the events they create, which
    is what replaced the old global ``task_manager`` role.
    """
    user = User(
        auth0_sub="auth0|manager123",
        email="manager@example.com",
        name="Manager User",
        roles=[],
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_outsider_user(db_session: AsyncSession) -> User:
    """A user with no membership anywhere — the default for a fresh signup."""
    user = User(
        auth0_sub="auth0|outsider123",
        email="outsider@example.com",
        name="Outsider User",
        roles=[],
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_inactive_user(db_session: AsyncSession) -> User:
    """A suspended account. Signup no longer produces these; moderation does."""
    user = User(
        auth0_sub="auth0|inactive123",
        email="inactive@example.com",
        name="Inactive User",
        roles=[],
        is_active=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user
