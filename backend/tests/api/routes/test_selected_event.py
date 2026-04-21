"""Tests for the user's selected-event scope.

Covers:
- PUT /users/me/selected-event (set / clear / forbidden / 404)
- UserProfile exposes selected_event_id
- Default scoping of /bookings/me, /tasks/, /tasks/feed by the user's selection
- Event.is_expired property
- app.logic.event_scope.get_user_event_scope helper
- ON DELETE SET NULL when the selected event is removed
"""

from datetime import date, time
from typing import Any, get_args

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps as deps_module
from app.crud.event_manager import event_manager as crud_egm
from app.logic.event_scope import get_user_event_scope
from app.models.booking import Booking
from app.models.event import Event
from app.models.shift import Shift
from app.models.task import Task
from app.models.user import User


async def _make_event(
    session: AsyncSession,
    *,
    name: str,
    owner: User,
    status: str = "published",
    start: date = date(2026, 8, 1),
    end: date = date(2026, 8, 5),
) -> Event:
    event = Event(
        name=name,
        description=f"{name} description",
        start_date=start,
        end_date=end,
        status=status,
        created_by_id=owner.id,
    )
    session.add(event)
    await session.flush()
    await session.refresh(event)
    return event


async def _make_task_with_shift(
    session: AsyncSession,
    *,
    owner: User,
    event: Event | None,
    task_name: str,
    slot_date: date = date(2026, 8, 2),
) -> tuple[Task, Shift]:
    task = Task(
        name=task_name,
        start_date=slot_date,
        end_date=slot_date,
        status="published",
        created_by_id=owner.id,
        event_id=event.id if event else None,
    )
    session.add(task)
    await session.flush()
    await session.refresh(task)

    shift = Shift(
        task_id=task.id,
        title=f"{task_name} shift",
        date=slot_date,
        start_time=time(9, 0),
        end_time=time(12, 0),
        max_bookings=2,
    )
    session.add(shift)
    await session.flush()
    await session.refresh(shift)
    return task, shift


