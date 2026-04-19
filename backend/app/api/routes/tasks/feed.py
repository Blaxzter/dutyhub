# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false
# SQLAlchemy column-level selects produce types that basedpyright cannot resolve.
import datetime as dt
import uuid
from collections import defaultdict

from fastapi import APIRouter, Query
from sqlalchemy import case, func, literal_column, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.api.deps import CurrentUser, DBDep
from app.core.errors import raise_problem
from app.crud.event_manager import event_manager as crud_egm
from app.crud.task import task as crud_task
from app.models.booking import Booking
from app.models.duty_slot import DutySlot
from app.models.event_manager import EventManager
from app.models.task import Task
from app.schemas.feed import (
    FeedFocusMode,
    FeedSlotEntry,
    FeedTaskItem,
    FeedView,
    SlotWindowResponse,
    TaskFeedResponse,
)
from app.schemas.task import TaskRead

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_slot(row) -> FeedSlotEntry:  # noqa: ANN001 – SA Row is untyped
    return FeedSlotEntry(
        id=row.id,
        date=row.date,
        start_time=row.start_time,
        end_time=row.end_time,
        max_bookings=row.max_bookings,
        current_bookings=row.current_bookings,
        is_booked_by_me=bool(row.is_booked_by_me),
    )


def _slot_select(cnt_sub, my_booking_exists):  # noqa: ANN001, ANN202
    """Base SELECT for duty-slot queries with booking counts."""
    return select(
        col(DutySlot.id),
        col(DutySlot.task_id),
        col(DutySlot.date),
        col(DutySlot.start_time),
        col(DutySlot.end_time),
        col(DutySlot.max_bookings),
        func.coalesce(cnt_sub.c.cnt, 0).label("current_bookings"),
        my_booking_exists.label("is_booked_by_me"),
    ).outerjoin(cnt_sub, col(DutySlot.id) == cnt_sub.c.duty_slot_id)


def _booking_count_sub():  # noqa: ANN202
    return (
        select(
            col(Booking.duty_slot_id),
            func.count().label("cnt"),
        )
        .where(col(Booking.status) == "confirmed")
        .group_by(col(Booking.duty_slot_id))
        .subquery("cnt_sub")
    )


def _my_booking_exists(user_id: uuid.UUID):  # noqa: ANN202
    return (
        select(literal_column("1"))
        .where(
            col(Booking.duty_slot_id) == col(DutySlot.id),
            col(Booking.user_id) == user_id,
            col(Booking.status) == "confirmed",
        )
        .correlate(DutySlot)
        .exists()
    )


