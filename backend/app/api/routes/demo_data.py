"""Demo data endpoints for creating/deleting test data.

All demo entities are tagged with a '[DEMO]' prefix so they can be
reliably identified and cleaned up.
"""

import datetime as dt
import random
import uuid

from fastapi import APIRouter
from sqlalchemy import select
from sqlmodel import col

from app.api.deps import CurrentSuperuser, DBDep
from app.models.booking import Booking
from app.models.event import Event
from app.models.shift import Shift
from app.models.task import Task
from app.models.user import User
from app.schemas.demo_data import (
    DEMO_PREFIX,
    DemoDataCreatedResponse,
    DemoDataDeletedResponse,
    DemoDataParams,
)

router = APIRouter(prefix="/demo-data", tags=["demo-data"])

DEMO_TASK_NAMES = [
    "Morning Shift",
    "Afternoon Shift",
    "Night Watch",
    "Weekend Duty",
    "Holiday Coverage",
    "Emergency Standby",
    "Reception Desk",
    "Parking Lot",
    "Main Entrance",
    "VIP Lounge",
    "Info Booth",
    "First Aid Station",
    "Stage Setup",
    "Sound Check",
    "Cleanup Crew",
]

DEMO_GROUP_NAMES = [
    "Summer Festival",
    "Winter Gala",
    "Spring Conference",
    "Autumn Fair",
    "Tech Summit",
    "Community Day",
]

DEMO_LOCATIONS = [
    "Hall A",
    "Hall B",
    "Main Stage",
    "Entrance Gate",
    "Parking Area",
    "VIP Area",
    "Conference Room 1",
    "Conference Room 2",
    "Outdoor Tent",
    "Cafeteria",
]

DEMO_FIRST_NAMES = [
    "Alex",
    "Jordan",
    "Casey",
    "Morgan",
    "Taylor",
    "Riley",
    "Quinn",
    "Avery",
    "Cameron",
    "Dakota",
    "Emery",
    "Finley",
    "Harper",
    "Kendall",
    "Logan",
    "Parker",
    "Reese",
    "Skyler",
    "Sage",
    "Rowan",
]

DEMO_LAST_NAMES = [
    "Mueller",
    "Schmidt",
    "Weber",
    "Fischer",
    "Wagner",
]

DEMO_PHONE_NUMBERS = [
    "+49 151 12345678",
    "+49 152 23456789",
    "+49 160 34567890",
    "+49 170 45678901",
    "+49 171 56789012",
    "+49 172 67890123",
    "+49 175 78901234",
    "+49 176 89012345",
    "+49 177 90123456",
    "+49 178 01234567",
    "+49 179 11223344",
    "+49 151 22334455",
    "+49 152 33445566",
    "+49 160 44556677",
    "+49 170 55667788",
    "+49 171 66778899",
    "+49 172 77889900",
    "+49 175 88990011",
    "+49 176 99001122",
    "+49 177 10203040",
]


