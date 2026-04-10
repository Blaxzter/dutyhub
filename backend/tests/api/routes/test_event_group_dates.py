"""Tests for event group date-bounds, shift-dates, and date validation endpoints."""

import datetime
import uuid
from typing import TypedDict

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.duty_slot import DutySlot
from app.models.event import Event
from app.models.event_group import EventGroup
from app.models.slot_batch import SlotBatch
from app.models.user import User
from app.models.user_availability import UserAvailability, UserAvailabilityDate

# ── Types ──────────────────────────────────────────────────────────────────


class FullHierarchy(TypedDict):
    group: EventGroup
    event: Event
    batch: SlotBatch
    slot: DutySlot
    availability: UserAvailability
    avail_date: UserAvailabilityDate


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
async def group_with_events(
    db_session: AsyncSession,
    test_event_group: EventGroup,
    test_user: User,
) -> tuple[EventGroup, list[Event]]:
    """Create a published event group with two events inside it."""
    event_a = Event(
        name="Event A",
        start_date=datetime.date(2026, 6, 10),
        end_date=datetime.date(2026, 6, 11),
        status="published",
        created_by_id=test_user.id,
        event_group_id=test_event_group.id,
    )
    event_b = Event(
        name="Event B",
        start_date=datetime.date(2026, 6, 13),
        end_date=datetime.date(2026, 6, 14),
        status="published",
        created_by_id=test_user.id,
        event_group_id=test_event_group.id,
    )
    db_session.add_all([event_a, event_b])
    await db_session.flush()
    await db_session.refresh(event_a)
    await db_session.refresh(event_b)
    return test_event_group, [event_a, event_b]


@pytest.fixture
async def group_with_full_hierarchy(
    db_session: AsyncSession,
    test_event_group: EventGroup,
    test_user: User,
) -> FullHierarchy:
    """Create a group with event → slot_batch → duty_slot + availability dates."""
    event = Event(
        name="Shift Test Event",
        start_date=datetime.date(2026, 6, 10),
        end_date=datetime.date(2026, 6, 12),
        status="published",
        created_by_id=test_user.id,
        event_group_id=test_event_group.id,
        schedule_overrides=[{"date": "2026-06-11", "skip": True}],
    )
    db_session.add(event)
    await db_session.flush()
    await db_session.refresh(event)

    batch = SlotBatch(
        event_id=event.id,
        start_date=datetime.date(2026, 6, 10),
        end_date=datetime.date(2026, 6, 12),
        schedule_overrides=[{"date": "2026-06-10", "start_time": "09:00"}],
    )
    db_session.add(batch)
    await db_session.flush()
    await db_session.refresh(batch)

    slot = DutySlot(
        event_id=event.id,
        batch_id=batch.id,
        title="Morning Shift",
        date=datetime.date(2026, 6, 10),
        start_time=datetime.time(8, 0),
        end_time=datetime.time(12, 0),
    )
    db_session.add(slot)
    await db_session.flush()
    await db_session.refresh(slot)

    avail = UserAvailability(
        user_id=test_user.id,
        event_group_id=test_event_group.id,
        availability_type="specific_dates",
    )
    db_session.add(avail)
    await db_session.flush()
    await db_session.refresh(avail)

    avail_date = UserAvailabilityDate(
        availability_id=avail.id,
        slot_date=datetime.date(2026, 6, 10),
    )
    db_session.add(avail_date)
    await db_session.flush()
    await db_session.refresh(avail_date)

    return FullHierarchy(
        group=test_event_group,
        event=event,
        batch=batch,
        slot=slot,
        availability=avail,
        avail_date=avail_date,
    )


# ── GET /event-groups/{id}/event-date-bounds ─────────────────────────────