async def _query_slots_with_bookings(
    session: AsyncSession,
    task_ids: list[uuid.UUID],
    user_id: uuid.UUID,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> list[tuple[uuid.UUID, FeedSlotEntry]]:
    """Return (task_id, FeedSlotEntry) pairs for slots in the given window."""
    if not task_ids:
        return []

    cnt_sub = _booking_count_sub()
    my_exists = _my_booking_exists(user_id)
    query = _slot_select(cnt_sub, my_exists).where(col(DutySlot.task_id).in_(task_ids))

    if date_from is not None:
        query = query.where(col(DutySlot.date) >= date_from)
    if date_to is not None:
        query = query.where(col(DutySlot.date) <= date_to)

    query = query.order_by(col(DutySlot.date), col(DutySlot.start_time))
    result = await session.execute(query)
    return [(row.task_id, _row_to_slot(row)) for row in result.all()]


async def _query_slots_first_available(
    session: AsyncSession,
    task_ids: list[uuid.UUID],
    user_id: uuid.UUID,
    today: dt.date,
    days: int,
) -> tuple[dict[uuid.UUID, list[FeedSlotEntry]], dict[uuid.UUID, dt.date]]:
    """For first-available mode: per-task 5-day window starting from the first slot date.

    Returns (slots_by_task, window_starts).
    """
    # CTE: first slot date >= today per task
    first_dates_cte = (
        select(
            col(DutySlot.task_id),
            func.min(col(DutySlot.date)).label("first_date"),
        )
        .where(
            col(DutySlot.task_id).in_(task_ids),
            col(DutySlot.date) >= today,
        )
        .group_by(col(DutySlot.task_id))
        .cte("first_dates")
    )

    cnt_sub = _booking_count_sub()
    my_exists = _my_booking_exists(user_id)

    query = (
        _slot_select(cnt_sub, my_exists)
        .join(first_dates_cte, col(DutySlot.task_id) == first_dates_cte.c.task_id)
        .where(
            col(DutySlot.date) >= first_dates_cte.c.first_date,
            col(DutySlot.date) <= first_dates_cte.c.first_date + (days - 1),
        )
        .order_by(col(DutySlot.date), col(DutySlot.start_time))
    )

    result = await session.execute(query)
    slots_by_task: dict[uuid.UUID, list[FeedSlotEntry]] = defaultdict(list)
    window_starts: dict[uuid.UUID, dt.date] = {}
    for row in result.all():
        slots_by_task[row.task_id].append(_row_to_slot(row))

    # Derive window starts from the CTE result (query it once more, lightweight)
    fd_query = select(
        first_dates_cte.c.task_id,
        first_dates_cte.c.first_date,
    )
    fd_result = await session.execute(fd_query)
    for row in fd_result.all():
        window_starts[row.task_id] = row.first_date

    return dict(slots_by_task), window_starts


async def _get_aggregated_stats(
    session: AsyncSession,
    task_ids: list[uuid.UUID],
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> dict[uuid.UUID, tuple[int, int]]:
    """Return {task_id: (total_slots, available_slots)}."""
    if not task_ids:
        return {}

    cnt_sub = _booking_count_sub()

    query = (
        select(
            col(DutySlot.task_id),
            func.count().label("total_slots"),
            func.sum(
                case(
                    (func.coalesce(cnt_sub.c.cnt, 0) < col(DutySlot.max_bookings), 1),
                    else_=0,
                )
            ).label("available_slots"),
        )
        .outerjoin(cnt_sub, col(DutySlot.id) == cnt_sub.c.duty_slot_id)
        .where(col(DutySlot.task_id).in_(task_ids))
    )

    if date_from is not None:
        query = query.where(col(DutySlot.date) >= date_from)
    if date_to is not None:
        query = query.where(col(DutySlot.date) <= date_to)

    query = query.group_by(col(DutySlot.task_id))
    result = await session.execute(query)
    return {
        row.task_id: (row.total_slots, int(row.available_slots or 0))
        for row in result.all()
    }


# ---------------------------------------------------------------------------
# Builders per view
# ---------------------------------------------------------------------------


async def _build_list_feed(
    session: AsyncSession,
    tasks: list[Task],
    task_ids: list[uuid.UUID],
    user_id: uuid.UUID,
    focus_mode: FeedFocusMode,
    days: int,
) -> list[FeedTaskItem]:
    today = dt.date.today()

    if focus_mode == "first_available":
        slots_by_task, window_starts = await _query_slots_first_available(
            session, task_ids, user_id, today, days
        )
    else:
        # today-centered: shared window for all tasks
        date_from = today
        date_to = today + dt.timedelta(days=days - 1)
        pairs = await _query_slots_with_bookings(
            session, task_ids, user_id, date_from, date_to
        )
        slots_by_task: dict[uuid.UUID, list[FeedSlotEntry]] = defaultdict(list)
        for eid, entry in pairs:
            slots_by_task[eid].append(entry)
        window_starts = dict.fromkeys(task_ids, today)

    items: list[FeedTaskItem] = []
    for ev in tasks:
        ev_read = TaskRead.model_validate(ev)
        items.append(
            FeedTaskItem(
                **ev_read.model_dump(),
                slots=slots_by_task.get(ev.id, []),
                slot_window_start=window_starts.get(ev.id),
            )
        )
    return items


async def _build_aggregated_feed(
    session: AsyncSession,
    tasks: list[Task],
    task_ids: list[uuid.UUID],
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> list[FeedTaskItem]:
    stats = await _get_aggregated_stats(session, task_ids, date_from, date_to)

    items: list[FeedTaskItem] = []
    for ev in tasks:
        ev_read = TaskRead.model_validate(ev)
        total, available = stats.get(ev.id, (0, 0))
        items.append(
            FeedTaskItem(
                **ev_read.model_dump(),
                total_slots=total,
                available_slots=available,
            )
        )
    return items


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/feed", response_model=TaskFeedResponse)
async def task_feed(
    session: DBDep,
    current_user: CurrentUser,
    view: FeedView = Query(default="list"),
    focus_mode: FeedFocusMode = Query(default="today"),
    search: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    my_bookings: bool = Query(default=False),
    days: int = Query(default=5, ge=1, le=31),
) -> TaskFeedResponse:
    """Unified feed endpoint — returns tasks with view-specific embedded data."""
    effective_status: str | None = None
    also_include_group_ids: list[uuid.UUID] | None = None

    if current_user.is_manager:
        pass  # global admin/task_manager — see everything
    else:
        result = await session.execute(
            select(col(EventManager.event_id)).where(
                col(EventManager.user_id) == current_user.id
            )
        )
        managed_ids: list[uuid.UUID] = list(result.scalars().all())
        effective_status = "published"
        if managed_ids:
            also_include_group_ids = managed_ids

    booked_by_user_id = str(current_user.id) if my_bookings else None

    today = dt.date.today()
    now = dt.datetime.now()
    ev_date_from = date_from if date_from else today
    ev_date_to = date_to if view == "calendar" else None
    # Only enforce future-slot filter when no explicit date_from is provided
    # (i.e. user hasn't picked a custom date range to look at past tasks)
    future_slots_cutoff = now if (not date_from and view != "calendar") else None

    tasks = await crud_task.get_multi_filtered(
        session,
        skip=skip,
        limit=limit,
        search=search,
        status=effective_status,
        booked_by_user_id=booked_by_user_id,
        date_from=ev_date_from,
        date_to=ev_date_to,
        has_future_slots=future_slots_cutoff,
        also_include_group_ids=also_include_group_ids,
    )
    total = await crud_task.get_count_filtered(
        session,
        search=search,
        status=effective_status,
        booked_by_user_id=booked_by_user_id,
        date_from=ev_date_from,
        date_to=ev_date_to,
        has_future_slots=future_slots_cutoff,
        also_include_group_ids=also_include_group_ids,
    )

    if not tasks:
        return TaskFeedResponse(items=[], total=total, skip=skip, limit=limit)

    task_ids = [e.id for e in tasks]

    if view == "list":
        items = await _build_list_feed(
            session, tasks, task_ids, current_user.id, focus_mode, days
        )
    else:
        # cards and calendar both get aggregated stats
        items = await _build_aggregated_feed(
            session, tasks, task_ids, date_from, date_to
        )

    return TaskFeedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/active-dates", response_model=list[dt.date])
async def task_active_dates(
    session: DBDep,
    current_user: CurrentUser,
    date_from: dt.date = Query(...),
    date_to: dt.date = Query(...),
) -> list[dt.date]:
    """Return distinct slot dates within a range where published tasks have slots."""
    query = (
        select(func.distinct(col(DutySlot.date)))
        .join(Task, col(DutySlot.task_id) == col(Task.id))
        .where(
            col(DutySlot.date) >= date_from,
            col(DutySlot.date) <= date_to,
        )
        .order_by(col(DutySlot.date))
    )

    if current_user.is_manager:
        pass  # global admin/task_manager — no status filter
    else:
        result = await session.execute(
            select(col(EventManager.event_id)).where(
                col(EventManager.user_id) == current_user.id
            )
        )
        managed_ids: list[uuid.UUID] = list(result.scalars().all())
        status_filter = col(Task.status) == "published"
        if managed_ids:
            status_filter = or_(status_filter, col(Task.event_id).in_(managed_ids))
        query = query.where(status_filter)

    result = await session.execute(query)
    return [row[0] for row in result.all()]


@router.get("/{task_id}/slot-window", response_model=SlotWindowResponse)
async def get_slot_window(
    task_id: str,
    session: DBDep,
    current_user: CurrentUser,
    start_date: dt.date = Query(...),
    days: int = Query(default=5, ge=1, le=31),
) -> SlotWindowResponse:
    """Get slots for a single task within a date window (for next/prev navigation)."""
    db_task = await crud_task.get(session, task_id, raise_404_error=True)
    if not current_user.is_manager and db_task.status != "published":
        if not db_task.event_id or not await crud_egm.is_manager(
            session, user_id=current_user.id, event_id=db_task.event_id
        ):
            raise_problem(
                403, code="task.not_published", detail="Task is not published"
            )

    end_date = start_date + dt.timedelta(days=days - 1)
    pairs = await _query_slots_with_bookings(
        session,
        task_ids=[db_task.id],
        user_id=current_user.id,
        date_from=start_date,
        date_to=end_date,
    )

    return SlotWindowResponse(
        slots=[entry for _, entry in pairs],
        start_date=start_date,
        days=days,
    )
