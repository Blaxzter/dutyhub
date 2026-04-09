"""User fixtures for testing."""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
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
    """Create a test admin user."""
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
async def test_event_manager_user(db_session: AsyncSession) -> User:
    """Create a test user with the event_manager role."""
    user = User(
        auth0_sub="auth0|manager123",
        email="manager@example.com",
        name="Manager User",
        roles=["event_manager"],
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_inactive_user(db_session: AsyncSession) -> User:
    """Create an inactive test user."""
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
