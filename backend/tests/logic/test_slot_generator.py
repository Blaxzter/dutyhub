"""Unit tests for shift generation logic."""

import uuid
from datetime import date, time

import pytest

from app.logic.shift_generator import generate_shifts
from app.schemas.task import ExcludedShift, ScheduleOverride


class TestShiftGenerator:
    """Tests for generate_shifts."""

    def _task_id(self) -> uuid.UUID:
        return uuid.uuid4()

    def test_single_day_30min_shifts(self):
        """10:00-12:00 with 30min shifts = 4 shifts."""
        shifts = generate_shifts(
            task_id=self._task_id(),
            task_name="Bierstand",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            default_start_time=time(10, 0),
            default_end_time=time(12, 0),
            shift_duration_minutes=30,
            people_per_shift=2,
            location="Halle A",
            category="Bar",
        )

        assert len(shifts) == 4
        assert shifts[0].title == "Bierstand 10:00-10:30"
        assert shifts[0].start_time == time(10, 0)
        assert shifts[0].end_time == time(10, 30)
        assert shifts[0].max_bookings == 2
        assert shifts[0].location == "Halle A"
        assert shifts[0].category == "Bar"
        assert shifts[3].title == "Bierstand 11:30-12:00"

    def test_multi_day(self):
        """3 days, 2 hours each, 60min shifts = 6 shifts."""
        shifts = generate_shifts(
            task_id=self._task_id(),
            task_name="Test",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 3),
            default_start_time=time(8, 0),
            default_end_time=time(10, 0),
            shift_duration_minutes=60,
        )

        assert len(shifts) == 6
        dates = {s.date for s in shifts}
        assert dates == {date(2026, 6, 1), date(2026, 6, 2), date(2026, 6, 3)}

    def test_partial_shift_not_created(self):
        """10:00-11:15 with 30min shifts = 2 full shifts (not 3 partial)."""
        shifts = generate_shifts(
            task_id=self._task_id(),
            task_name="Test",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            default_start_time=time(10, 0),
            default_end_time=time(11, 15),
            shift_duration_minutes=30,
        )

        assert len(shifts) == 2
        assert shifts[-1].end_time == time(11, 0)

    def test_override_changes_times(self):
        """Override on day 2 changes its time range."""
        overrides = [
            ScheduleOverride(
                date=date(2026, 6, 2),
                start_time=time(18, 0),
                end_time=time(22, 0),
            )
        ]

        shifts = generate_shifts(
            task_id=self._task_id(),
            task_name="Test",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 2),
            default_start_time=time(10, 0),
            default_end_time=time(12, 0),
            shift_duration_minutes=60,
            overrides=overrides,
        )

        day1_shifts = [s for s in shifts if s.date == date(2026, 6, 1)]
        day2_shifts = [s for s in shifts if s.date == date(2026, 6, 2)]

        assert len(day1_shifts) == 2  # 10-12, 60min
        assert len(day2_shifts) == 4  # 18-22, 60min
        assert day2_shifts[0].start_time == time(18, 0)

    def test_zero_duration_raises(self):
        """shift_duration_minutes < 1 should be rejected by schema validation."""
        with pytest.raises(ValueError, match="at least 1"):
            from app.schemas.task import ShiftGenerationConfig

            ShiftGenerationConfig(
                default_start_time=time(10, 0),
                default_end_time=time(12, 0),
                shift_duration_minutes=0,
                people_per_shift=1,
            )

    def test_default_max_bookings(self):
        """Default people_per_shift is 1."""
        shifts = generate_shifts(
            task_id=self._task_id(),
            task_name="Test",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            default_start_time=time(10, 0),
            default_end_time=time(11, 0),
            shift_duration_minutes=30,
        )

        assert all(s.max_bookings == 1 for s in shifts)

    def test_15min_shifts(self):
        """15-minute shifts over 1 hour = 4 shifts."""
        shifts = generate_shifts(
            task_id=self._task_id(),
            task_name="Test",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            default_start_time=time(9, 0),
            default_end_time=time(10, 0),
            shift_duration_minutes=15,
        )

        assert len(shifts) == 4

    def test_remainder_mode_short_adds_shorter_final_shift(self):
        """10:00-11:15 with 30min shifts + 'short' = 2 full + 1 shorter shift."""
        shifts = generate_shifts(
            task_id=self._task_id(),
            task_name="Bierstand",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            default_start_time=time(10, 0),
            default_end_time=time(11, 15),
            shift_duration_minutes=30,
            remainder_mode="short",
        )

        assert len(shifts) == 3
        assert shifts[0].start_time == time(10, 0)
        assert shifts[0].end_time == time(10, 30)
        assert shifts[-1].start_time == time(11, 0)
        assert shifts[-1].end_time == time(11, 15)
        assert shifts[-1].title == "Bierstand 11:00-11:15"

    def test_remainder_mode_extend_lengthens_last_shift(self):
        """10:00-11:15 with 30min shifts + 'extend' = 2 shifts; last runs 10:30-11:15."""
        shifts = generate_shifts(
            task_id=self._task_id(),
            task_name="Bierstand",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            default_start_time=time(10, 0),
            default_end_time=time(11, 15),
            shift_duration_minutes=30,
            remainder_mode="extend",
        )

        assert len(shifts) == 2
        assert shifts[-1].start_time == time(10, 30)
        assert shifts[-1].end_time == time(11, 15)
        assert shifts[-1].title == "Bierstand 10:30-11:15"

    def test_remainder_mode_extend_noop_when_no_prior_shift(self):
        """Window shorter than duration + 'extend' produces no shifts."""
        shifts = generate_shifts(
            task_id=self._task_id(),
            task_name="Test",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            default_start_time=time(10, 0),
            default_end_time=time(10, 15),
            shift_duration_minutes=30,
            remainder_mode="extend",
        )

        assert shifts == []

    def test_remainder_mode_drop_default_matches_legacy_behavior(self):
        """'drop' is the default; remainder is discarded."""
        shifts = generate_shifts(
            task_id=self._task_id(),
            task_name="Test",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            default_start_time=time(10, 0),
            default_end_time=time(11, 15),
            shift_duration_minutes=30,
            remainder_mode="drop",
        )

        assert len(shifts) == 2
        assert shifts[-1].end_time == time(11, 0)

    def test_excluded_shifts_are_filtered(self):
        """Shifts matching (date, start, end) in excluded_shifts are removed."""
        task_id = self._task_id()
        shifts = generate_shifts(
            task_id=task_id,
            task_name="Test",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            default_start_time=time(10, 0),
            default_end_time=time(12, 0),
            shift_duration_minutes=30,
            excluded_shifts=[
                ExcludedShift(
                    date=date(2026, 6, 1),
                    start_time=time(10, 30),
                    end_time=time(11, 0),
                )
            ],
        )

        assert len(shifts) == 3
        assert all(s.start_time != time(10, 30) for s in shifts)
