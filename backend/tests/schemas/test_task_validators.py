"""Validator coverage for app.schemas.task."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas.task import (
    AddSlotsToTask,
    ExcludedSlot,
    ScheduleOverride,
    SlotGenerationConfig,
    TaskBase,
    TaskCreateWithSlots,
)


def _schedule(**overrides: Any) -> SlotGenerationConfig:
    return SlotGenerationConfig(
        default_start_time=overrides.pop("default_start_time", dt.time(9, 0)),
        default_end_time=overrides.pop("default_end_time", dt.time(17, 0)),
        slot_duration_minutes=overrides.pop("slot_duration_minutes", 60),
        people_per_slot=overrides.pop("people_per_slot", 1),
        **overrides,
    )


class TestTaskBase:
    def test_accepts_valid_range(self):
        e = TaskBase(
            name="x",
            start_date=dt.date(2026, 1, 1),
            end_date=dt.date(2026, 1, 2),
        )
        assert e.end_date > e.start_date

    def test_rejects_end_before_start(self):
        with pytest.raises(ValidationError, match="end_date"):
            TaskBase(
                name="x",
                start_date=dt.date(2026, 1, 2),
                end_date=dt.date(2026, 1, 1),
            )

    def test_same_day_allowed(self):
        e = TaskBase(
            name="x",
            start_date=dt.date(2026, 1, 1),
            end_date=dt.date(2026, 1, 1),
        )
        assert e.end_date == e.start_date


class TestScheduleOverride:
    def test_valid(self):
        ScheduleOverride(
            date=dt.date(2026, 1, 1),
            start_time=dt.time(9, 0),
            end_time=dt.time(10, 0),
        )

    def test_end_not_after_start(self):
        with pytest.raises(ValidationError, match="end_time"):
            ScheduleOverride(
                date=dt.date(2026, 1, 1),
                start_time=dt.time(10, 0),
                end_time=dt.time(10, 0),
            )


class TestExcludedSlot:
    def test_valid(self):
        ExcludedSlot(
            date=dt.date(2026, 1, 1),
            start_time=dt.time(9, 0),
            end_time=dt.time(10, 0),
        )


class TestSlotGenerationConfig:
    def test_valid(self):
        _schedule()

    def test_duration_must_be_positive(self):
        with pytest.raises(ValidationError, match="slot_duration_minutes"):
            _schedule(slot_duration_minutes=0)

    def test_people_must_be_positive(self):
        with pytest.raises(ValidationError, match="people_per_slot"):
            _schedule(people_per_slot=0)

    def test_end_time_must_be_after_start_time(self):
        with pytest.raises(ValidationError, match="default_end_time"):
            _schedule(
                default_start_time=dt.time(17, 0),
                default_end_time=dt.time(17, 0),
            )


class TestTaskCreateWithSlots:
    def test_valid(self):
        TaskCreateWithSlots(
            name="x",
            start_date=dt.date(2026, 1, 1),
            end_date=dt.date(2026, 1, 2),
            schedule=_schedule(),
        )

    def test_rejects_end_before_start(self):
        with pytest.raises(ValidationError, match="end_date"):
            TaskCreateWithSlots(
                name="x",
                start_date=dt.date(2026, 1, 2),
                end_date=dt.date(2026, 1, 1),
                schedule=_schedule(),
            )

    def test_rejects_both_event_group_refs(self):
        from app.schemas.event_group import EventGroupCreate

        with pytest.raises(ValidationError, match="event_group_id and new_event_group"):
            TaskCreateWithSlots(
                name="x",
                start_date=dt.date(2026, 1, 1),
                end_date=dt.date(2026, 1, 2),
                event_group_id=uuid.uuid4(),
                new_event_group=EventGroupCreate(
                    name="g",
                    start_date=dt.date(2026, 1, 1),
                    end_date=dt.date(2026, 1, 2),
                ),
                schedule=_schedule(),
            )


class TestAddSlotsToTask:
    def test_valid(self):
        AddSlotsToTask(
            start_date=dt.date(2026, 1, 1),
            end_date=dt.date(2026, 1, 2),
            schedule=_schedule(),
        )

    def test_rejects_end_before_start(self):
        with pytest.raises(ValidationError, match="end_date"):
            AddSlotsToTask(
                start_date=dt.date(2026, 1, 2),
                end_date=dt.date(2026, 1, 1),
                schedule=_schedule(),
            )