@pytest.mark.asyncio
class TestEventDateBounds:
    """Test suite for GET /event-groups/{id}/event-date-bounds."""

    async def test_returns_bounds_with_events(
        self,
        async_client: AsyncClient,
        group_with_events: tuple[EventGroup, list[Event]],
    ):
        group, _events = group_with_events
        r = await async_client.get(f"/api/v1/event-groups/{group.id}/event-date-bounds")
        assert r.status_code == 200
        data = r.json()
        assert data["earliest_start"] == "2026-06-10"
        assert data["latest_end"] == "2026-06-14"

    async def test_returns_nulls_when_no_events(
        self,
        async_client: AsyncClient,
        test_event_group: EventGroup,
    ):
        r = await async_client.get(
            f"/api/v1/event-groups/{test_event_group.id}/event-date-bounds"
        )
        assert r.status_code == 200
        data = r.json()
        assert data["earliest_start"] is None
        assert data["latest_end"] is None

    async def test_404_for_nonexistent_group(self, async_client: AsyncClient):
        r = await async_client.get(
            f"/api/v1/event-groups/{uuid.uuid4()}/event-date-bounds"
        )
        assert r.status_code == 404

    async def test_single_event_same_start_and_end(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_event_group: EventGroup,
        test_user: User,
    ):
        """When there's only one event, earliest_start == latest_end boundaries."""
        event = Event(
            name="Single Day",
            start_date=datetime.date(2026, 6, 12),
            end_date=datetime.date(2026, 6, 12),
            status="draft",
            created_by_id=test_user.id,
            event_group_id=test_event_group.id,
        )
        db_session.add(event)
        await db_session.flush()

        r = await async_client.get(
            f"/api/v1/event-groups/{test_event_group.id}/event-date-bounds"
        )
        assert r.status_code == 200
        data = r.json()
        assert data["earliest_start"] == "2026-06-12"
        assert data["latest_end"] == "2026-06-12"


# ── PATCH /event-groups/{id} — Date validation ──────────────────────────


