"""Dump golden fixtures from the real backend shift generator.

`frontend/src/composables/useShiftPreview.ts` re-implements
`app/logic/shift_generator.py` in TypeScript so the task-creation wizard can show
a live preview. Drift between the two makes the preview lie about what is about
to be created, so the frontend unit tests assert parity against the output of
*this* module rather than against hand-copied expectations.

Regenerate with:

    just dump-shift-fixtures

and commit the result. If the diff is non-empty, the backend generator changed
and `useShiftPreview.ts` very likely needs the same change.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, time
from pathlib import Path
from typing import Any

from app.logic.shift_generator import generate_shifts
from app.schemas.task import ScheduleOverride

OUT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "frontend"
    / "src"
    / "composables"
    / "__tests__"
    / "shift-generator-fixtures.json"
)

TASK_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TASK_NAME = "Cleanup"


def _case(
    name: str,
    *,
    description: str,
    start_date: date,
    end_date: date,
    default_start_time: time,
    default_end_time: time,
    shift_duration_minutes: int,
    remainder_mode: str = "drop",
    overrides: list[ScheduleOverride] | None = None,
    specific_dates: list[date] | None = None,
) -> dict[str, Any]:
    shifts = generate_shifts(
        task_id=TASK_ID,
        task_name=TASK_NAME,
        start_date=start_date,
        end_date=end_date,
        default_start_time=default_start_time,
        default_end_time=default_end_time,
        shift_duration_minutes=shift_duration_minutes,
        people_per_shift=1,
        remainder_mode=remainder_mode,
        overrides=overrides,
        specific_dates=specific_dates,
    )
    return {
        "name": name,
        "description": description,
        "config": {
            "eventName": TASK_NAME,
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "defaultStartTime": default_start_time.strftime("%H:%M"),
            "defaultEndTime": default_end_time.strftime("%H:%M"),
            "shiftDurationMinutes": shift_duration_minutes,
            "remainderMode": remainder_mode,
            # None and [] are distinct in the JSON but mean the same thing to
            # both generators ("no restriction"); the fixtures carry both so the
            # frontend parity run exercises each.
            "specificDates": (
                None
                if specific_dates is None
                else [d.isoformat() for d in specific_dates]
            ),
            "overrides": [
                {
                    "date": o.date.isoformat(),
                    "startTime": o.start_time.strftime("%H:%M"),
                    "endTime": o.end_time.strftime("%H:%M"),
                }
                for o in (overrides or [])
            ],
        },
        "expected": [
            {
                "date": s.date.isoformat() if s.date else "",
                "startTime": s.start_time.strftime("%H:%M") if s.start_time else "",
                "endTime": s.end_time.strftime("%H:%M") if s.end_time else "",
                "title": s.title,
            }
            for s in shifts
        ],
    }


def build() -> list[dict[str, Any]]:
    return [
        _case(
            "single-day-exact",
            description="Single day, duration divides the window exactly.",
            start_date=date(2026, 3, 2),
            end_date=date(2026, 3, 2),
            default_start_time=time(10, 0),
            default_end_time=time(12, 0),
            shift_duration_minutes=30,
        ),
        _case(
            "single-day-remainder-drop",
            description="Single day with a 20-minute tail that is discarded.",
            start_date=date(2026, 3, 2),
            end_date=date(2026, 3, 2),
            default_start_time=time(10, 0),
            default_end_time=time(12, 20),
            shift_duration_minutes=60,
            remainder_mode="drop",
        ),
        _case(
            "single-day-remainder-short",
            description="Same window, tail kept as a shorter final shift.",
            start_date=date(2026, 3, 2),
            end_date=date(2026, 3, 2),
            default_start_time=time(10, 0),
            default_end_time=time(12, 20),
            shift_duration_minutes=60,
            remainder_mode="short",
        ),
        _case(
            "single-day-remainder-extend",
            description="Same window, tail absorbed by extending the last shift.",
            start_date=date(2026, 3, 2),
            end_date=date(2026, 3, 2),
            default_start_time=time(10, 0),
            default_end_time=time(12, 20),
            shift_duration_minutes=60,
            remainder_mode="extend",
        ),
        _case(
            "single-day-shorter-than-one-shift-drop",
            description="Window smaller than one shift: nothing is generated.",
            start_date=date(2026, 3, 2),
            end_date=date(2026, 3, 2),
            default_start_time=time(10, 0),
            default_end_time=time(10, 20),
            shift_duration_minutes=60,
            remainder_mode="drop",
        ),
        _case(
            "single-day-shorter-than-one-shift-short",
            description="Window smaller than one shift, 'short' mode keeps it.",
            start_date=date(2026, 3, 2),
            end_date=date(2026, 3, 2),
            default_start_time=time(10, 0),
            default_end_time=time(10, 20),
            shift_duration_minutes=60,
            remainder_mode="short",
        ),
        _case(
            "range-three-days",
            description="Multi-day range with a uniform window.",
            start_date=date(2026, 3, 2),
            end_date=date(2026, 3, 4),
            default_start_time=time(9, 0),
            default_end_time=time(11, 0),
            shift_duration_minutes=60,
        ),
        _case(
            "range-crossing-month-boundary",
            description="Range spanning the end of a month.",
            start_date=date(2026, 3, 30),
            end_date=date(2026, 4, 2),
            default_start_time=time(9, 0),
            default_end_time=time(10, 0),
            shift_duration_minutes=30,
        ),
        _case(
            "range-with-override",
            description="Per-date override replaces that day's window only.",
            start_date=date(2026, 3, 2),
            end_date=date(2026, 3, 4),
            default_start_time=time(9, 0),
            default_end_time=time(11, 0),
            shift_duration_minutes=60,
            overrides=[
                ScheduleOverride(
                    date=date(2026, 3, 3),
                    start_time=time(14, 0),
                    end_time=time(17, 0),
                )
            ],
        ),
        _case(
            "range-end-before-start",
            description="end_date before start_date yields nothing.",
            start_date=date(2026, 3, 4),
            end_date=date(2026, 3, 2),
            default_start_time=time(9, 0),
            default_end_time=time(11, 0),
            shift_duration_minutes=60,
        ),
        _case(
            "day-window-inverted",
            description="default_end_time before default_start_time yields nothing.",
            start_date=date(2026, 3, 2),
            end_date=date(2026, 3, 2),
            default_start_time=time(18, 0),
            default_end_time=time(10, 0),
            shift_duration_minutes=60,
        ),
        # Specific-dates mode, before #144: the wizard previewed only the chosen
        # days but submitted start=min / end=max with no per-date exclusions, so
        # the backend filled in the gap days too. Kept as the counter-example —
        # a span with no specific_dates still means "every day in it".
        _case(
            "specific-dates-as-submitted-span",
            description=(
                "A 'specific dates' span submitted WITHOUT specific_dates "
                "(2026-03-02, 03-05): every day between them is generated."
            ),
            start_date=date(2026, 3, 2),
            end_date=date(2026, 3, 5),
            default_start_time=time(9, 0),
            default_end_time=time(11, 0),
            shift_duration_minutes=60,
        ),
        # …and the same span WITH the date list, which is what the wizard sends
        # now. The preview and the generator must agree exactly on this one.
        _case(
            "specific-dates-honoured",
            description=(
                "The same span carrying specific_dates: only 2026-03-02 and "
                "03-05 get shifts, the gap days are skipped."
            ),
            start_date=date(2026, 3, 2),
            end_date=date(2026, 3, 5),
            default_start_time=time(9, 0),
            default_end_time=time(11, 0),
            shift_duration_minutes=60,
            specific_dates=[date(2026, 3, 2), date(2026, 3, 5)],
        ),
        # The trap this pair guards: an empty list must not mean "no days".
        # The frontend checks `specificDates?.length`, so [] falls through to
        # the unfiltered path; the generator has to agree or a client sending
        # `specific_dates: []` in range mode would silently create nothing.
        _case(
            "specific-dates-empty-list-is-no-filter",
            description="An empty specific_dates list generates the whole span.",
            start_date=date(2026, 3, 2),
            end_date=date(2026, 3, 4),
            default_start_time=time(9, 0),
            default_end_time=time(11, 0),
            shift_duration_minutes=60,
            specific_dates=[],
        ),
        # Dates outside [start_date, end_date] are simply never reached, so the
        # generator must not produce them.
        _case(
            "specific-dates-outside-the-span-are-ignored",
            description=(
                "specific_dates listing days beyond the span only yields the "
                "ones inside it."
            ),
            start_date=date(2026, 3, 2),
            end_date=date(2026, 3, 4),
            default_start_time=time(9, 0),
            default_end_time=time(11, 0),
            shift_duration_minutes=60,
            specific_dates=[date(2026, 2, 27), date(2026, 3, 3), date(2026, 3, 9)],
        ),
        # A skipped day's override must have no effect at all.
        _case(
            "specific-dates-with-override-on-a-skipped-day",
            description=(
                "An override on a day outside specific_dates is ignored, and "
                "one on a listed day still applies."
            ),
            start_date=date(2026, 3, 2),
            end_date=date(2026, 3, 4),
            default_start_time=time(9, 0),
            default_end_time=time(11, 0),
            shift_duration_minutes=60,
            specific_dates=[date(2026, 3, 2), date(2026, 3, 4)],
            overrides=[
                ScheduleOverride(
                    date=date(2026, 3, 3),
                    start_time=time(14, 0),
                    end_time=time(17, 0),
                ),
                ScheduleOverride(
                    date=date(2026, 3, 4),
                    start_time=time(14, 0),
                    end_time=time(16, 0),
                ),
            ],
        ),
    ]


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_generated_by": "backend/scripts/dump_shift_generator_fixtures.py",
        "_regenerate_with": "just dump-shift-fixtures",
        "cases": build(),
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    total = sum(len(c["expected"]) for c in payload["cases"])
    print(f"Wrote {len(payload['cases'])} cases ({total} shifts) to {OUT_PATH}")


if __name__ == "__main__":
    main()
