"""Unit tests for slot generation logic."""

import uuid
from datetime import date, time

import pytest

from app.logic.slot_generator import generate_duty_slots
from app.schemas.task import ExcludedSlot, ScheduleOverride


class TestSlotGenerator:
    """Tests for generate_duty_slots."""

    def _task_id(self) -> uuid.UUID:
        return uuid.uuid4()

    def test_single_day_30min_slots(self):
        """10:00-12:00 with 30min slots = 4 slots."""
        slots = generate_duty_slots(
            task_id=self._task_id(),
            task_name="Bierstand",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            default_start_time=time(10, 0),
            default_end_time=time(12, 0),
            slot_duration_minutes=30,
            people_per_slot=2,
            location="Halle A",
            category="Bar",
        )

        assert len(slots) == 4
        assert slots[0].title == "Bierstand 10:00-10:30"
        assert slots[0].start_time == time(10, 0)
        assert slots[0].end_time == time(10, 30)
        assert slots[0].max_bookings == 2
        assert slots[0].location == "Halle A"
        assert slots[0].category == "Bar"
        assert slots[3].title == "Bierstand 11:30-12:00"

    def test_multi_day(self):
        """3 days, 2 hours each, 60min slots = 6 slots."""
        slots = generate_duty_slots(
            task_id=self._task_id(),
            task_name="Test",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 3),
            default_start_time=time(8, 0),
            default_end_time=time(10, 0),
            slot_duration_minutes=60,
        )

        assert len(slots) == 6
        dates = {s.date for s in slots}
        assert dates == {date(2026, 6, 1), date(2026, 6, 2), date(2026, 6, 3)}

    def test_partial_slot_not_created(self):
        """10:00-11:15 with 30min slots = 2 full slots (not 3 partial)."""
        slots = generate_duty_slots(
            task_id=self._task_id(),
            task_name="Test",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            default_start_time=time(10, 0),
            default_end_time=time(11, 15),
            slot_duration_minutes=30,
        )

        assert len(slots) == 2
        assert slots[-1].end_time == time(11, 0)

    def test_override_changes_times(self):
        """Override on day 2 changes its time range."""
        overrides = [
            ScheduleOverride(
                date=date(2026, 6, 2),
                start_time=time(18, 0),
                end_time=time(22, 0),
            )
        ]

        slots = generate_duty_slots(
            task_id=self._task_id(),
            task_name="Test",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 2),
            default_start_time=time(10, 0),
            default_end_time=time(12, 0),
            slot_duration_minutes=60,
            overrides=overrides,
        )

        day1_slots = [s for s in slots if s.date == date(2026, 6, 1)]
        day2_slots = [s for s in slots if s.date == date(2026, 6, 2)]

        assert len(day1_slots) == 2  # 10-12, 60min
        assert len(day2_slots) == 4  # 18-22, 60min
        assert day2_slots[0].start_time == time(18, 0)

    def test_zero_duration_raises(self):
        """slot_duration_minutes < 1 should be rejected by schema validation."""
        with pytest.raises(ValueError, match="at least 1"):
            from app.schemas.task import SlotGenerationConfig

            SlotGenerationConfig(
                default_start_time=time(10, 0),
                default_end_time=time(12, 0),
                slot_duration_minutes=0,
                people_per_slot=1,
            )

    def test_default_max_bookings(self):
        """Default people_per_slot is 1."""
        slots = generate_duty_slots(
            task_id=self._task_id(),
            task_name="Test",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            default_start_time=time(10, 0),
            default_end_time=time(11, 0),
            slot_duration_minutes=30,
        )

        assert all(s.max_bookings == 1 for s in slots)

    def test_15min_slots(self):
        """15-minute slots over 1 hour = 4 slots."""
        slots = generate_duty_slots(
            task_id=self._task_id(),
            task_name="Test",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            default_start_time=time(9, 0),
            default_end_time=time(10, 0),
            slot_duration_minutes=15,
        )

        assert len(slots) == 4

    def test_remainder_mode_short_adds_shorter_final_slot(self):
        """10:00-11:15 with 30min slots + 'short' = 2 full + 1 shorter slot."""
        slots = generate_duty_slots(
            task_id=self._task_id(),
            task_name="Bierstand",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            default_start_time=time(10, 0),
            default_end_time=time(11, 15),
            slot_duration_minutes=30,
            remainder_mode="short",
        )

        assert len(slots) == 3
        assert slots[0].start_time == time(10, 0)
        assert slots[0].end_time == time(10, 30)
        assert slots[-1].start_time == time(11, 0)
        assert slots[-1].end_time == time(11, 15)
        assert slots[-1].title == "Bierstand 11:00-11:15"

    def test_remainder_mode_extend_lengthens_last_slot(self):
        """10:00-11:15 with 30min slots + 'extend' = 2 slots; last runs 10:30-11:15."""
        slots = generate_duty_slots(
            task_id=self._task_id(),
            task_name="Bierstand",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            default_start_time=time(10, 0),
            default_end_time=time(11, 15),
            slot_duration_minutes=30,
            remainder_mode="extend",
        )

        assert len(slots) == 2
        assert slots[-1].start_time == time(10, 30)
        assert slots[-1].end_time == time(11, 15)
        assert slots[-1].title == "Bierstand 10:30-11:15"

    def test_remainder_mode_extend_noop_when_no_prior_slot(self):
        """Window shorter than duration + 'extend' produces no slots."""
        slots = generate_duty_slots(
            task_id=self._task_id(),
            task_name="Test",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            default_start_time=time(10, 0),
            default_end_time=time(10, 15),
            slot_duration_minutes=30,
            remainder_mode="extend",
        )

        assert slots == []

    def test_remainder_mode_drop_default_matches_legacy_behavior(self):
        """'drop' is the default; remainder is discarded."""
        slots = generate_duty_slots(
            task_id=self._task_id(),
            task_name="Test",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            default_start_time=time(10, 0),
            default_end_time=time(11, 15),
            slot_duration_minutes=30,
            remainder_mode="drop",
        )

        assert len(slots) == 2
        assert slots[-1].end_time == time(11, 0)

    def test_excluded_slots_are_filtered(self):
        """Slots matching (date, start, end) in excluded_slots are removed."""
        task_id = self._task_id()
        slots = generate_duty_slots(
            task_id=task_id,
            task_name="Test",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            default_start_time=time(10, 0),
            default_end_time=time(12, 0),
            slot_duration_minutes=30,
            excluded_slots=[
                ExcludedSlot(
                    date=date(2026, 6, 1),
                    start_time=time(10, 30),
                    end_time=time(11, 0),
                )
            ],
        )

        assert len(slots) == 3
        assert all(s.start_time != time(10, 30) for s in slots)
