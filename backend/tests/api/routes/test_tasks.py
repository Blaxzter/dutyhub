"""Route tests for Task endpoints."""

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.task import Task
from app.models.user import User


@pytest.mark.asyncio
class TestTasksRoutes:
    """Test suite for /tasks/ routes."""

    async def test_list_tasks(self, async_client: AsyncClient, test_task: Task):
        """Test listing tasks returns published tasks."""
        r = await async_client.get("/api/v1/tasks/")

        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert any(item["name"] == test_task.name for item in data["items"])

    async def test_list_tasks_filters_drafts_for_normal_user(
        self, async_client: AsyncClient, test_task: Task, test_draft_task: Task
    ):
        """Test that normal users only see published tasks by default."""
        r = await async_client.get("/api/v1/tasks/")

        assert r.status_code == 200
        data = r.json()
        names = [item["name"] for item in data["items"]]
        assert test_task.name in names
        assert test_draft_task.name not in names

    async def test_get_task(self, async_client: AsyncClient, test_task: Task):
        """Test getting a single published task."""
        r = await async_client.get(f"/api/v1/tasks/{test_task.id}")

        assert r.status_code == 200
        assert r.json()["name"] == test_task.name

    async def test_draft_task_hidden_from_normal_user(
        self, async_client: AsyncClient, test_draft_task: Task
    ):
        """Test that a normal user cannot access a draft task."""
        r = await async_client.get(f"/api/v1/tasks/{test_draft_task.id}")

        assert r.status_code == 403

    async def test_create_task_as_admin(
        self, async_client: AsyncClient, as_admin: None
    ):
        """Test that an admin can create an task."""
        r = await async_client.post(
            "/api/v1/tasks/",
            json={
                "name": "Admin Task",
                "start_date": "2026-07-01",
                "end_date": "2026-07-03",
            },
        )

        assert r.status_code == 201
        assert r.json()["name"] == "Admin Task"
        assert r.json()["status"] == "draft"

    async def test_update_task_as_admin(
        self, async_client: AsyncClient, test_task: Task, as_admin: None
    ):
        """Test that an admin can update an task."""
        r = await async_client.patch(
            f"/api/v1/tasks/{test_task.id}",
            json={"name": "Updated Task Name"},
        )

        assert r.status_code == 200
        assert r.json()["name"] == "Updated Task Name"

    async def test_delete_task_as_admin(
        self, async_client: AsyncClient, test_task: Task, as_admin: None
    ):
        """Test that an admin can delete an task."""
        r = await async_client.delete(f"/api/v1/tasks/{test_task.id}")

        assert r.status_code == 204

    async def test_list_tasks_with_search(
        self, async_client: AsyncClient, test_task: Task
    ):
        """Test searching tasks by name."""
        r = await async_client.get("/api/v1/tasks/", params={"search": "Pfingsten"})

        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert any(item["name"] == test_task.name for item in data["items"])

    async def test_get_nonexistent_task(self, async_client: AsyncClient):
        """Test getting a non-existent task returns 404."""
        import uuid

        fake_id = uuid.uuid4()
        r = await async_client.get(f"/api/v1/tasks/{fake_id}")

        assert r.status_code == 404

    async def test_create_task_with_slots(
        self, async_client: AsyncClient, as_admin: None
    ):
        """Test creating an task with auto-generated duty slots."""
        r = await async_client.post(
            "/api/v1/tasks/with-slots",
            json={
                "name": "Bierstand",
                "description": "Beer stand duty",
                "start_date": "2026-06-01",
                "end_date": "2026-06-02",
                "location": "Halle A",
                "category": "Bar",
                "schedule": {
                    "default_start_time": "10:00:00",
                    "default_end_time": "12:00:00",
                    "slot_duration_minutes": 60,
                    "people_per_slot": 3,
                },
            },
        )

        assert r.status_code == 201
        data = r.json()
        assert data["task"]["name"] == "Bierstand"
        assert data["task"]["location"] == "Halle A"
        assert data["task"]["slot_duration_minutes"] == 60
        assert data["task"]["people_per_slot"] == 3
        assert data["duty_slots_created"] == 4  # 2 days * 2 slots/day
        assert data["event"] is None

    async def test_create_task_with_slots_and_new_group(
        self, async_client: AsyncClient, as_admin: None
    ):
        """Test creating an task with slots and a new task group."""
        r = await async_client.post(
            "/api/v1/tasks/with-slots",
            json={
                "name": "Weinstand",
                "start_date": "2026-06-01",
                "end_date": "2026-06-01",
                "new_event": {
                    "name": "Sommerfest 2026",
                    "start_date": "2026-06-01",
                    "end_date": "2026-06-03",
                },
                "schedule": {
                    "default_start_time": "18:00:00",
                    "default_end_time": "20:00:00",
                    "slot_duration_minutes": 30,
                    "people_per_slot": 2,
                },
            },
        )

        assert r.status_code == 201
        data = r.json()
        assert data["task"]["name"] == "Weinstand"
        assert data["event"] is not None
        assert data["event"]["name"] == "Sommerfest 2026"
        assert data["task"]["event_id"] == data["event"]["id"]
        assert data["duty_slots_created"] == 4  # 2 hours / 30 min

    async def test_create_task_with_slots_and_overrides(
        self, async_client: AsyncClient, as_admin: None
    ):
        """Test per-date schedule overrides."""
        r = await async_client.post(
            "/api/v1/tasks/with-slots",
            json={
                "name": "Kasse",
                "start_date": "2026-06-01",
                "end_date": "2026-06-02",
                "schedule": {
                    "default_start_time": "10:00:00",
                    "default_end_time": "12:00:00",
                    "slot_duration_minutes": 60,
                    "people_per_slot": 1,
                    "overrides": [
                        {
                            "date": "2026-06-02",
                            "start_time": "14:00:00",
                            "end_time": "18:00:00",
                        }
                    ],
                },
            },
        )

        assert r.status_code == 201
        data = r.json()
        # Day 1: 10-12 = 2 slots, Day 2: 14-18 = 4 slots
        assert data["duty_slots_created"] == 6


