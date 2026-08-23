"""User fixtures for testing.

Every user here is an ordinary local account: a ``local|`` subject, a verified
address and a real bcrypt password hash. That last part is what changed when
authentication moved in-house — an account is now a credential, not just a row
an external issuer pointed at, and a fixture without a hash can be *read* by
the suite but never *signed in as*.

The hash is computed **once, at import**, and shared by all five fixtures. That
is not a micro-optimisation: bcrypt at the default work factor costs roughly a
quarter of a second, ``test_user`` is pulled in by almost every one of the ~1500
collected tests through the ``app`` fixture, and hashing per fixture call would
add minutes of pure CPU to a suite that currently runs in about ninety seconds.
Sharing one hash is safe precisely because the salt is inside it — these are
five accounts that happen to have the same password, which is exactly what
``TEST_USER_PASSWORD`` says on the tin.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User

# The plaintext behind every fixture account below. Tests that need to *prove*
# a password (POST /auth/login, POST /auth/change-password) import this rather
# than guessing; anything else can ignore it.
TEST_USER_PASSWORD = "fixture-password-123"

# Hashed once for the whole session — see the module docstring.
TEST_USER_PASSWORD_HASH = hash_password(TEST_USER_PASSWORD)


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """A plain user. Holds no global role; event fixtures give them ``member``."""
    user = User(
        subject="local|test123",
        email="test@example.com",
        name="Test User",
        password_hash=TEST_USER_PASSWORD_HASH,
        email_verified=True,
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
        subject="local|admin123",
        email="admin@example.com",
        name="Admin User",
        password_hash=TEST_USER_PASSWORD_HASH,
        email_verified=True,
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
        subject="local|manager123",
        email="manager@example.com",
        name="Manager User",
        password_hash=TEST_USER_PASSWORD_HASH,
        email_verified=True,
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
        subject="local|outsider123",
        email="outsider@example.com",
        name="Outsider User",
        password_hash=TEST_USER_PASSWORD_HASH,
        email_verified=True,
        roles=[],
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_inactive_user(db_session: AsyncSession) -> User:
    """A suspended account. Signup no longer produces these; moderation does.

    It keeps its password: suspension is a moderation switch, not a credential
    change, so this account can still *authenticate* and must still be refused
    everywhere ``require_active`` applies. Tests that conflate the two would
    pass against an account that simply had no password.
    """
    user = User(
        subject="local|inactive123",
        email="inactive@example.com",
        name="Inactive User",
        password_hash=TEST_USER_PASSWORD_HASH,
        email_verified=True,
        roles=[],
        is_active=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_passwordless_user(db_session: AsyncSession) -> User:
    """An account with no password at all — ``password_hash`` is NULL.

    Demo and test accounts are provisioned this way, and so was every row that
    predates local authentication. bcrypt raises ``ValueError: Invalid salt`` on
    an empty hash, so this shape is the difference between a clean 401 and a 500
    on the login path; it exists as a fixture so that distinction stays covered.
    """
    user = User(
        subject="demo|passwordless",
        email="passwordless@example.com",
        name="Passwordless User",
        password_hash=None,
        email_verified=False,
        roles=[],
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user