@router.post(
    "/",
    response_model=DemoDataCreatedResponse,
)
async def create_demo_data(
    params: DemoDataParams,
    db: DBDep,
    _current_user: CurrentSuperuser,
) -> DemoDataCreatedResponse:
    """Create demo events, tasks, users, and duty shifts."""
    rng = random.Random()  # noqa: S311
    today = dt.date.today()
    created_groups: list[Event] = []
    created_tasks: list[Task] = []
    created_users: list[User] = []
    created_shifts: list[Shift] = []
    total_bookings = 0

    # --- Task groups ---
    for i in range(params.num_events):
        name = DEMO_GROUP_NAMES[i % len(DEMO_GROUP_NAMES)]
        group_start = today + dt.timedelta(days=rng.randint(0, 2))
        group_end = group_start + dt.timedelta(days=rng.randint(5, 9))
        group = Event(
            name=f"{DEMO_PREFIX} {name}",
            description=f"Auto-generated demo event #{i + 1}",
            start_date=group_start,
            end_date=group_end,
            status="published" if params.publish_tasks else "draft",
            created_by_id=_current_user.id,
        )
        db.add(group)
        created_groups.append(group)

    # Flush to get group IDs
    if created_groups:
        await db.flush()

    # --- Tasks — distribute roughly equally across groups ---
    for i in range(params.num_tasks):
        task_name = rng.choice(DEMO_TASK_NAMES)
        day_offset = rng.randint(0, 7)
        task_start = today + dt.timedelta(days=day_offset)

        # Weighted random duration: 1d (50%), 2d (25%), 3d (15%), 4d (10%)
        duration_days = rng.choices([1, 2, 3, 4], weights=[50, 25, 15, 10])[0]
        task_end = task_start + dt.timedelta(days=duration_days - 1)

        # Round-robin group assignment (equal distribution)
        group = created_groups[i % len(created_groups)] if created_groups else None

        task = Task(
            name=f"{DEMO_PREFIX} {task_name}",
            description=f"Auto-generated demo task #{i + 1}",
            start_date=task_start,
            end_date=task_end,
            status="published" if params.publish_tasks else "draft",
            created_by_id=_current_user.id,
            event_id=group.id if group else None,
            location=rng.choice(DEMO_LOCATIONS),
            category="demo",
        )
        db.add(task)
        created_tasks.append(task)

    # Flush to get task IDs
    if created_tasks:
        await db.flush()

    # --- Duty shifts for each task (randomised count per day) ---
    for task in created_tasks:
        # Iterate each day of the task
        num_days = (task.end_date - task.start_date).days + 1
        for d in range(num_days):
            slot_date = task.start_date + dt.timedelta(days=d)
            # Random number of shifts around the target, ±50 %
            lo = max(1, params.num_shifts_per_task // 2)
            hi = max(lo + 1, int(params.num_shifts_per_task * 1.5))
            day_shifts = rng.randint(lo, hi)
            start_hour = rng.randint(7, 10)
            for s in range(day_shifts):
                hour = (start_hour + s) % 23
                slot_start = dt.time(hour=hour)
                slot_end = dt.time(hour=(hour + 1) % 23)
                shift = Shift(
                    task_id=task.id,
                    title=f"{DEMO_PREFIX} Shift {s + 1}",
                    description=f"Demo shift {s + 1} for {task.name}",
                    date=slot_date,
                    start_time=slot_start,
                    end_time=slot_end,
                    location=task.location,
                    category="demo",
                    max_bookings=rng.choice([1, 2, 2, 3]),
                )
                db.add(shift)
                created_shifts.append(shift)

    # --- Demo users (use example.com — RFC 2606 reserved, always valid) ---
    for i in range(params.num_users):
        first = DEMO_FIRST_NAMES[i % len(DEMO_FIRST_NAMES)]
        last = rng.choice(DEMO_LAST_NAMES)
        user = User(
            auth0_sub=f"demo|{uuid.uuid4().hex[:16]}",
            email=f"{first.lower()}.{last.lower()}.{i}@demo.example.com",
            name=f"{DEMO_PREFIX} {first} {last}",
            phone_number=DEMO_PHONE_NUMBERS[i % len(DEMO_PHONE_NUMBERS)],
            preferred_language=rng.choice(["en", "de"]),
            is_active=True,
            roles=[],
        )
        db.add(user)
        created_users.append(user)

    # Flush to get user + shift IDs for bookings
    if created_users or created_shifts:
        await db.flush()

    # --- Bookings: each demo user books a random subset of shifts ---
    if created_users and created_shifts:
        # Track confirmed bookings per shift to respect max_bookings
        slot_booking_counts: dict[uuid.UUID, int] = {s.id: 0 for s in created_shifts}
        booked_pairs: set[tuple[uuid.UUID, uuid.UUID]] = set()

        for user in created_users:
            # Each user books 20-60 % of available shifts
            num_to_book = rng.randint(
                max(1, len(created_shifts) // 5),
                max(1, len(created_shifts) * 3 // 5),
            )
            candidates = rng.sample(
                created_shifts, min(num_to_book, len(created_shifts))
            )
            for shift in candidates:
                pair = (shift.id, user.id)
                if pair in booked_pairs:
                    continue
                if slot_booking_counts[shift.id] >= shift.max_bookings:
                    continue
                booked_pairs.add(pair)
                slot_booking_counts[shift.id] += 1
                booking = Booking(
                    shift_id=shift.id,
                    user_id=user.id,
                    status="confirmed",
                )
                db.add(booking)
                total_bookings += 1

    return DemoDataCreatedResponse(
        events_created=len(created_groups),
        tasks_created=len(created_tasks),
        users_created=len(created_users),
        shifts_created=len(created_shifts),
        bookings_created=total_bookings,
    )


@router.delete(
    "/",
    response_model=DemoDataDeletedResponse,
)
async def delete_demo_data(
    db: DBDep,
    _current_user: CurrentSuperuser,
) -> DemoDataDeletedResponse:
    """Delete all entities whose name starts with the demo prefix."""

    # Find demo tasks
    demo_tasks = (
        (await db.execute(select(Task).where(col(Task.name).startswith(DEMO_PREFIX))))
        .scalars()
        .all()
    )

    # Find demo shifts
    demo_shifts = (
        (
            await db.execute(
                select(Shift).where(col(Shift.title).startswith(DEMO_PREFIX))
            )
        )
        .scalars()
        .all()
    )
    demo_shift_ids = [s.id for s in demo_shifts]

    # Delete bookings on demo shifts
    bookings_deleted = 0
    if demo_shift_ids:
        bookings = (
            (
                await db.execute(
                    select(Booking).where(col(Booking.shift_id).in_(demo_shift_ids))
                )
            )
            .scalars()
            .all()
        )
        bookings_deleted = len(bookings)
        for b in bookings:
            await db.delete(b)

    # Delete demo shifts
    for s in demo_shifts:
        await db.delete(s)

    # Delete demo tasks
    for e in demo_tasks:
        await db.delete(e)

    # Delete demo events
    demo_groups = (
        (await db.execute(select(Event).where(col(Event.name).startswith(DEMO_PREFIX))))
        .scalars()
        .all()
    )
    groups_deleted = len(demo_groups)
    for g in demo_groups:
        await db.delete(g)

    # Delete demo users (auth0_sub starts with 'demo|')
    demo_users = (
        (await db.execute(select(User).where(col(User.auth0_sub).startswith("demo|"))))
        .scalars()
        .all()
    )
    users_deleted = len(demo_users)
    for u in demo_users:
        await db.delete(u)

    return DemoDataDeletedResponse(
        tasks_deleted=len(demo_tasks),
        events_deleted=groups_deleted,
        users_deleted=users_deleted,
        shifts_deleted=len(demo_shifts),
        bookings_deleted=bookings_deleted,
    )
