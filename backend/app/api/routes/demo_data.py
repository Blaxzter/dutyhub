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
from app.models.duty_slot import DutySlot
from app.models.event import Event
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
    """Create demo task groups, tasks, users, and duty slots."""
    rng = random.Random()  # noqa: S311
    today = dt.date.today()
    created_groups: list[Event] = []
    created_tasks: list[Task] = []
    created_users: list[User] = []
    created_slots: list[DutySlot] = []
    total_bookings = 0

    # --- Task groups ---
    for i in range(params.num_events):
        name = DEMO_GROUP_NAMES[i % len(DEMO_GROUP_NAMES)]
        group_start = today + dt.timedelta(days=rng.randint(0, 2))
        group_end = group_start + dt.timedelta(days=rng.randint(5, 9))
        group = Event(
            name=f"{DEMO_PREFIX} {name}",
            description=f"Auto-generated demo task group #{i + 1}",
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

    # --- Duty slots for each task (randomised count per day) ---
    for task in created_tasks:
        # Iterate each day of the task
        num_days = (task.end_date - task.start_date).days + 1
        for d in range(num_days):
            slot_date = task.start_date + dt.timedelta(days=d)
            # Random number of slots around the target, ±50 %
            lo = max(1, params.num_slots_per_task // 2)
            hi = max(lo + 1, int(params.num_slots_per_task * 1.5))
            day_slots = rng.randint(lo, hi)
            start_hour = rng.randint(7, 10)
            for s in range(day_slots):
                hour = (start_hour + s) % 23
                slot_start = dt.time(hour=hour)
                slot_end = dt.time(hour=(hour + 1) % 23)
                slot = DutySlot(
                    task_id=task.id,
                    title=f"{DEMO_PREFIX} Slot {s + 1}",
                    description=f"Demo slot {s + 1} for {task.name}",
                    date=slot_date,
                    start_time=slot_start,
                    end_time=slot_end,
                    location=task.location,
                    category="demo",
                    max_bookings=rng.choice([1, 2, 2, 3]),
                )
                db.add(slot)
                created_slots.append(slot)

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

    # Flush to get user + slot IDs for bookings
    if created_users or created_slots:
        await db.flush()

    # --- Bookings: each demo user books a random subset of slots ---
    if created_users and created_slots:
        # Track confirmed bookings per slot to respect max_bookings
        slot_booking_counts: dict[uuid.UUID, int] = {s.id: 0 for s in created_slots}
        booked_pairs: set[tuple[uuid.UUID, uuid.UUID]] = set()

        for user in created_users:
            # Each user books 20-60 % of available slots
            num_to_book = rng.randint(
                max(1, len(created_slots) // 5),
                max(1, len(created_slots) * 3 // 5),
            )
            candidates = rng.sample(created_slots, min(num_to_book, len(created_slots)))
            for slot in candidates:
                pair = (slot.id, user.id)
                if pair in booked_pairs:
                    continue
                if slot_booking_counts[slot.id] >= slot.max_bookings:
                    continue
                booked_pairs.add(pair)
                slot_booking_counts[slot.id] += 1
                booking = Booking(
                    duty_slot_id=slot.id,
                    user_id=user.id,
                    status="confirmed",
                )
                db.add(booking)
                total_bookings += 1

    return DemoDataCreatedResponse(
        events_created=len(created_groups),
        tasks_created=len(created_tasks),
        users_created=len(created_users),
        duty_slots_created=len(created_slots),
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

    # Find demo slots
    demo_slots = (
        (
            await db.execute(
                select(DutySlot).where(col(DutySlot.title).startswith(DEMO_PREFIX))
            )
        )
        .scalars()
        .all()
    )
    demo_slot_ids = [s.id for s in demo_slots]

    # Delete bookings on demo slots
    bookings_deleted = 0
    if demo_slot_ids:
        bookings = (
            (
                await db.execute(
                    select(Booking).where(col(Booking.duty_slot_id).in_(demo_slot_ids))
                )
            )
            .scalars()
            .all()
        )
        bookings_deleted = len(bookings)
        for b in bookings:
            await db.delete(b)

    # Delete demo slots
    for s in demo_slots:
        await db.delete(s)

    # Delete demo tasks
    for e in demo_tasks:
        await db.delete(e)

    # Delete demo task groups
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
        duty_slots_deleted=len(demo_slots),
        bookings_deleted=bookings_deleted,
    )
