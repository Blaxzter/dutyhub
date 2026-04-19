import datetime as dt
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func as sa_func
from sqlalchemy import select as sa_select
from sqlalchemy import update as sa_update
from sqlmodel import col

from app.api.deps import CurrentGlobalManager, CurrentSuperuser, CurrentUser, DBDep
from app.core.errors import raise_problem
from app.crud.event import event as crud_event
from app.crud.event_manager import event_manager as crud_egm
from app.crud.user import user as crud_user
from app.crud.user_availability import user_availability as crud_availability
from app.logic.permissions import require_event_access
from app.models.duty_slot import DutySlot
from app.models.event import Event
from app.models.event_manager import EventManager
from app.models.slot_batch import SlotBatch
from app.models.task import Task
from app.models.user import User as UserModel
from app.models.user_availability import UserAvailabilityDate
from app.schemas.event import (
    EventCreate,
    EventListResponse,
    EventRead,
    EventStatus,
    EventUpdate,
)
from app.schemas.user import UserRead
from app.schemas.user_availability import (
    UserAvailabilityCreate,
    UserAvailabilityRead,
    UserAvailabilityWithUser,
)

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/", response_model=EventListResponse)
async def list_events(
    session: DBDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    search: str | None = None,
    status: EventStatus | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> EventListResponse:
    """List published task groups (all users) or all groups (admin/manager).

    Scoped group managers see published groups plus their managed groups
    regardless of status.
    """
    effective_status = status
    also_include_ids: list[uuid.UUID] | None = None

    if current_user.is_manager:
        # Global admin/task_manager — see everything
        pass
    else:
        # Check if user is a scoped group manager
        result = await session.execute(
            sa_select(col(EventManager.event_id)).where(
                col(EventManager.user_id) == current_user.id
            )
        )
        managed_ids = list(result.scalars().all())

        if effective_status is None:
            effective_status = "published"
        if managed_ids:
            also_include_ids = managed_ids

    filter_kwargs: dict[str, Any] = {
        "search": search,
        "status": effective_status,
        "date_from": date_from,
        "date_to": date_to,
        "also_include_ids": also_include_ids,
    }

    items = await crud_event.get_multi_filtered(
        session,
        skip=skip,
        limit=limit,
        **filter_kwargs,
    )
    total = await crud_event.get_count_filtered(
        session,
        **filter_kwargs,
    )
    return EventListResponse(
        items=[EventRead.model_validate(i) for i in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{group_id}", response_model=EventRead)
async def get_event(
    group_id: uuid.UUID,
    session: DBDep,
    current_user: CurrentUser,
) -> Event:
    db_group = await crud_event.get(session, group_id, raise_404_error=True)
    if not current_user.is_manager and db_group.status != "published":
        # Allow scoped group managers to see their own unpublished groups
        is_scoped = await crud_egm.is_manager(
            session, user_id=current_user.id, event_id=group_id
        )
        if not is_scoped:
            raise_problem(
                403,
                code="event.not_published",
                detail="Task group is not published",
            )
    return db_group


@router.post("/", response_model=EventRead, status_code=201)
async def create_event(
    group_in: EventCreate,
    session: DBDep,
    current_user: CurrentGlobalManager,
) -> Event:
    group_in.created_by_id = current_user.id
    return await crud_event.create(session, obj_in=group_in)


@router.patch("/{group_id}", response_model=EventRead)
async def update_event(
    group_id: uuid.UUID,
    group_in: EventUpdate,
    session: DBDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> Event:
    db_group = await crud_event.get(session, group_id, raise_404_error=True)
    await require_event_access(current_user, session, db_group.id)

    # Validate date range against existing tasks
    new_start = group_in.start_date or db_group.start_date
    new_end = group_in.end_date or db_group.end_date
    if new_end < new_start:
        raise_problem(
            422,
            code="event.invalid_dates",
            detail="End date must be on or after start date",
        )
    if group_in.start_date is not None or group_in.end_date is not None:
        result = await session.execute(
            sa_select(
                sa_func.min(col(Task.start_date)),
                sa_func.max(col(Task.end_date)),
            ).where(col(Task.event_id) == group_id)
        )
        row = result.one()
        earliest_task, latest_task = row[0], row[1]
        if earliest_task is not None and new_start > earliest_task:
            raise_problem(
                422,
                code="event.date_range_conflict",
                detail=f"Cannot set start date after {earliest_task.isoformat()} — an task starts on that date",
            )
        if latest_task is not None and new_end < latest_task:
            raise_problem(
                422,
                code="event.date_range_conflict",
                detail=f"Cannot set end date before {latest_task.isoformat()} — an task ends on that date",
            )

    old_status = db_group.status
    updated = await crud_event.update(session, db_obj=db_group, obj_in=group_in)

    # Notify when task group is published
    if old_status != "published" and updated.status == "published":
        from app.logic.notifications.triggers import dispatch_event_published

        background_tasks.add_task(
            dispatch_event_published,
            event_id=updated.id,
            event_name=updated.name,
        )

    return updated


@router.get("/{group_id}/task-date-bounds")
async def get_task_date_bounds(
    group_id: uuid.UUID,
    session: DBDep,
    _current_user: CurrentUser,
) -> dict[str, dt.date | None]:
    """Return the earliest task start and latest task end within this group."""
    await crud_event.get(session, group_id, raise_404_error=True)
    result = await session.execute(
        sa_select(
            sa_func.min(col(Task.start_date)),
            sa_func.max(col(Task.end_date)),
        ).where(col(Task.event_id) == group_id)
    )
    row = result.one()
    return {"earliest_start": row[0], "latest_end": row[1]}


class ShiftDatesRequest(BaseModel):
    new_start_date: dt.date


@router.post("/{group_id}/shift-dates", response_model=EventRead)
async def shift_event_dates(
    group_id: uuid.UUID,
    body: ShiftDatesRequest,
    session: DBDep,
    current_user: CurrentUser,
) -> Event:
    """Shift the entire task group and all its tasks/slots/availabilities by a date offset.

    The offset is calculated from the difference between the current group
    start_date and the provided new_start_date.
    """
    db_group = await crud_event.get(session, group_id, raise_404_error=True)
    await require_event_access(current_user, session, db_group.id)

    delta = body.new_start_date - db_group.start_date
    if delta.days == 0:
        return db_group

    # 1. Shift the task group itself
    db_group.start_date = db_group.start_date + delta
    db_group.end_date = db_group.end_date + delta
    session.add(db_group)

    # Get task IDs in this group
    task_ids_result = await session.execute(
        sa_select(col(Task.id)).where(col(Task.event_id) == group_id)
    )
    task_ids = list(task_ids_result.scalars().all())

    if task_ids:
        # 2. Shift tasks
        await session.execute(
            sa_update(Task)
            .where(col(Task.event_id) == group_id)
            .values(
                start_date=Task.start_date + delta,
                end_date=Task.end_date + delta,
            )
        )

        # 3. Shift slot_batches
        await session.execute(
            sa_update(SlotBatch)
            .where(col(SlotBatch.task_id).in_(task_ids))
            .values(
                start_date=SlotBatch.start_date + delta,
                end_date=SlotBatch.end_date + delta,
            )
        )

        # 4. Shift duty_slots
        await session.execute(
            sa_update(DutySlot)
            .where(col(DutySlot.task_id).in_(task_ids))
            .values(date=DutySlot.date + delta)
        )

        # 5. Shift schedule_overrides in tasks and slot_batches (JSON with date keys)
        if delta.days != 0:
            tasks_with_overrides = (
                (
                    await session.execute(
                        sa_select(Task).where(
                            col(Task.id).in_(task_ids),
                            col(Task.schedule_overrides).isnot(None),
                        )
                    )
                )
                .scalars()
                .all()
            )
            for ev in tasks_with_overrides:
                ev.schedule_overrides = _shift_overrides(ev.schedule_overrides, delta)
                session.add(ev)

            batches_with_overrides = (
                (
                    await session.execute(
                        sa_select(SlotBatch).where(
                            col(SlotBatch.task_id).in_(task_ids),
                            col(SlotBatch.schedule_overrides).isnot(None),
                        )
                    )
                )
                .scalars()
                .all()
            )
            for batch in batches_with_overrides:
                batch.schedule_overrides = _shift_overrides(
                    batch.schedule_overrides, delta
                )
                session.add(batch)

    # 6. Shift user availability dates for this group
    from app.models.user_availability import UserAvailability

    avail_ids_result = await session.execute(
        sa_select(col(UserAvailability.id)).where(
            col(UserAvailability.event_id) == group_id
        )
    )
    avail_ids = list(avail_ids_result.scalars().all())
    if avail_ids:
        await session.execute(
            sa_update(UserAvailabilityDate)
            .where(col(UserAvailabilityDate.availability_id).in_(avail_ids))
            .values(slot_date=UserAvailabilityDate.slot_date + delta)
        )

    await session.flush()
    await session.refresh(db_group)
    return db_group


def _shift_overrides(
    overrides: list[dict[str, object]] | None,
    delta: dt.timedelta,
) -> list[dict[str, object]]:
    """Shift the 'date' key in each schedule override entry."""
    if not overrides:
        return overrides or []
    shifted: list[dict[str, object]] = []
    for entry in overrides:
        new_entry = dict(entry)
        if "date" in new_entry and isinstance(new_entry["date"], str):
            try:
                d = dt.date.fromisoformat(new_entry["date"])
                new_entry["date"] = (d + delta).isoformat()
            except ValueError:
                pass
        shifted.append(new_entry)
    return shifted


@router.delete("/{group_id}", status_code=204)
async def delete_event(
    group_id: uuid.UUID,
    session: DBDep,
    current_user: CurrentUser,
) -> None:
    db_group = await crud_event.get(session, group_id, raise_404_error=True)
    await require_event_access(current_user, session, db_group.id)
    await session.delete(db_group)
    await session.commit()


# --- Availability endpoints ---


@router.get("/{group_id}/availabilities", response_model=list[UserAvailabilityWithUser])
async def list_group_availabilities(
    group_id: uuid.UUID,
    session: DBDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
) -> list[UserAvailabilityWithUser]:
    """List all user availabilities for this task group (managers only)."""
    await crud_event.get(session, group_id, raise_404_error=True)
    await require_event_access(current_user, session, group_id)
    availabilities = await crud_availability.get_multi_by_group(
        session, event_id=group_id, skip=skip, limit=limit
    )

    user_ids = [a.user_id for a in availabilities]
    users_map: dict[uuid.UUID, UserModel] = {}
    if user_ids:
        result = await session.execute(
            sa_select(UserModel).where(UserModel.id.in_(user_ids))  # type: ignore[attr-defined]
        )
        users_map = {u.id: u for u in result.scalars().all()}

    return [
        UserAvailabilityWithUser(
            **UserAvailabilityRead.model_validate(avail).model_dump(),
            user_full_name=(
                users_map[avail.user_id].name if avail.user_id in users_map else None
            ),
            user_email=(
                users_map[avail.user_id].email if avail.user_id in users_map else None
            ),
        )
        for avail in availabilities
    ]


@router.get("/{group_id}/availability/me", response_model=UserAvailabilityRead)
async def get_my_availability(
    group_id: uuid.UUID,
    session: DBDep,
    current_user: CurrentUser,
) -> UserAvailabilityRead:
    avail = await crud_availability.get_by_user_and_group(
        session,
        user_id=current_user.id,
        event_id=group_id,
    )
    if not avail:
        raise_problem(
            404,
            code="availability.not_found",
            detail="No availability registered",
        )
    return UserAvailabilityRead.model_validate(avail)


@router.post(
    "/{group_id}/availability",
    response_model=UserAvailabilityRead,
    status_code=201,
)
async def set_my_availability(
    group_id: uuid.UUID,
    avail_in: UserAvailabilityCreate,
    session: DBDep,
    current_user: CurrentUser,
) -> UserAvailabilityRead:
    await crud_event.get(session, group_id, raise_404_error=True)
    await crud_availability.upsert_for_user(
        session,
        user_id=current_user.id,
        event_id=group_id,
        obj_in=avail_in,
    )
    await session.flush()
    # Re-fetch after flush to get eagerly-loaded available_dates
    avail = await crud_availability.get_by_user_and_group(
        session,
        user_id=current_user.id,
        event_id=group_id,
    )
    return UserAvailabilityRead.model_validate(avail)


@router.delete("/{group_id}/availability/me", status_code=204)
async def delete_my_availability(
    group_id: uuid.UUID,
    session: DBDep,
    current_user: CurrentUser,
) -> None:
    deleted = await crud_availability.delete_for_user(
        session,
        user_id=current_user.id,
        event_id=group_id,
    )
    if not deleted:
        raise_problem(
            404,
            code="availability.not_found",
            detail="No availability registered",
        )
    await session.commit()


# --- Manager assignment endpoints ---


@router.get("/{group_id}/managers", response_model=list[UserRead])
async def list_group_managers(
    group_id: uuid.UUID,
    session: DBDep,
    current_user: CurrentUser,
) -> list[UserRead]:
    """List all assigned managers for this task group."""
    await crud_event.get(session, group_id, raise_404_error=True)
    await require_event_access(current_user, session, group_id)
    assignments = await crud_egm.get_by_group(session, event_id=group_id)
    user_ids = [a.user_id for a in assignments]
    if not user_ids:
        return []
    result = await session.execute(
        sa_select(UserModel).where(UserModel.id.in_(user_ids))  # type: ignore[attr-defined]
    )
    return [UserRead.model_validate(u) for u in result.scalars().all()]


@router.post("/{group_id}/managers/{user_id}", response_model=UserRead, status_code=201)
async def assign_group_manager(
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    session: DBDep,
    _current_user: CurrentSuperuser,
) -> UserRead:
    """Admin-only: assign a user as manager of this task group."""
    await crud_event.get(session, group_id, raise_404_error=True)
    user = await crud_user.get(session, id=user_id, raise_404_error=True)
    await crud_egm.assign(session, user_id=user_id, event_id=group_id)
    return UserRead.model_validate(user)


@router.delete("/{group_id}/managers/{user_id}", status_code=204)
async def remove_group_manager(
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    session: DBDep,
    _current_user: CurrentSuperuser,
) -> None:
    """Admin-only: remove a user as manager of this task group."""
    await crud_event.get(session, group_id, raise_404_error=True)
    removed = await crud_egm.remove(session, user_id=user_id, event_id=group_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manager assignment not found",
        )
