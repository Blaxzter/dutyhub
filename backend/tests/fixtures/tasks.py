"""Task fixtures for testing."""

from datetime import date

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.task import Task
from app.models.user import User


@pytest_asyncio.fixture
async def test_task(
    db_session: AsyncSession, test_user: User, test_event: Event
) -> Task:
    """A published task inside ``test_event``.

    Tasks are always attached to an event now — that is what decides who may
    see or manage them. An event-less task would be invisible to everyone
    except the platform superadmin.
    """
    task = Task(
        name="Pfingsten 2026",
        description="Überregionale Dienstliste Pfingsten",
        start_date=date(2026, 6, 11),
        end_date=date(2026, 6, 13),
        status="published",
        created_by_id=test_user.id,
        event_id=test_event.id,
    )
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)
    return task


@pytest_asyncio.fixture
async def test_draft_task(
    db_session: AsyncSession, test_user: User, test_event: Event
) -> Task:
    """A draft task inside ``test_event``."""
    task = Task(
        name="Kirchentag 2026",
        description="Draft task",
        start_date=date(2026, 6, 10),
        end_date=date(2026, 6, 14),
        status="draft",
        created_by_id=test_user.id,
        event_id=test_event.id,
    )
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)
    return task
