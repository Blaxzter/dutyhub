from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlmodel import col

from app.api.deps import CurrentUser, DBDep
from app.core.errors import raise_problem
from app.crud.duty_slot import duty_slot as crud_duty_slot
from app.crud.event import event as crud_event
from app.crud.slot_batch import slot_batch as crud_slot_batch
from app.crud.task import task as crud_task
from app.logic.permissions import require_event_access
from app.logic.slot_generator import generate_duty_slots
from app.models.duty_slot import DutySlot
from app.models.slot_batch import SlotBatch
from app.schemas.duty_slot import DutySlotCreate
from app.schemas.event import EventRead
from app.schemas.slot_batch import SlotBatchCreate
from app.schemas.task import (
    AddSlotsResponse,
    AddSlotsToTask,
    AffectedBookingInfo,
    SlotRegenerationResult,
    TaskCreate,
    TaskCreateWithSlots,
    TaskCreateWithSlotsResponse,
    TaskRead,
    TaskUpdateWithSlots,
)

router = APIRouter()


@router.post("/with-slots", response_model=TaskCreateWithSlotsResponse, status_code=201)
async def create_task_with_slots(
    payload: TaskCreateWithSlots,
    session: DBDep,
    current_user: CurrentUser,
) -> TaskCreateWithSlotsResponse:
    """Create an task with auto-generated duty slots in a single transaction."""
    # Check access for the target task group (if any)
    await require_event_access(current_user, session, payload.event_id)
    # 1. Optionally create a new task group
    event_read: EventRead | None = None
    event_id = payload.event_id

    if payload.new_event:
        payload.new_event.created_by_id = current_user.id
        db_group = await crud_event.create(session, obj_in=payload.new_event)
        event_id = db_group.id
        event_read = EventRead.model_validate(db_group)

    # 2. Create the task with generation config stored
    task_in = TaskCreate(
        name=payload.name,
        description=payload.description,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status,
        location=payload.location,
        category=payload.category,
        event_id=event_id,
        created_by_id=current_user.id,
    )
    db_task = await crud_task.create(session, obj_in=task_in)

    # Store generation config on the task (kept for backwards compat)
    db_task.slot_duration_minutes = payload.schedule.slot_duration_minutes
    db_task.default_start_time = payload.schedule.default_start_time
    db_task.default_end_time = payload.schedule.default_end_time
    db_task.people_per_slot = payload.schedule.people_per_slot
    db_task.schedule_overrides = [
        o.model_dump(mode="json") for o in payload.schedule.overrides
    ]
    session.add(db_task)
    await session.flush()

    # 3. Create a SlotBatch to store the generation config
    batch_in = SlotBatchCreate(
        task_id=db_task.id,
        label=payload.name,
        start_date=payload.start_date,
        end_date=payload.end_date,
        location=payload.location,
        category=payload.category,
        default_start_time=payload.schedule.default_start_time,
        default_end_time=payload.schedule.default_end_time,
        slot_duration_minutes=payload.schedule.slot_duration_minutes,
        people_per_slot=payload.schedule.people_per_slot,
        remainder_mode=payload.schedule.remainder_mode,
        schedule_overrides=[
            o.model_dump(mode="json") for o in payload.schedule.overrides
        ],
    )
    db_batch = await crud_slot_batch.create(session, obj_in=batch_in)

    # 4. Generate and bulk-insert duty slots linked to the batch
    slot_creates = generate_duty_slots(
        task_id=db_task.id,
        task_name=payload.name,
        start_date=payload.start_date,
        end_date=payload.end_date,
        default_start_time=payload.schedule.default_start_time,
        default_end_time=payload.schedule.default_end_time,
        slot_duration_minutes=payload.schedule.slot_duration_minutes,
        people_per_slot=payload.schedule.people_per_slot,
        remainder_mode=payload.schedule.remainder_mode,
        location=payload.location,
        category=payload.category,
        overrides=payload.schedule.overrides,
        excluded_slots=payload.schedule.excluded_slots,
    )

    for slot_in in slot_creates:
        slot_in.batch_id = db_batch.id
        await crud_duty_slot.create(session, obj_in=slot_in)

    await session.flush()
    await session.refresh(db_task)

    return TaskCreateWithSlotsResponse(
        task=TaskRead.model_validate(db_task),
        duty_slots_created=len(slot_creates),
        event=event_read,
    )