@pytest.mark.asyncio
class TestTasksTaskManagerRole:
    """Test suite verifying task_manager role access on /tasks/ routes."""

    async def test_create_task_as_task_manager(
        self,
        async_client: AsyncClient,
        as_task_manager: None,
    ):
        """Test that an task_manager can create an task (no group required)."""
        r = await async_client.post(
            "/api/v1/tasks/",
            json={
                "name": "Manager Task",
                "start_date": "2026-08-01",
                "end_date": "2026-08-02",
            },
        )

        assert r.status_code == 201
        assert r.json()["name"] == "Manager Task"

    async def test_create_task_as_normal_user_raises_403(
        self,
        async_client: AsyncClient,
    ):
        """Test that a plain user cannot create tasks without group assignment."""
        r = await async_client.post(
            "/api/v1/tasks/",
            json={
                "name": "Unauthorized Task",
                "start_date": "2026-08-01",
                "end_date": "2026-08-02",
            },
        )

        assert r.status_code == 403

    async def test_update_task_as_task_manager(
        self,
        async_client: AsyncClient,
        test_task: Task,
        as_task_manager: None,
    ):
        """Test that an task_manager can update any task."""
        r = await async_client.patch(
            f"/api/v1/tasks/{test_task.id}",
            json={"name": "Updated by Manager"},
        )

        assert r.status_code == 200
        assert r.json()["name"] == "Updated by Manager"

    async def test_update_task_as_normal_user_raises_403(
        self,
        async_client: AsyncClient,
        test_task: Task,
    ):
        """Test that a plain user cannot update tasks."""
        r = await async_client.patch(
            f"/api/v1/tasks/{test_task.id}",
            json={"name": "Should Fail"},
        )

        assert r.status_code == 403

    async def test_delete_task_as_task_manager(
        self,
        async_client: AsyncClient,
        test_task: Task,
        as_task_manager: None,
    ):
        """Test that an task_manager can delete any task."""
        r = await async_client.delete(f"/api/v1/tasks/{test_task.id}")

        assert r.status_code == 204

    async def test_delete_task_as_normal_user_raises_403(
        self,
        async_client: AsyncClient,
        test_task: Task,
    ):
        """Test that a plain user cannot delete tasks."""
        r = await async_client.delete(f"/api/v1/tasks/{test_task.id}")

        assert r.status_code == 403

    async def test_scoped_manager_can_manage_own_group_task(
        self,
        async_client: AsyncClient,
        app: FastAPI,
        db_session: AsyncSession,
        test_task_manager_user: User,
        test_event: Event,
    ):
        """Test that a scoped group manager can edit tasks in their assigned group."""
        from datetime import date
        from typing import Any, get_args

        from app.api import deps as deps_module
        from app.crud.event_manager import event_manager as crud_egm
        from app.models.task import Task as TaskModel

        # Assign test_task_manager_user as scoped manager (no global role)
        test_task_manager_user.roles = []
        db_session.add(test_task_manager_user)
        await db_session.flush()
        await crud_egm.assign(
            db_session,
            user_id=test_task_manager_user.id,
            event_id=test_event.id,
        )

        # Create an task in that group
        task = TaskModel(
            name="Group Task",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 1),
            status="published",
            created_by_id=test_task_manager_user.id,
            event_id=test_event.id,
        )
        db_session.add(task)
        await db_session.flush()
        await db_session.refresh(task)

        # Override deps to return the scoped user
        user_dep: Any = get_args(deps_module.CurrentUser)[1].dependency
        manager_dep: Any = get_args(deps_module.CurrentManager)[1].dependency

        async def override():
            return test_task_manager_user

        app.dependency_overrides[user_dep] = override
        app.dependency_overrides[manager_dep] = override

        r = await async_client.patch(
            f"/api/v1/tasks/{task.id}", json={"name": "Renamed by Scoped Manager"}
        )

        app.dependency_overrides.pop(user_dep, None)
        app.dependency_overrides.pop(manager_dep, None)

        assert r.status_code == 200
        assert r.json()["name"] == "Renamed by Scoped Manager"

    async def test_scoped_manager_cannot_manage_other_group_task(
        self,
        async_client: AsyncClient,
        app: FastAPI,
        db_session: AsyncSession,
        test_task_manager_user: User,
        test_event: Event,
        test_draft_event: Event,
    ):
        """Test that a scoped group manager cannot edit tasks in another group."""
        from datetime import date
        from typing import Any, get_args

        from app.api import deps as deps_module
        from app.crud.event_manager import event_manager as crud_egm
        from app.models.task import Task as TaskModel

        # Assign user as scoped manager for test_event only (no global role)
        test_task_manager_user.roles = []
        db_session.add(test_task_manager_user)
        await db_session.flush()
        await crud_egm.assign(
            db_session,
            user_id=test_task_manager_user.id,
            event_id=test_event.id,
        )

        # Create task in the OTHER group
        task = TaskModel(
            name="Other Group Task",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 1),
            status="published",
            created_by_id=test_task_manager_user.id,
            event_id=test_draft_event.id,
        )
        db_session.add(task)
        await db_session.flush()
        await db_session.refresh(task)

        user_dep: Any = get_args(deps_module.CurrentUser)[1].dependency
        manager_dep: Any = get_args(deps_module.CurrentManager)[1].dependency

        async def override():
            return test_task_manager_user

        app.dependency_overrides[user_dep] = override
        app.dependency_overrides[manager_dep] = override

        r = await async_client.patch(
            f"/api/v1/tasks/{task.id}", json={"name": "Should Fail"}
        )

        app.dependency_overrides.pop(user_dep, None)
        app.dependency_overrides.pop(manager_dep, None)

        assert r.status_code == 403