@pytest.mark.asyncio
class TestUpdateEventGroupDateValidation:
    """Test enhanced date validation when updating event groups."""

    async def test_rejects_end_before_start(
        self,
        async_client: AsyncClient,
        test_event_group: EventGroup,
        as_admin: None,
    ):
        r = await async_client.patch(
            f"/api/v1/event-groups/{test_event_group.id}",
            json={
                "start_date": "2026-06-14",
                "end_date": "2026-06-10",
            },
        )
        assert r.status_code == 422

    async def test_rejects_start_after_earliest_event(
        self,
        async_client: AsyncClient,
        group_with_events: tuple[EventGroup, list[Event]],
        as_admin: None,
    ):
        """Cannot set start_date after the earliest event start_date."""
        group, _ = group_with_events
        r = await async_client.patch(
            f"/api/v1/event-groups/{group.id}",
            json={"start_date": "2026-06-12"},  # Event A starts on 2026-06-10
        )
        assert r.status_code == 422

    async def test_rejects_end_before_latest_event(
        self,
        async_client: AsyncClient,
        group_with_events: tuple[EventGroup, list[Event]],
        as_admin: None,
    ):
        """Cannot set end_date before the latest event end_date."""
        group, _ = group_with_events
        r = await async_client.patch(
            f"/api/v1/event-groups/{group.id}",
            json={"end_date": "2026-06-12"},  # Event B ends on 2026-06-14
        )
        assert r.status_code == 422

    async def test_allows_valid_date_range_with_events(
        self,
        async_client: AsyncClient,
        group_with_events: tuple[EventGroup, list[Event]],
        as_admin: None,
    ):
        """Can set dates that encompass all events."""
        group, _ = group_with_events
        r = await async_client.patch(
            f"/api/v1/event-groups/{group.id}",
            json={
                "start_date": "2026-06-09",
                "end_date": "2026-06-15",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["start_date"] == "2026-06-09"
        assert data["end_date"] == "2026-06-15"

    async def test_allows_date_update_without_events(
        self,
        async_client: AsyncClient,
        test_event_group: EventGroup,
        as_admin: None,
    ):
        """Can freely update dates when there are no events."""
        r = await async_client.patch(
            f"/api/v1/event-groups/{test_event_group.id}",
            json={
                "start_date": "2026-07-01",
                "end_date": "2026-07-05",
            },
        )
        assert r.status_code == 200
        assert r.json()["start_date"] == "2026-07-01"

    async def test_allows_name_update_without_date_validation(
        self,
        async_client: AsyncClient,
        group_with_events: tuple[EventGroup, list[Event]],
        as_admin: None,
    ):
        """Updating only the name does not trigger date validation."""
        group, _ = group_with_events
        r = await async_client.patch(
            f"/api/v1/event-groups/{group.id}",
            json={"name": "Renamed with events"},
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Renamed with events"


# ── POST /event-groups/{id}/shift-dates ──────────────────────────────────


@pytest.mark.asyncio
class TestShiftEventGroupDates:
    """Test suite for POST /event-groups/{id}/shift-dates."""

    async def test_no_op_when_same_start_date(
        self,
        async_client: AsyncClient,
        group_with_events: tuple[EventGroup, list[Event]],
        as_admin: None,
    ):
        """Shifting to the same start date returns the group unchanged."""
        group, _ = group_with_events
        r = await async_client.post(
            f"/api/v1/event-groups/{group.id}/shift-dates",
            json={"new_start_date": str(group.start_date)},
        )
        assert r.status_code == 200
        assert r.json()["start_date"] == str(group.start_date)

    async def test_shifts_group_dates_forward(
        self,
        async_client: AsyncClient,
        group_with_full_hierarchy: FullHierarchy,
        as_admin: None,
    ):
        """Shifting forward by 7 days updates the group dates."""
        group = group_with_full_hierarchy["group"]
        # Fixture group: start=2026-06-10, end=2026-06-14
        original_start = datetime.date(2026, 6, 10)
        original_end = datetime.date(2026, 6, 14)
        delta = datetime.timedelta(days=7)
        new_start = original_start + delta

        r = await async_client.post(
            f"/api/v1/event-groups/{group.id}/shift-dates",
            json={"new_start_date": new_start.isoformat()},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["start_date"] == new_start.isoformat()
        assert data["end_date"] == (original_end + delta).isoformat()

    async def test_shifts_events(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        group_with_full_hierarchy: FullHierarchy,
        as_admin: None,
    ):
        """Events within the group get their dates shifted."""
        group = group_with_full_hierarchy["group"]
        event = group_with_full_hierarchy["event"]
        original_event_start = event.start_date
        delta = datetime.timedelta(days=5)
        new_start = group.start_date + delta

        await async_client.post(
            f"/api/v1/event-groups/{group.id}/shift-dates",
            json={"new_start_date": new_start.isoformat()},
        )

        await db_session.refresh(event)
        assert event.start_date == original_event_start + delta
        assert event.end_date == datetime.date(2026, 6, 12) + delta

    async def test_shifts_slot_batches(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        group_with_full_hierarchy: FullHierarchy,
        as_admin: None,
    ):
        """Slot batches get their dates shifted."""
        group = group_with_full_hierarchy["group"]
        batch = group_with_full_hierarchy["batch"]
        original_batch_start = batch.start_date
        delta = datetime.timedelta(days=3)
        new_start = group.start_date + delta

        await async_client.post(
            f"/api/v1/event-groups/{group.id}/shift-dates",
            json={"new_start_date": new_start.isoformat()},
        )

        await db_session.refresh(batch)
        assert batch.start_date == original_batch_start + delta
        assert batch.end_date == datetime.date(2026, 6, 12) + delta

    async def test_shifts_duty_slots(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        group_with_full_hierarchy: FullHierarchy,
        as_admin: None,
    ):
        """Duty slots get their dates shifted."""
        group = group_with_full_hierarchy["group"]
        slot = group_with_full_hierarchy["slot"]
        original_slot_date = slot.date
        delta = datetime.timedelta(days=10)
        new_start = group.start_date + delta

        await async_client.post(
            f"/api/v1/event-groups/{group.id}/shift-dates",
            json={"new_start_date": new_start.isoformat()},
        )

        await db_session.refresh(slot)
        assert slot.date == original_slot_date + delta

    async def test_shifts_schedule_overrides(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        group_with_full_hierarchy: FullHierarchy,
        as_admin: None,
    ):
        """Schedule override date keys in events and batches are shifted."""
        group = group_with_full_hierarchy["group"]
        event = group_with_full_hierarchy["event"]
        batch = group_with_full_hierarchy["batch"]
        delta = datetime.timedelta(days=7)
        new_start = group.start_date + delta

        await async_client.post(
            f"/api/v1/event-groups/{group.id}/shift-dates",
            json={"new_start_date": new_start.isoformat()},
        )

        await db_session.refresh(event)
        await db_session.refresh(batch)
        assert event.schedule_overrides is not None
        assert batch.schedule_overrides is not None
        # Event override: "2026-06-11" + 7 days = "2026-06-18"
        assert event.schedule_overrides[0]["date"] == "2026-06-18"
        assert event.schedule_overrides[0]["skip"] is True
        # Batch override: "2026-06-10" + 7 days = "2026-06-17"
        assert batch.schedule_overrides[0]["date"] == "2026-06-17"
        assert batch.schedule_overrides[0]["start_time"] == "09:00"

    async def test_shifts_availability_dates(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        group_with_full_hierarchy: FullHierarchy,
        as_admin: None,
    ):
        """User availability dates are shifted."""
        group = group_with_full_hierarchy["group"]
        avail_date = group_with_full_hierarchy["avail_date"]
        original_date = avail_date.slot_date
        delta = datetime.timedelta(days=4)
        new_start = group.start_date + delta

        await async_client.post(
            f"/api/v1/event-groups/{group.id}/shift-dates",
            json={"new_start_date": new_start.isoformat()},
        )

        await db_session.refresh(avail_date)
        assert avail_date.slot_date == original_date + delta

    async def test_shift_backward(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        group_with_full_hierarchy: FullHierarchy,
        as_admin: None,
    ):
        """Shifting backward (earlier start) works correctly."""
        group = group_with_full_hierarchy["group"]
        event = group_with_full_hierarchy["event"]
        delta = datetime.timedelta(days=-3)
        new_start = group.start_date + delta

        r = await async_client.post(
            f"/api/v1/event-groups/{group.id}/shift-dates",
            json={"new_start_date": new_start.isoformat()},
        )
        assert r.status_code == 200
        assert r.json()["start_date"] == new_start.isoformat()

        await db_session.refresh(event)
        assert event.start_date == datetime.date(2026, 6, 7)  # 10 - 3

    async def test_shift_requires_access(
        self,
        async_client: AsyncClient,
        test_event_group: EventGroup,
    ):
        """Normal user without manager access gets 403."""
        r = await async_client.post(
            f"/api/v1/event-groups/{test_event_group.id}/shift-dates",
            json={"new_start_date": "2026-07-01"},
        )
        assert r.status_code == 403

    async def test_shift_404_for_nonexistent_group(
        self,
        async_client: AsyncClient,
        as_admin: None,
    ):
        r = await async_client.post(
            f"/api/v1/event-groups/{uuid.uuid4()}/shift-dates",
            json={"new_start_date": "2026-07-01"},
        )
        assert r.status_code == 404

    async def test_shift_with_no_events(
        self,
        async_client: AsyncClient,
        test_event_group: EventGroup,
        as_admin: None,
    ):
        """Shifting a group with no events still shifts the group dates."""
        original_start = test_event_group.start_date
        new_start = original_start + datetime.timedelta(days=14)

        r = await async_client.post(
            f"/api/v1/event-groups/{test_event_group.id}/shift-dates",
            json={"new_start_date": new_start.isoformat()},
        )
        assert r.status_code == 200
        assert r.json()["start_date"] == new_start.isoformat()
