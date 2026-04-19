"""Task group and user availability fixtures for testing."""

import datetime

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.user import User
from app.models.user_availability import UserAvailability, UserAvailabilityDate


@pytest_asyncio.fixture
async def test_event(db_session: AsyncSession, test_user: User) -> Event:
    """Create a published test task group."""
    group = Event(
        name="Kirchentags Woche 2026",
        description="Überregionale Kirchentags-Aktionswoche",
        start_date=datetime.date(2026, 6, 10),
        end_date=datetime.date(2026, 6, 14),
        status="published",
        created_by_id=test_user.id,
    )
    db_session.add(group)
    await db_session.flush()
    await db_session.refresh(group)
    return group


@pytest_asyncio.fixture
async def test_draft_event(db_session: AsyncSession, test_user: User) -> Event:
    """Create a draft test task group."""
    group = Event(
        name="Adventskonzert 2026",
        description="Draft group",
        start_date=datetime.date(2026, 12, 1),
        end_date=datetime.date(2026, 12, 7),
        status="draft",
        created_by_id=test_user.id,
    )
    db_session.add(group)
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
