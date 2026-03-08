from fastapi import APIRouter, Query

from app.api.deps import CurrentSuperuser, CurrentUser, DBDep
from app.core.errors import raise_problem
from app.crud.duty_slot import duty_slot as crud_duty_slot
from app.crud.event import event as crud_event
from app.crud.event_group import event_group as crud_event_group
from app.logic.slot_generator import generate_duty_slots
from app.models.event import Event
from app.schemas.event import (
    EventCreate,
    EventCreateWithSlots,
    EventCreateWithSlotsResponse,
    EventListResponse,
    EventRead,
    EventStatus,
    EventUpdate,
)
from app.schemas.event_group import EventGroupRead

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/", response_model=EventListResponse)
async def list_events(
    session: DBDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    search: str | None = None,
    status: EventStatus | None = None,
) -> EventListResponse:
    """List published events (all users) or all events (admin)."""
    effective_status = status
    if not current_user.is_admin and effective_status is None:
        effective_status = "published"

    items = await crud_event.get_multi_filtered(
        session, skip=skip, limit=limit, search=search, status=effective_status
    )
    total = await crud_event.get_count_filtered(
        session, search=search, status=effective_status
    )
    return EventListResponse(
        items=[EventRead.model_validate(i) for i in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: str,
    session: DBDep,
    current_user: CurrentUser,
) -> Event:
    db_event = await crud_event.get(session, event_id, raise_404_error=True)
    if not current_user.is_admin and db_event.status != "published":
        raise_problem(403, code="event.not_published", detail="Event is not published")
    return db_event


@router.post("/", response_model=EventRead, status_code=201)
async def create_event(
    event_in: EventCreate,
    session: DBDep,
    current_user: CurrentSuperuser,
) -> Event:
    event_in.created_by_id = current_user.id
    return await crud_event.create(session, obj_in=event_in)


@router.post("/with-slots", response_model=EventCreateWithSlotsResponse, status_code=201)
async def create_event_with_slots(
    payload: EventCreateWithSlots,
    session: DBDep,
    current_user: CurrentSuperuser,
) -> EventCreateWithSlotsResponse:
    """Create an event with auto-generated duty slots in a single transaction."""
    # 1. Optionally create a new event group
    event_group_read: EventGroupRead | None = None
    event_group_id = payload.event_group_id

    if payload.new_event_group:
        payload.new_event_group.created_by_id = current_user.id
        db_group = await crud_event_group.create(session, obj_in=payload.new_event_group)
        event_group_id = db_group.id
        event_group_read = EventGroupRead.model_validate(db_group)

    # 2. Create the event with generation config stored
    event_in = EventCreate(
        name=payload.name,
        description=payload.description,
        start_date=payload.start_date,
        end_date=payload.end_date,
        location=payload.location,
        category=payload.category,
        event_group_id=event_group_id,
        created_by_id=current_user.id,
    )
    db_event = await crud_event.create(session, obj_in=event_in)

    # Store generation config on the event
    db_event.slot_duration_minutes = payload.schedule.slot_duration_minutes
    db_event.default_start_time = payload.schedule.default_start_time
    db_event.default_end_time = payload.schedule.default_end_time
    db_event.people_per_slot = payload.schedule.people_per_slot
    db_event.schedule_overrides = [o.model_dump(mode="json") for o in payload.schedule.overrides]
    session.add(db_event)
    await session.flush()

    # 3. Generate and bulk-insert duty slots
    slot_creates = generate_duty_slots(
        event_id=db_event.id,
        event_name=payload.name,
        start_date=payload.start_date,
        end_date=payload.end_date,
        default_start_time=payload.schedule.default_start_time,
        default_end_time=payload.schedule.default_end_time,
        slot_duration_minutes=payload.schedule.slot_duration_minutes,
        people_per_slot=payload.schedule.people_per_slot,
        location=payload.location,
        category=payload.category,
        overrides=payload.schedule.overrides,
    )

    for slot_in in slot_creates:
        await crud_duty_slot.create(session, obj_in=slot_in)

    await session.flush()
    await session.refresh(db_event)

    return EventCreateWithSlotsResponse(
        event=EventRead.model_validate(db_event),
        duty_slots_created=len(slot_creates),
        event_group=event_group_read,
    )


@router.patch("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: str,
    event_in: EventUpdate,
    session: DBDep,
    _current_user: CurrentSuperuser,
) -> Event:
    db_event = await crud_event.get(session, event_id, raise_404_error=True)
    return await crud_event.update(session, db_obj=db_event, obj_in=event_in)


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: str,
    session: DBDep,
    _current_user: CurrentSuperuser,
) -> None:
    db_event = await crud_event.get(session, event_id, raise_404_error=True)
    await session.delete(db_event)
    await session.commit()