@router.post("/{task_id}/add-slots", response_model=AddSlotsResponse, status_code=201)
async def add_slots_to_task(
    task_id: str,
    payload: AddSlotsToTask,
    session: DBDep,
    current_user: CurrentUser,
) -> AddSlotsResponse:
    """Add a new batch of duty slots to an existing task without touching existing slots."""
    db_task = await crud_task.get(session, task_id, raise_404_error=True)
    await require_event_access(current_user, session, db_task.event_id)

    # Validate dates against task group constraints
    if db_task.event_id:
        db_group = await crud_event.get(session, db_task.event_id, raise_404_error=True)
        if (
            payload.start_date < db_group.start_date
            or payload.end_date > db_group.end_date
        ):
            raise_problem(
                400,
                code="dates_outside_event",
                detail=(
                    f"Slot dates must fall within the task group date range "
                    f"({db_group.start_date} to {db_group.end_date})"
                ),
            )

    # Create a SlotBatch record
    batch_in = SlotBatchCreate(
        task_id=db_task.id,
        label=payload.location or payload.category or db_task.name,
        start_date=payload.start_date,
        end_date=payload.end_date,
        location=payload.location,
        category=payload.category,
        default_start_time=payload.schedule.default_start_time,
        default_end_time=payload.schedule.default_end_time,
        slot_duration_minutes=payload.schedule.slot_duration_minutes,
        people_per_slot=payload.schedule.people_per_slot,
        remainder_mode=payload.schedule.remainder_mode,
        schedule_overrides=[
            o.model_dump(mode="json") for o in payload.schedule.overrides
        ],
    )
    db_batch = await crud_slot_batch.create(session, obj_in=batch_in)

    slot_creates = generate_duty_slots(
        task_id=db_task.id,
        task_name=db_task.name,
        start_date=payload.start_date,
        end_date=payload.end_date,
        default_start_time=payload.schedule.default_start_time,
        default_end_time=payload.schedule.default_end_time,
        slot_duration_minutes=payload.schedule.slot_duration_minutes,
        people_per_slot=payload.schedule.people_per_slot,
        remainder_mode=payload.schedule.remainder_mode,
        location=payload.location,
        category=payload.category,
        overrides=payload.schedule.overrides,
        excluded_slots=payload.schedule.excluded_slots,
    )

    for slot_in in slot_creates:
        slot_in.batch_id = db_batch.id
        await crud_duty_slot.create(session, obj_in=slot_in)

    await session.flush()
    await session.refresh(db_task)

    return AddSlotsResponse(
        task=TaskRead.model_validate(db_task),
        slots_added=len(slot_creates),
    )


