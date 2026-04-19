"""Unit tests for Task CRUD operations."""

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.task import task as crud_task
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate


@pytest.mark.asyncio
class TestCRUDTask:
    """Test suite for Task CRUD operations."""

    async def test_create_task(self, db_session: AsyncSession, test_user: User):
        """Test creating a new task."""
        task_in = TaskCreate(
            name="Test Task",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 3),
            status="draft",
            created_by_id=test_user.id,
        )
        task = await crud_task.create(db_session, obj_in=task_in)

        assert task.name == "Test Task"
        assert task.status == "draft"
        assert task.created_by_id == test_user.id
        assert task.id is not None

    async def test_get_task(self, db_session: AsyncSession, test_task: Task):
        """Test getting a task by ID."""
        task = await crud_task.get(db_session, test_task.id)

        assert task is not None
        assert task.name == test_task.name
        assert task.id == test_task.id

    async def test_update_task(self, db_session: AsyncSession, test_task: Task):
        """Test updating a task."""
        update = TaskUpdate(name="Updated Task")
        updated = await crud_task.update(db_session, db_obj=test_task, obj_in=update)

        assert updated.name == "Updated Task"
        assert updated.id == test_task.id

    async def test_get_multi_filtered_by_status(
        self, db_session: AsyncSession, test_task: Task, test_draft_task: Task
    ):
        """Test filtering tasks by status."""
        published = await crud_task.get_multi_filtered(db_session, status="published")

        assert len(published) >= 1
        assert all(e.status == "published" for e in published)

        drafts = await crud_task.get_multi_filtered(db_session, status="draft")
        assert len(drafts) >= 1
        assert all(e.status == "draft" for e in drafts)

    async def test_get_count_filtered(self, db_session: AsyncSession, test_task: Task):
        """Test counting tasks with filter."""
        count = await crud_task.get_count_filtered(db_session, status="published")

        assert count >= 1

    async def test_get_multi_filtered_by_search(
        self, db_session: AsyncSession, test_task: Task
    ):
        """Test searching tasks by name."""
        results = await crud_task.get_multi_filtered(db_session, search="Pfingsten")

        assert len(results) >= 1
        assert any(e.id == test_task.id for e in results)

    async def test_remove_task(self, db_session: AsyncSession, test_task: Task):
        """Test removing a task."""
        task_id = test_task.id
        removed = await crud_task.remove(db_session, id=task_id)

        assert removed is not None
        assert removed.id == task_id

        found = await crud_task.get(db_session, task_id)
        assert found is None
