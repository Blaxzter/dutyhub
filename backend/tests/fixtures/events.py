"""Event, membership and user availability fixtures for testing."""

import datetime

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.event_membership import EventMembership
from app.models.user import User
from app.models.user_availability import UserAvailability, UserAvailabilityDate


async def _seed_memberships(
    db_session: AsyncSession,
    event: Event,
    owner: User,
    event_admin: User,
    member: User,
) -> None:
    """Give an event the standard cast: an owner, an admin and a member.

    Every event fixture goes through here so tests never depend on the
    implicit, platform-wide access that membership replaced.
    """
    for user, role in ((owner, "owner"), (event_admin, "admin"), (member, "member")):
        db_session.add(EventMembership(user_id=user.id, event_id=event.id, role=role))
    await db_session.flush()


@pytest_asyncio.fixture
async def test_event(
    db_session: AsyncSession,
    test_user: User,
    test_admin_user: User,
    test_event_admin_user: User,
) -> Event:
    """A published, public event owned by the superadmin."""
    group = Event(
        name="Kirchentags Woche 2026",
        description="Überregionale Kirchentags-Aktionswoche",
        start_date=datetime.date(2026, 6, 10),
        end_date=datetime.date(2026, 6, 14),
        status="published",
        visibility="public",
        created_by_id=test_admin_user.id,
    )
    db_session.add(group)
    await db_session.flush()
    await _seed_memberships(
        db_session, group, test_admin_user, test_event_admin_user, test_user
    )
    await db_session.refresh(group)
    return group


@pytest_asyncio.fixture
async def test_draft_event(
    db_session: AsyncSession,
    test_user: User,
    test_admin_user: User,
    test_event_admin_user: User,
) -> Event:
    """A draft event with the same cast, for status-visibility tests."""
    group = Event(
        name="Adventskonzert 2026",
        description="Draft group",
        start_date=datetime.date(2026, 12, 1),
        end_date=datetime.date(2026, 12, 7),
        status="draft",
        visibility="public",
        created_by_id=test_admin_user.id,
    )
    db_session.add(group)
    await db_session.flush()
    await _seed_memberships(
        db_session, group, test_admin_user, test_event_admin_user, test_user
    )
    await db_session.refresh(group)
    return group


@pytest_asyncio.fixture
async def test_private_event(
    db_session: AsyncSession,
    test_admin_user: User,
    test_event_admin_user: User,
) -> Event:
    """A private event that ``test_user`` is deliberately NOT in."""
    group = Event(
        name="Interne Planung 2026",
        description="Invitation only",
        start_date=datetime.date(2026, 9, 1),
        end_date=datetime.date(2026, 9, 3),
        status="published",
        visibility="private",
        created_by_id=test_admin_user.id,
    )
    db_session.add(group)
    await db_session.flush()
    for user, role in ((test_admin_user, "owner"), (test_event_admin_user, "admin")):
        db_session.add(EventMembership(user_id=user.id, event_id=group.id, role=role))
    await db_session.flush()
    await db_session.refresh(group)
    return group


@pytest_asyncio.fixture
async def test_user_availability(
    db_session: AsyncSession, test_user: User, test_event: Event
) -> UserAvailability:
    """Create a 'fully_available' UserAvailability for the test user."""
    avail = UserAvailability(
        user_id=test_user.id,
        event_id=test_event.id,
        availability_type="fully_available",
        notes="I'm available all week",
    )
    db_session.add(avail)
    await db_session.flush()
    await db_session.refresh(avail)
    return avail


@pytest_asyncio.fixture
async def test_user_availability_with_dates(
    db_session: AsyncSession, test_user: User, test_event: Event
) -> UserAvailability:
    """Create a 'specific_dates' UserAvailability with individual date entries."""
    avail = UserAvailability(
        user_id=test_user.id,
        event_id=test_event.id,
        availability_type="specific_dates",
        notes="Only free Wednesday and Thursday",
    )
    db_session.add(avail)
    await db_session.flush()
    await db_session.refresh(avail)

    for day in [datetime.date(2026, 6, 10), datetime.date(2026, 6, 11)]:
        db_session.add(UserAvailabilityDate(availability_id=avail.id, slot_date=day))
    await db_session.flush()
    await db_session.refresh(avail)
    return avail
