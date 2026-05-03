# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false
# SQLAlchemy column-level selects produce types that basedpyright cannot resolve.
import datetime as dt
import uuid

from fastapi import APIRouter
from sqlalchemy import and_, func, or_, select
from sqlmodel import col

from app.api.deps import CurrentUser, DBDep
from app.crud.event import event as crud_event
from app.crud.task import task as crud_task
from app.logic.event_scope import get_user_event_scope
from app.models.booking import Booking
from app.models.event import Event
from app.models.event_manager import EventManager
from app.models.shift import Shift
from app.models.task import Task
from app.models.user import User
from app.schemas.dashboard import (
    DashboardBookingItem,
    DashboardEvent,
    DashboardFeedResponse,
    DashboardTask,
)
from app.schemas.sidebar import (
    SidebarBooking,
    SidebarEvent,
    SidebarResponse,
    SidebarTask,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


async def _get_visibility_filters(
    session,
    user: User,  # noqa: ANN001
) -> tuple[str | None, list[uuid.UUID] | None]:
    """Return (effective_status, managed_group_ids) for the current user."""
    if user.is_manager:
        return None, None  # global admin/task_manager — see everything
    result = await session.execute(
        select(col(EventManager.event_id)).where(col(EventManager.user_id) == user.id)
    )
    managed_ids: list[uuid.UUID] = list(result.scalars().all())
    return "published", managed_ids or None


@router.get("/feed", response_model=DashboardFeedResponse)
async def dashboard_feed(
    session: DBDep,
    current_user: CurrentUser,
) -> DashboardFeedResponse:
    """Single endpoint powering the /app/home dashboard."""
    effective_status, managed_group_ids = await _get_visibility_filters(
        session, current_user
    )
    now = dt.datetime.now()
    today = now.date()

    # Tasks + count (only current/future)
    tasks_list, task_count, groups_list = await _load_tasks_and_groups(
        session, effective_status, today, now, managed_group_ids
    )

    # User's upcoming confirmed bookings with shift info (single query, no N+1)
    bookings, booking_count = await _load_bookings(
        session, current_user.id, today, now.time()
    )

    # Pending user count (admin only)
    pending_user_count = None
    if current_user.is_admin:
        pending_user_count = await _count_pending_users(session)

    return DashboardFeedResponse(
        tasks=[DashboardTask.model_validate(e) for e in tasks_list],
        task_count=task_count,
        events=[DashboardEvent.model_validate(g) for g in groups_list],
        bookings=bookings,
        booking_count=booking_count,
        pending_user_count=pending_user_count,
    )


async def _load_tasks_and_groups(  # noqa: ANN001, ANN202
    session,
    effective_status,
    today: dt.date,
    now: dt.datetime,
    managed_group_ids: list[uuid.UUID] | None = None,
):
    tasks_list = await crud_task.get_multi_filtered(
        session,
        limit=100,
        status=effective_status,
        date_from=today,
        has_future_shifts=now,
        also_include_group_ids=managed_group_ids,
    )
    task_count = await crud_task.get_count_filtered(
        session,
        status=effective_status,
        date_from=today,
        has_future_shifts=now,
        also_include_group_ids=managed_group_ids,
    )
    groups_list = await crud_event.get_multi_filtered(
        session,
        limit=100,
        status=effective_status,
        also_include_ids=managed_group_ids,
    )
    return tasks_list, task_count, groups_list


async def _load_bookings(
    session,
    user_id,
    today: dt.date,
    now_time: dt.time,  # noqa: ANN001
) -> tuple[list[DashboardBookingItem], int]:
    """Fetch upcoming confirmed bookings joined with shift data in a single query."""
    future_cond = _future_shift_condition(today, now_time)
    query = (
        select(
            col(Booking.id),
            col(Shift.id).label("slot_id"),
            col(Shift.date),
            col(Shift.title),
            col(Shift.start_time),
            col(Shift.end_time),
        )
        .join(Shift, col(Booking.shift_id) == col(Shift.id))
        .where(
            col(Booking.user_id) == user_id,
            col(Booking.status) == "confirmed",
            future_cond,
        )
        .order_by(col(Shift.date), col(Shift.start_time))
        .limit(200)
    )
    result = await session.execute(query)
    rows = result.all()
    items = [
        DashboardBookingItem(
            id=row.id,
            slot_id=row.slot_id,
            date=row.date,
            title=row.title,
            start_time=row.start_time,
            end_time=row.end_time,
        )
        for row in rows
    ]

    # Count (also only upcoming)
    count_query = (
        select(func.count())
        .select_from(Booking)
        .join(Shift, col(Booking.shift_id) == col(Shift.id))
        .where(
            col(Booking.user_id) == user_id,
            col(Booking.status) == "confirmed",
            future_cond,
        )
    )
    count_result = await session.execute(count_query)
    total = count_result.scalar_one()

    return items, total


async def _count_pending_users(session) -> int:  # noqa: ANN001
    query = (
        select(func.count())
        .select_from(User)
        .where(
            col(User.is_active) == False,  # noqa: E712
            col(User.rejection_reason).is_(None),
        )
    )
    result = await session.execute(query)
    return result.scalar_one()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _future_shift_condition(today: dt.date, now_time: dt.time | None = None):  # noqa: ANN202
    """Shift is in the future: date > today, or date == today and start_time >= now."""
    if now_time is not None:
        return or_(
            col(Shift.date) > today,
            and_(
                col(Shift.date) == today,
                or_(
                    col(Shift.start_time).is_(None),
                    col(Shift.start_time) >= now_time,
                ),
            ),
        )
    return col(Shift.date) >= today


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


@router.get("/sidebar", response_model=SidebarResponse)
async def dashboard_sidebar(
    session: DBDep,
    current_user: CurrentUser,
) -> SidebarResponse:
    """Lightweight data for sidebar quick-links."""
    now = dt.datetime.now()
    today = now.date()
    now_time = now.time()
    effective_status, managed_group_ids = await _get_visibility_filters(
        session, current_user
    )

    scoped_event_id = get_user_event_scope(current_user)

    groups = await _sidebar_events(session, today, effective_status, managed_group_ids)
    tasks = await _sidebar_tasks(
        session,
        today,
        now_time,
        effective_status,
        managed_group_ids,
        event_id=scoped_event_id,
    )
    bookings = await _sidebar_bookings(
        session,
        current_user.id,
        today,
        now_time,
        event_id=scoped_event_id,
    )

    return SidebarResponse(
        events=groups,
        tasks=tasks,
        bookings=bookings,
    )


async def _sidebar_events(  # noqa: ANN001
    session,
    today: dt.date,
    status: str | None,
    managed_group_ids: list[uuid.UUID] | None = None,
) -> list[SidebarEvent]:
    """Published groups (+ managed groups) whose end_date >= today, limit 5."""
    query = (
        select(col(Event.id), col(Event.name), col(Event.status))
        .where(col(Event.end_date) >= today)
        .order_by(col(Event.start_date))
        .limit(5)
    )
    if status:
        status_filter = col(Event.status) == status
        if managed_group_ids:
            status_filter = or_(status_filter, col(Event.id).in_(managed_group_ids))
        query = query.where(status_filter)
    result = await session.execute(query)
    return [SidebarEvent(id=r.id, name=r.name, status=r.status) for r in result.all()]


async def _sidebar_tasks(  # noqa: ANN001
    session,
    today: dt.date,
    now_time: dt.time,
    status: str | None,
    managed_group_ids: list[uuid.UUID] | None = None,
    event_id: uuid.UUID | None = None,
) -> list[SidebarTask]:
    """Published tasks with open-shift count and next shift date, limit 10.

    Scoped to ``event_id`` when provided so the sidebar matches the user's
    selected event.
    """
    future_cond = _future_shift_condition(today, now_time)

    # Subquery: confirmed booking count per shift
    booking_count_sq = (
        select(func.count())
        .select_from(Booking)
        .where(
            col(Booking.shift_id) == col(Shift.id),
            col(Booking.status) == "confirmed",
        )
        .correlate(Shift)
        .scalar_subquery()
    )

    # Subquery: count of open shifts (future AND has capacity)
    open_shifts_sq = (
        select(func.count())
        .select_from(Shift)
        .where(
            col(Shift.task_id) == col(Task.id),
            future_cond,
            col(Shift.max_bookings) > booking_count_sq,
        )
        .correlate(Task)
        .scalar_subquery()
    )

    # Subquery: next open shift date
    next_shift_date_sq = (
        select(func.min(col(Shift.date)))
        .where(
            col(Shift.task_id) == col(Task.id),
            future_cond,
            col(Shift.max_bookings) > booking_count_sq,
        )
        .correlate(Task)
        .scalar_subquery()
    )

    # Subquery: start_time of next open shift (on that date)
    next_shift_time_sq = (
        select(func.min(col(Shift.start_time)))
        .where(
            col(Shift.task_id) == col(Task.id),
            col(Shift.date) == next_shift_date_sq,
            col(Shift.max_bookings) > booking_count_sq,
        )
        .correlate(Task)
        .scalar_subquery()
    )

    # Only tasks that have at least one future open shift
    has_open_shift_sq = select(col(Shift.task_id)).where(
        future_cond,
        col(Shift.max_bookings) > booking_count_sq,
    )

    query = (
        select(
            col(Task.id),
            col(Task.name),
            col(Task.status),
            open_shifts_sq.label("open_shifts"),
            next_shift_date_sq.label("next_shift_date"),
            next_shift_time_sq.label("next_shift_start_time"),
        )
        .where(
            col(Task.end_date) >= today,
            col(Task.id).in_(has_open_shift_sq),
        )
        .order_by(col(Task.start_date))
        .limit(10)
    )
    if status:
        status_filter = col(Task.status) == status
        if managed_group_ids:
            status_filter = or_(
                status_filter, col(Task.event_id).in_(managed_group_ids)
            )
        query = query.where(status_filter)
    if event_id is not None:
        query = query.where(col(Task.event_id) == event_id)

    result = await session.execute(query)
    return [
        SidebarTask(
            id=r.id,
            name=r.name,
            status=r.status,
            open_shifts=r.open_shifts or 0,
            next_shift_date=r.next_shift_date,
            next_shift_start_time=r.next_shift_start_time,
        )
        for r in result.all()
    ]


async def _sidebar_bookings(  # noqa: ANN001
    session,
    user_id,
    today: dt.date,
    now_time: dt.time,
    event_id: uuid.UUID | None = None,
) -> list[SidebarBooking]:
    """User's upcoming confirmed bookings, limit 5.

    Scoped to ``event_id`` when provided so the sidebar matches the
    event-scoped /bookings/me view.
    """
    future_cond = _future_shift_condition(today, now_time)
    query = (
        select(
            col(Booking.id),
            col(Shift.id).label("slot_id"),
            col(Shift.task_id),
            col(Shift.title).label("slot_title"),
            col(Shift.date).label("slot_date"),
            col(Shift.start_time).label("slot_start_time"),
        )
        .join(Shift, col(Booking.shift_id) == col(Shift.id))
        .where(
            col(Booking.user_id) == user_id,
            col(Booking.status) == "confirmed",
            future_cond,
        )
        .order_by(col(Shift.date), col(Shift.start_time))
        .limit(5)
    )
    if event_id is not None:
        query = query.where(
            col(Shift.task_id).in_(
                select(col(Task.id)).where(col(Task.event_id) == event_id)
            )
        )
    result = await session.execute(query)
    return [
        SidebarBooking(
            id=r.id,
            slot_id=r.slot_id,
            task_id=r.task_id,
            slot_title=r.slot_title,
            slot_date=r.slot_date,
            slot_start_time=r.slot_start_time,
        )
        for r in result.all()
    ]