@pytest.mark.asyncio
class TestUpdateSelectedEvent:
    """PUT /users/me/selected-event"""

    async def test_set_published_event(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_event: Event,
    ):
        r = await async_client.put(
            "/api/v1/users/me/selected-event",
            json={"selected_event_id": str(test_event.id)},
        )

        assert r.status_code == 200
        assert r.json()["selected_event_id"] == str(test_event.id)

        await db_session.refresh(test_user)
        assert test_user.selected_event_id == test_event.id

    async def test_clear_selection(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_event: Event,
    ):
        test_user.selected_event_id = test_event.id
        db_session.add(test_user)
        await db_session.flush()

        r = await async_client.put(
            "/api/v1/users/me/selected-event",
            json={"selected_event_id": None},
        )

        assert r.status_code == 200
        assert r.json()["selected_event_id"] is None

        await db_session.refresh(test_user)
        assert test_user.selected_event_id is None

    async def test_draft_event_forbidden_for_regular_user(
        self,
        async_client: AsyncClient,
        test_draft_event: Event,
    ):
        r = await async_client.put(
            "/api/v1/users/me/selected-event",
            json={"selected_event_id": str(test_draft_event.id)},
        )
        assert r.status_code == 403

    async def test_draft_event_allowed_for_admin(
        self,
        async_client: AsyncClient,
        test_draft_event: Event,
        as_admin: None,
    ):
        r = await async_client.put(
            "/api/v1/users/me/selected-event",
            json={"selected_event_id": str(test_draft_event.id)},
        )
        assert r.status_code == 200
        assert r.json()["selected_event_id"] == str(test_draft_event.id)

    async def test_draft_event_allowed_for_scoped_manager(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_draft_event: Event,
    ):
        await crud_egm.assign(
            db_session, user_id=test_user.id, event_id=test_draft_event.id
        )

        r = await async_client.put(
            "/api/v1/users/me/selected-event",
            json={"selected_event_id": str(test_draft_event.id)},
        )
        assert r.status_code == 200
        assert r.json()["selected_event_id"] == str(test_draft_event.id)

    async def test_missing_event_returns_404(
        self,
        async_client: AsyncClient,
    ):
        r = await async_client.put(
            "/api/v1/users/me/selected-event",
            json={"selected_event_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert r.status_code == 404

    async def test_profile_exposes_selected_event_id(
        self,
        app: FastAPI,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_event: Event,
    ):
        test_user.selected_event_id = test_event.id
        db_session.add(test_user)
        await db_session.flush()

        dep: Any = get_args(deps_module.AnyUser)[1].dependency

        async def override_any_user():
            return test_user

        app.dependency_overrides[dep] = override_any_user
        try:
            r = await async_client.post("/api/v1/users/me")
            assert r.status_code == 200
            assert r.json()["selected_event_id"] == str(test_event.id)
        finally:
            app.dependency_overrides.pop(dep, None)


@pytest.mark.asyncio
class TestEventExpirationAndScopeHelper:
    async def test_is_expired_true_for_past_end_date(self):
        past = Event(
            name="Past",
            start_date=date(2020, 1, 1),
            end_date=date(2020, 1, 2),
            status="published",
        )
        assert past.is_expired is True

    async def test_is_expired_false_for_future_end_date(self, test_event: Event):
        assert test_event.is_expired is False

    async def test_get_user_event_scope_returns_selection(
        self, test_user: User, test_event: Event
    ):
        assert get_user_event_scope(test_user) is None
        test_user.selected_event_id = test_event.id
        assert get_user_event_scope(test_user) == test_event.id


@pytest.mark.asyncio
class TestSelectedEventCascade:
    async def test_set_null_when_selected_event_deleted(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_event: Event,
    ):
        test_user.selected_event_id = test_event.id
        db_session.add(test_user)
        await db_session.flush()

        await db_session.delete(test_event)
        await db_session.flush()
        await db_session.refresh(test_user)

        assert test_user.selected_event_id is None


@pytest.mark.asyncio
class TestBookingsScoping:
    """/bookings/me defaults to the user's selected event."""

    async def test_defaults_to_selected_event(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        event_a = await _make_event(db_session, name="Event A", owner=test_user)
        event_b = await _make_event(db_session, name="Event B", owner=test_user)

        _task_a, shift_a = await _make_task_with_shift(
            db_session, owner=test_user, event=event_a, task_name="Task A"
        )
        _task_b, shift_b = await _make_task_with_shift(
            db_session, owner=test_user, event=event_b, task_name="Task B"
        )

        booking_a = Booking(
            shift_id=shift_a.id, user_id=test_user.id, status="confirmed"
        )
        booking_b = Booking(
            shift_id=shift_b.id, user_id=test_user.id, status="confirmed"
        )
        db_session.add_all([booking_a, booking_b])
        await db_session.flush()

        test_user.selected_event_id = event_a.id
        db_session.add(test_user)
        await db_session.flush()

        r = await async_client.get("/api/v1/bookings/me")
        assert r.status_code == 200
        ids = {item["id"] for item in r.json()["items"]}
        assert str(booking_a.id) in ids
        assert str(booking_b.id) not in ids

    async def test_all_events_bypasses_scope(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        event_a = await _make_event(db_session, name="Event A", owner=test_user)
        event_b = await _make_event(db_session, name="Event B", owner=test_user)

        _task_a, shift_a = await _make_task_with_shift(
            db_session, owner=test_user, event=event_a, task_name="Task A"
        )
        _task_b, shift_b = await _make_task_with_shift(
            db_session, owner=test_user, event=event_b, task_name="Task B"
        )

        booking_a = Booking(
            shift_id=shift_a.id, user_id=test_user.id, status="confirmed"
        )
        booking_b = Booking(
            shift_id=shift_b.id, user_id=test_user.id, status="confirmed"
        )
        db_session.add_all([booking_a, booking_b])
        await db_session.flush()

        test_user.selected_event_id = event_a.id
        db_session.add(test_user)
        await db_session.flush()

        r = await async_client.get("/api/v1/bookings/me", params={"all_events": "true"})
        assert r.status_code == 200
        ids = {item["id"] for item in r.json()["items"]}
        assert {str(booking_a.id), str(booking_b.id)}.issubset(ids)

    async def test_explicit_event_id_overrides_selection(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        event_a = await _make_event(db_session, name="Event A", owner=test_user)
        event_b = await _make_event(db_session, name="Event B", owner=test_user)

        _task_a, shift_a = await _make_task_with_shift(
            db_session, owner=test_user, event=event_a, task_name="Task A"
        )
        _task_b, shift_b = await _make_task_with_shift(
            db_session, owner=test_user, event=event_b, task_name="Task B"
        )

        booking_a = Booking(
            shift_id=shift_a.id, user_id=test_user.id, status="confirmed"
        )
        booking_b = Booking(
            shift_id=shift_b.id, user_id=test_user.id, status="confirmed"
        )
        db_session.add_all([booking_a, booking_b])
        await db_session.flush()

        test_user.selected_event_id = event_a.id
        db_session.add(test_user)
        await db_session.flush()

        r = await async_client.get(
            "/api/v1/bookings/me", params={"event_id": str(event_b.id)}
        )
        assert r.status_code == 200
        ids = {item["id"] for item in r.json()["items"]}
        assert str(booking_b.id) in ids
        assert str(booking_a.id) not in ids


@pytest.mark.asyncio
class TestTasksListScoping:
    """/tasks/ and /tasks/feed default to the user's selected event."""

    async def test_list_defaults_to_selected_event(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        event_a = await _make_event(db_session, name="Event A", owner=test_user)
        event_b = await _make_event(db_session, name="Event B", owner=test_user)

        task_a, _ = await _make_task_with_shift(
            db_session, owner=test_user, event=event_a, task_name="Task A"
        )
        task_b, _ = await _make_task_with_shift(
            db_session, owner=test_user, event=event_b, task_name="Task B"
        )

        test_user.selected_event_id = event_a.id
        db_session.add(test_user)
        await db_session.flush()

        r = await async_client.get("/api/v1/tasks/")
        assert r.status_code == 200
        ids = {item["id"] for item in r.json()["items"]}
        assert str(task_a.id) in ids
        assert str(task_b.id) not in ids

    async def test_list_all_events_bypasses_scope(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        event_a = await _make_event(db_session, name="Event A", owner=test_user)
        event_b = await _make_event(db_session, name="Event B", owner=test_user)

        task_a, _ = await _make_task_with_shift(
            db_session, owner=test_user, event=event_a, task_name="Task A"
        )
        task_b, _ = await _make_task_with_shift(
            db_session, owner=test_user, event=event_b, task_name="Task B"
        )

        test_user.selected_event_id = event_a.id
        db_session.add(test_user)
        await db_session.flush()

        r = await async_client.get("/api/v1/tasks/", params={"all_events": "true"})
        assert r.status_code == 200
        ids = {item["id"] for item in r.json()["items"]}
        assert {str(task_a.id), str(task_b.id)}.issubset(ids)

    async def test_feed_defaults_to_selected_event(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        event_a = await _make_event(db_session, name="Event A", owner=test_user)
        event_b = await _make_event(db_session, name="Event B", owner=test_user)

        task_a, _ = await _make_task_with_shift(
            db_session, owner=test_user, event=event_a, task_name="Task A"
        )
        task_b, _ = await _make_task_with_shift(
            db_session, owner=test_user, event=event_b, task_name="Task B"
        )

        test_user.selected_event_id = event_a.id
        db_session.add(test_user)
        await db_session.flush()

        r = await async_client.get(
            "/api/v1/tasks/feed",
            params={"view": "cards", "date_from": "2026-01-01"},
        )
        assert r.status_code == 200
        ids = {item["id"] for item in r.json()["items"]}
        assert str(task_a.id) in ids
        assert str(task_b.id) not in ids

    async def test_feed_explicit_event_id_overrides_selection(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        event_a = await _make_event(db_session, name="Event A", owner=test_user)
        event_b = await _make_event(db_session, name="Event B", owner=test_user)

        task_a, _ = await _make_task_with_shift(
            db_session, owner=test_user, event=event_a, task_name="Task A"
        )
        task_b, _ = await _make_task_with_shift(
            db_session, owner=test_user, event=event_b, task_name="Task B"
        )

        test_user.selected_event_id = event_a.id
        db_session.add(test_user)
        await db_session.flush()

        r = await async_client.get(
            "/api/v1/tasks/feed",
            params={
                "view": "cards",
                "date_from": "2026-01-01",
                "event_id": str(event_b.id),
            },
        )
        assert r.status_code == 200
        ids = {item["id"] for item in r.json()["items"]}
        assert str(task_b.id) in ids
        assert str(task_a.id) not in ids
