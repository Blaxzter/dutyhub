"""Task fixtures for testing."""

from datetime import date

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.user import User


@pytest_asyncio.fixture
async def test_task(db_session: AsyncSession, test_user: User) -> Task:
    """Create a published test task."""
    task = Task(
        name="Pfingsten 2026",
        description="Überregionale Dienstliste Pfingsten",
        start_date=date(2026, 5, 24),
        end_date=date(2026, 5, 26),
        status="published",
        created_by_id=test_user.id,
    )
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)
    return task


@pytest_asyncio.fixture
async def test_draft_task(db_session: AsyncSession, test_user: User) -> Task:
    """Create a draft test task."""
    task = Task(
        name="Kirchentag 2026",
        description="Draft task",
        start_date=date(2026, 6, 10),
        end_date=date(2026, 6, 14),
        status="draft",
        created_by_id=test_user.id,
    )
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)
    return task
