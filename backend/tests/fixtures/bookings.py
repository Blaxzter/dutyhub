"""Booking fixtures for testing."""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.shift import Shift
from app.models.user import User


@pytest_asyncio.fixture
async def test_booking(
    db_session: AsyncSession, test_shift: Shift, test_user: User
) -> Booking:
    """Create a test booking."""
    booking = Booking(
        shift_id=test_shift.id,
        user_id=test_user.id,
        status="confirmed",
        notes="I'll be there!",
    )
    db_session.add(booking)
    await db_session.flush()
    await db_session.refresh(booking)
    return booking