@router.post(
    "/{task_id}/regenerate-slots",
    response_model=SlotRegenerationResult,
)
async def regenerate_task_slots(
    task_id: str,
    payload: TaskUpdateWithSlots,
    session: DBDep,
    current_user: CurrentUser,
    dry_run: bool = Query(default=False),
    batch_id: str | None = Query(default=None),
) -> SlotRegenerationResult:
    """Regenerate duty slots for an task, preserving bookings where slots match.

    When dry_run=True, returns a preview without making changes.
    When batch_id is provided, only regenerates slots belonging to that batch.
    Slots are matched by (date, start_time, end_time) — matched slots keep their bookings.
    """
    db_task = await crud_task.get(session, task_id, raise_404_error=True)
    await require_event_access(current_user, session, db_task.event_id)

    # If batch_id provided, load the batch for defaults
    db_batch: SlotBatch | None = None
    if batch_id:
        db_batch = await crud_slot_batch.get(session, batch_id, raise_404_error=True)
        if str(db_batch.task_id) != str(db_task.id):
            raise_problem(
                400,
                code="batch.wrong_task",
                detail="Batch does not belong to this task",
            )

    # Determine effective task fields (use payload overrides or existing/batch values)
    effective_name = payload.name or db_task.name
    if db_batch:
        effective_start_date = payload.start_date or db_batch.start_date
        effective_end_date = payload.end_date or db_batch.end_date
        effective_location = (
            payload.location if payload.location is not None else db_batch.location
        )
        effective_category = (
            payload.category if payload.category is not None else db_batch.category
        )
    else:
        effective_start_date = payload.start_date or db_task.start_date
        effective_end_date = payload.end_date or db_task.end_date
        effective_location = (
            payload.location if payload.location is not None else db_task.location
        )
        effective_category = (
            payload.category if payload.category is not None else db_task.category
        )

    # 1. Generate new slot definitions
    new_slot_defs = generate_duty_slots(
        task_id=db_task.id,
        task_name=effective_name,
        start_date=effective_start_date,
        end_date=effective_end_date,
        default_start_time=payload.schedule.default_start_time,
        default_end_time=payload.schedule.default_end_time,
        slot_duration_minutes=payload.schedule.slot_duration_minutes,
        people_per_slot=payload.schedule.people_per_slot,
        remainder_mode=payload.schedule.remainder_mode,
        location=effective_location,
        category=effective_category,
        overrides=payload.schedule.overrides,
        excluded_slots=payload.schedule.excluded_slots,
    )

    # 2. Load existing slots with their bookings (scoped to batch if provided)
    stmt = (
        select(DutySlot)
        .where(col(DutySlot.task_id) == db_task.id)
        .options(selectinload(DutySlot.bookings))  # type: ignore[arg-type]
    )
    if batch_id:
        stmt = stmt.where(col(DutySlot.batch_id) == batch_id)
    result = await session.execute(stmt)
    existing_slots = list(result.scalars().all())

    # 3. Build lookup of existing slots by (date, start_time, end_time)
    existing_lookup: dict[tuple[Any, ...], DutySlot] = {}
    for slot in existing_slots:
        key = (slot.date, slot.start_time, slot.end_time)
        existing_lookup[key] = slot

    # 4. Match new slots to existing
    matched_keys: set[tuple[Any, ...]] = set()
    slots_to_create: list[DutySlotCreate] = []
    for new_slot in new_slot_defs:
        key = (new_slot.date, new_slot.start_time, new_slot.end_time)
        if key in existing_lookup:
            matched_keys.add(key)
            # Update title and max_bookings on matched slots
            existing = existing_lookup[key]
            existing.title = new_slot.title
            existing.max_bookings = new_slot.max_bookings
            existing.location = new_slot.location
            existing.category = new_slot.category
        else:
            slots_to_create.append(new_slot)

    # 5. Find unmatched existing slots (to be deleted) and their confirmed bookings
    affected_bookings: list[AffectedBookingInfo] = []
    slots_to_delete: list[DutySlot] = []
    for key, slot in existing_lookup.items():
        if key not in matched_keys:
            slots_to_delete.append(slot)
            for booking in slot.bookings:
                if booking.status == "confirmed":
                    affected_bookings.append(
                        AffectedBookingInfo(
                            booking_id=booking.id,
                            user_id=booking.user_id,
                            slot_title=slot.title,
                            slot_date=slot.date,
                            slot_start_time=slot.start_time,
                            slot_end_time=slot.end_time,
                        )
                    )

    if not dry_run:
        # 6a. Update task fields (only when not scoped to a batch)
        if not batch_id:
            if payload.name is not None:
                db_task.name = payload.name
            if payload.description is not None:
                db_task.description = payload.description
            if payload.start_date is not None:
                db_task.start_date = payload.start_date
            if payload.end_date is not None:
                db_task.end_date = payload.end_date
            if payload.location is not None:
                db_task.location = payload.location
            if payload.category is not None:
                db_task.category = payload.category

            # Store generation config on task
            db_task.slot_duration_minutes = payload.schedule.slot_duration_minutes
            db_task.default_start_time = payload.schedule.default_start_time
            db_task.default_end_time = payload.schedule.default_end_time
            db_task.people_per_slot = payload.schedule.people_per_slot
            db_task.schedule_overrides = [
                o.model_dump(mode="json") for o in payload.schedule.overrides
            ]
            session.add(db_task)

        # 6b. Update batch record if scoped
        if db_batch:
            db_batch.start_date = effective_start_date
            db_batch.end_date = effective_end_date
            db_batch.location = effective_location
            db_batch.category = effective_category
            db_batch.default_start_time = payload.schedule.default_start_time
            db_batch.default_end_time = payload.schedule.default_end_time
            db_batch.slot_duration_minutes = payload.schedule.slot_duration_minutes
            db_batch.people_per_slot = payload.schedule.people_per_slot
            db_batch.remainder_mode = payload.schedule.remainder_mode
            db_batch.schedule_overrides = [
                o.model_dump(mode="json") for o in payload.schedule.overrides
            ]
            session.add(db_batch)

        # 6c. Delete unmatched slots (cascade deletes bookings)
        for slot in slots_to_delete:
            await session.delete(slot)

        # 6d. Create new slots (linked to batch if scoped)
        for slot_in in slots_to_create:
            if batch_id and db_batch:
                slot_in.batch_id = db_batch.id
            await crud_duty_slot.create(session, obj_in=slot_in)

        await session.flush()
        await session.refresh(db_task)

    return SlotRegenerationResult(
        task=TaskRead.model_validate(db_task),
        slots_added=len(slots_to_create),
        slots_removed=len(slots_to_delete),
        slots_kept=len(matched_keys),
        affected_bookings=affected_bookings,
    )
