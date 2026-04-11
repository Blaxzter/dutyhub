import uuid

from fastapi import APIRouter, BackgroundTasks, Query
from sqlalchemy import select
from sqlmodel import col

from app.api.deps import CurrentUser, DBDep
from app.core.errors import raise_problem
from app.crud.booking import booking as crud_booking
from app.crud.event import event as crud_event
from app.crud.event_group_manager import event_group_manager as crud_egm
from app.logic.permissions import require_event_group_access
from app.models.duty_slot import DutySlot
from app.models.event import Event
from app.models.event_group_manager import EventGroupManager
from app.schemas.booking import EventBookingEntry
from app.schemas.event import (
    EventCreate,
    EventListResponse,
    EventRead,
    EventStatus,
    EventUpdate,
)

router = APIRouter()


@router.get("/", response_model=EventListResponse)
async def list_events(
    session: DBDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    search: str | None = None,
    status: EventStatus | None = None,
    my_bookings: bool = Query(default=False),
) -> EventListResponse:
    """List published events (all users) or all events (admin/manager).

    Scoped group managers see published events plus events in their managed groups.
    """
    effective_status = status
    also_include_group_ids = None

    if current_user.is_manager:
        # Global admin/event_manager — see everything
        pass
    else:
        # Check for scoped group manager
        result = await session.execute(
            select(col(EventGroupManager.event_group_id)).where(
                col(EventGroupManager.user_id) == current_user.id
            )
        )
        managed_ids: list[uuid.UUID] = list(result.scalars().all())

        if effective_status is None:
            effective_status = "published"
        if managed_ids:
            also_include_group_ids = managed_ids

    booked_by_user_id = str(current_user.id) if my_bookings else None

    items = await crud_event.get_multi_filtered(
        session,
        skip=skip,
        limit=limit,
        search=search,
        status=effective_status,
        booked_by_user_id=booked_by_user_id,
        also_include_group_ids=also_include_group_ids,
    )
    total = await crud_event.get_count_filtered(
        session,
        search=search,
        status=effective_status,
        booked_by_user_id=booked_by_user_id,
        also_include_group_ids=also_include_group_ids,
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
    if not current_user.is_manager and db_event.status != "published":
        # Allow scoped group managers to see their unpublished events
        if not db_event.event_group_id or not await crud_egm.is_manager(
            session, user_id=current_user.id, event_group_id=db_event.event_group_id
        ):
            raise_problem(
                403, code="event.not_published", detail="Event is not published"
            )
    return db_event


@router.post("/", response_model=EventRead, status_code=201)
async def create_event(
    event_in: EventCreate,
    session: DBDep,
    current_user: CurrentUser,
) -> Event:
    await require_event_group_access(current_user, session, event_in.event_group_id)
    event_in.created_by_id = current_user.id
    return await crud_event.create(session, obj_in=event_in)


@router.patch("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: str,
    event_in: EventUpdate,
    session: DBDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> Event:
    db_event = await crud_event.get(session, event_id, raise_404_error=True)
    await require_event_group_access(current_user, session, db_event.event_group_id)
    old_status = db_event.status
    updated = await crud_event.update(session, db_obj=db_event, obj_in=event_in)

    # Notify when event is published
    if old_status != "published" and updated.status == "published":
        from app.logic.notifications.triggers import dispatch_event_published

        background_tasks.add_task(
            dispatch_event_published,
            event_id=updated.id,
            event_name=updated.name,
            event_group_id=updated.event_group_id,
        )

    return updated


@router.get("/{event_id}/bookings", response_model=list[EventBookingEntry])
async def list_event_bookings(
    event_id: str,
    session: DBDep,
    _current_user: CurrentUser,
) -> list[EventBookingEntry]:
    """List all confirmed bookings for every slot in an event, with user info."""
    import uuid as _uuid

    await crud_event.get(session, event_id, raise_404_error=True)
    bookings = await crud_booking.get_confirmed_by_event(
        session, event_id=_uuid.UUID(event_id)
    )
    return [
        EventBookingEntry(
            id=b.id,
            duty_slot_id=b.duty_slot_id,  # type: ignore[arg-type]
            user_name=b.user.name if b.user else None,
            user_phone_number=b.user.phone_number if b.user else None,
        )
        for b in bookings
    ]


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: str,
    session: DBDep,
    current_user: CurrentUser,
    cancellation_reason: str | None = Query(default=None),
) -> None:
    db_event = await crud_event.get(session, event_id, raise_404_error=True)
    await require_event_group_access(current_user, session, db_event.event_group_id)

    # Collect all slot IDs for this event
    stmt = select(col(DutySlot.id)).where(col(DutySlot.event_id) == db_event.id)
    result = await session.execute(stmt)
    slot_ids = list(result.scalars().all())

    # Cancel confirmed bookings with snapshot before deleting
    await crud_booking.cancel_bookings_for_slots(
        session,
        slot_ids=slot_ids,
        event_name=db_event.name,
        cancellation_reason=cancellation_reason,
    )

    await session.delete(db_event)
    await session.commit()
