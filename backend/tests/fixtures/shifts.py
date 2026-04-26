"""Shift fixtures for testing."""

from datetime import date, time

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shift import Shift
from app.models.task import Task


@pytest_asyncio.fixture
async def test_shift(db_session: AsyncSession, test_task: Task) -> Shift:
    """Create a test duty shift."""
    shift = Shift(
        task_id=test_task.id,
        title="Einlasskontrolle",
        description="Einlass am Haupteingang",
        date=date(2026, 5, 24),
        start_time=time(8, 0),
        end_time=time(12, 0),
        location="Haupteingang",
        category="Sicherheit",
        max_bookings=2,
    )
    db_session.add(shift)
    await db_session.flush()
    await db_session.refresh(shift)
    return shift
