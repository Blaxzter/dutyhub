"""Validator coverage for app.schemas.event."""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas.event import EventBase, EventCreate


def _event(**overrides: Any) -> EventBase:
    return EventBase(
        name=overrides.pop("name", "x"),
        start_date=overrides.pop("start_date", dt.date(2026, 1, 1)),
        end_date=overrides.pop("end_date", dt.date(2026, 1, 2)),
        **overrides,
    )


class TestEventDates:
    def test_accepts_valid_range(self):
        e = _event()
        assert e.end_date > e.start_date

    def test_same_day_allowed(self):
        e = _event(end_date=dt.date(2026, 1, 1))
        assert e.end_date == e.start_date

    def test_rejects_end_before_start(self):
        with pytest.raises(ValidationError, match="end_date"):
            _event(
                start_date=dt.date(2026, 1, 2),
                end_date=dt.date(2026, 1, 1),
            )


class TestDefaultTimeWindow:
    def test_valid_window(self):
        e = _event(
            default_start_time=dt.time(9, 0),
            default_end_time=dt.time(17, 0),
        )
        assert e.default_start_time == dt.time(9, 0)
        assert e.default_end_time == dt.time(17, 0)

    def test_rejects_end_equal_to_start(self):
        with pytest.raises(ValidationError, match="default_end_time"):
            _event(
                default_start_time=dt.time(9, 0),
                default_end_time=dt.time(9, 0),
            )

    def test_rejects_end_before_start(self):
        with pytest.raises(ValidationError, match="default_end_time"):
            _event(
                default_start_time=dt.time(17, 0),
                default_end_time=dt.time(9, 0),
            )

    def test_rejects_overnight_window(self):
        # 18:00 → 02:00 would need wrap-around semantics (issue #85);
        # until then it must be rejected instead of rendering a blank grid.
        with pytest.raises(ValidationError, match="default_end_time"):
            _event(
                default_start_time=dt.time(18, 0),
                default_end_time=dt.time(2, 0),
            )

    def test_both_empty_allowed(self):
        e = _event()
        assert e.default_start_time is None
        assert e.default_end_time is None

    def test_only_start_allowed(self):
        e = _event(default_start_time=dt.time(9, 0))
        assert e.default_start_time == dt.time(9, 0)
        assert e.default_end_time is None

    def test_only_end_allowed(self):
        e = _event(default_end_time=dt.time(17, 0))
        assert e.default_start_time is None
        assert e.default_end_time == dt.time(17, 0)


class TestEventCreate:
    def test_inherits_default_time_validation(self):
        with pytest.raises(ValidationError, match="default_end_time"):
            EventCreate(
                name="x",
                start_date=dt.date(2026, 1, 1),
                end_date=dt.date(2026, 1, 2),
                default_start_time=dt.time(18, 0),
                default_end_time=dt.time(2, 0),
            )
