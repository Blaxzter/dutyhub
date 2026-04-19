"""Unit tests for Shift CRUD operations."""

from datetime import date, time

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.shift import shift as crud_shift
from app.models.shift import Shift
from app.models.task import Task
from app.schemas.shift import ShiftCreate, ShiftUpdate


@pytest.mark.asyncio
class TestCRUDShift:
    """Test suite for Shift CRUD operations."""

    async def test_create_shift(self, db_session: AsyncSession, test_task: Task):
        """Test creating a new duty shift."""
        slot_in = ShiftCreate(
            task_id=test_task.id,
            title="Morning Shift",
            date=date(2026, 6, 1),
            start_time=time(8, 0),
            end_time=time(12, 0),
            max_bookings=3,
        )
        shift = await crud_shift.create(db_session, obj_in=slot_in)

        assert shift.title == "Morning Shift"
        assert shift.date == date(2026, 6, 1)
        assert shift.max_bookings == 3
        assert shift.id is not None

    async def test_get_shift(self, db_session: AsyncSession, test_shift: Shift):
        """Test getting a duty shift by ID."""
        found = await crud_shift.get(db_session, test_shift.id)

        assert found is not None
        assert found.id == test_shift.id

    async def test_update_shift(self, db_session: AsyncSession, test_shift: Shift):
        """Test updating a duty shift."""
        updated = await crud_shift.update(
            db_session,
            db_obj=test_shift,
            obj_in=ShiftUpdate(title="Updated Shift"),
        )

        assert updated.title == "Updated Shift"

    async def test_get_multi_filtered_by_task(
        self, db_session: AsyncSession, test_shift: Shift, test_task: Task
    ):
        """Test filtering duty shifts by task."""
        shifts = await crud_shift.get_multi_filtered(
            db_session, task_id=str(test_task.id)
        )

        assert len(shifts) >= 1
        assert all(s.task_id == test_task.id for s in shifts)

    async def test_get_multi_filtered_by_search(
        self, db_session: AsyncSession, test_shift: Shift
    ):
        """Test searching duty shifts by title."""
        shifts = await crud_shift.get_multi_filtered(
            db_session, search=test_shift.title[:5]
        )

        assert len(shifts) >= 1
        assert any(s.id == test_shift.id for s in shifts)

    async def test_get_multi_filtered_no_results(self, db_session: AsyncSession):
        """Test searching with no matching results."""
        shifts = await crud_shift.get_multi_filtered(
            db_session, search="zzz_nonexistent_zzz"
        )

        assert len(shifts) == 0

    async def test_get_count_filtered(
        self, db_session: AsyncSession, test_shift: Shift, test_task: Task
    ):
        """Test counting filtered duty shifts."""
        count = await crud_shift.get_count_filtered(
            db_session, task_id=str(test_task.id)
        )

        assert count >= 1

    async def test_get_count_filtered_empty(self, db_session: AsyncSession):
        """Test counting with no matching results."""
        count = await crud_shift.get_count_filtered(
            db_session, search="zzz_nonexistent_zzz"
        )

        assert count == 0

    async def test_get_multi_filtered_sort_desc(
        self, db_session: AsyncSession, test_task: Task
    ):
        """Test sorting duty shifts in descending order."""
        # Create two shifts with different dates
        for i, d in enumerate([date(2026, 7, 1), date(2026, 7, 10)]):
            slot_in = ShiftCreate(
                task_id=test_task.id,
                title=f"Shift {i}",
                date=d,
                start_time=time(9, 0),
                end_time=time(12, 0),
            )
            await crud_shift.create(db_session, obj_in=slot_in)

        shifts = await crud_shift.get_multi_filtered(
            db_session,
            task_id=str(test_task.id),
            sort_by="date",
            sort_dir="desc",
        )

        assert len(shifts) >= 2
        dates = [s.date for s in shifts]
        assert dates == sorted(dates, reverse=True)

    async def test_remove_shift(self, db_session: AsyncSession, test_task: Task):
        """Test removing a duty shift."""
        slot_in = ShiftCreate(
            task_id=test_task.id,
            title="To Delete",
            date=date(2026, 8, 1),
            start_time=time(10, 0),
            end_time=time(14, 0),
        )
        shift = await crud_shift.create(db_session, obj_in=slot_in)
        slot_id = shift.id

        await crud_shift.remove(db_session, id=slot_id)

        deleted = await crud_shift.get(db_session, slot_id)
        assert deleted is None
