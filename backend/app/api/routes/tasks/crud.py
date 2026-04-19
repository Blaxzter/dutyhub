import uuid

from fastapi import APIRouter, BackgroundTasks, Query
from sqlalchemy import select
from sqlmodel import col

from app.api.deps import CurrentUser, DBDep
from app.core.errors import raise_problem
from app.crud.booking import booking as crud_booking
from app.crud.event_group_manager import event_group_manager as crud_egm
from app.crud.task import task as crud_task
from app.logic.permissions import require_event_group_access
from app.models.duty_slot import DutySlot
from app.models.event_group_manager import EventGroupManager
from app.models.task import Task
from app.schemas.booking import TaskBookingEntry
from app.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskRead,
    TaskStatus,
    TaskUpdate,
)

router = APIRouter()


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    session: DBDep,
    current_user: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    search: str | None = None,
    status: TaskStatus | None = None,
    my_bookings: bool = Query(default=False),
    event_group_id: uuid.UUID | None = Query(default=None),
) -> TaskListResponse:
    """List published tasks (all users) or all tasks (admin/manager).

    Scoped group managers see published tasks plus tasks in their managed groups.
    """
    effective_status = status
    also_include_group_ids = None

    if current_user.is_manager:
        # Global admin/task_manager — see everything
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

    items = await crud_task.get_multi_filtered(
        session,
        skip=skip,
        limit=limit,
        search=search,
        status=effective_status,
        booked_by_user_id=booked_by_user_id,
        also_include_group_ids=also_include_group_ids,
        event_group_id=event_group_id,
    )
    total = await crud_task.get_count_filtered(
        session,
        search=search,
        status=effective_status,
        booked_by_user_id=booked_by_user_id,
        also_include_group_ids=also_include_group_ids,
        event_group_id=event_group_id,
    )
    return TaskListResponse(
        items=[TaskRead.model_validate(i) for i in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: str,
    session: DBDep,
    current_user: CurrentUser,
) -> Task:
    db_task = await crud_task.get(session, task_id, raise_404_error=True)
    if not current_user.is_manager and db_task.status != "published":
        # Allow scoped group managers to see their unpublished tasks
        if not db_task.event_group_id or not await crud_egm.is_manager(
            session, user_id=current_user.id, event_group_id=db_task.event_group_id
        ):
            raise_problem(
                403, code="task.not_published", detail="Task is not published"
            )
    return db_task


@router.post("/", response_model=TaskRead, status_code=201)
async def create_task(
    task_in: TaskCreate,
    session: DBDep,
    current_user: CurrentUser,
) -> Task:
    await require_event_group_access(current_user, session, task_in.event_group_id)
    task_in.created_by_id = current_user.id
    return await crud_task.create(session, obj_in=task_in)


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: str,
    task_in: TaskUpdate,
    session: DBDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> Task:
    db_task = await crud_task.get(session, task_id, raise_404_error=True)
    await require_event_group_access(current_user, session, db_task.event_group_id)
    old_status = db_task.status
    updated = await crud_task.update(session, db_obj=db_task, obj_in=task_in)

    # Notify when task is published
    if old_status != "published" and updated.status == "published":
        from app.logic.notifications.triggers import dispatch_task_published

        background_tasks.add_task(
            dispatch_task_published,
            task_id=updated.id,
            task_name=updated.name,
            event_group_id=updated.event_group_id,
        )

    return updated


@router.get("/{task_id}/bookings", response_model=list[TaskBookingEntry])
async def list_task_bookings(
    task_id: str,
    session: DBDep,
    _current_user: CurrentUser,
) -> list[TaskBookingEntry]:
    """List all confirmed bookings for every slot in an task, with user info."""
    import uuid as _uuid

    await crud_task.get(session, task_id, raise_404_error=True)
    bookings = await crud_booking.get_confirmed_by_task(
        session, task_id=_uuid.UUID(task_id)
    )
    return [
        TaskBookingEntry(
            id=b.id,
            duty_slot_id=b.duty_slot_id,  # type: ignore[arg-type]
            user_name=b.user.name if b.user else None,
            user_phone_number=b.user.phone_number if b.user else None,
        )
        for b in bookings
    ]


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    session: DBDep,
    current_user: CurrentUser,
    cancellation_reason: str | None = Query(default=None),
) -> None:
    db_task = await crud_task.get(session, task_id, raise_404_error=True)
    await require_event_group_access(current_user, session, db_task.event_group_id)

    # Collect all slot IDs for this task
    stmt = select(col(DutySlot.id)).where(col(DutySlot.task_id) == db_task.id)
    result = await session.execute(stmt)
    slot_ids = list(result.scalars().all())

    # Cancel confirmed bookings with snapshot before deleting
    await crud_booking.cancel_bookings_for_slots(
        session,
        slot_ids=slot_ids,
        task_name=db_task.name,
        cancellation_reason=cancellation_reason,
    )

    await session.delete(db_task)
    await session.commit()
