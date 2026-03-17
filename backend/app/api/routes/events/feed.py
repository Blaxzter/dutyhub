# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false
# SQLAlchemy column-level selects produce types that basedpyright cannot resolve.
import datetime as dt
import uuid
from collections import defaultdict

from fastapi import APIRouter, Query
from sqlalchemy import case, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.api.deps import CurrentUser, DBDep
from app.core.errors import raise_problem
from app.crud.event import event as crud_event
from app.models.booking import Booking
from app.models.duty_slot import DutySlot
from app.models.event import Event
from app.schemas.event import EventRead
from app.schemas.feed import (
    EventFeedResponse,
    FeedEventItem,
    FeedFocusMode,
    FeedSlotEntry,
    FeedView,
    SlotWindowResponse,
)

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
        col(DutySlot.event_id),
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
    event_ids: list[uuid.UUID],
    user_id: uuid.UUID,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> list[tuple[uuid.UUID, FeedSlotEntry]]:
    """Return (event_id, FeedSlotEntry) pairs for slots in the given window."""
    if not event_ids:
        return []

    cnt_sub = _booking_count_sub()
    my_exists = _my_booking_exists(user_id)
    query = _slot_select(cnt_sub, my_exists).where(
        col(DutySlot.event_id).in_(event_ids)
    )

    if date_from is not None:
        query = query.where(col(DutySlot.date) >= date_from)
    if date_to is not None:
        query = query.where(col(DutySlot.date) <= date_to)

    query = query.order_by(col(DutySlot.date), col(DutySlot.start_time))
    result = await session.execute(query)
    return [(row.event_id, _row_to_slot(row)) for row in result.all()]


async def _query_slots_first_available(
    session: AsyncSession,
    event_ids: list[uuid.UUID],
    user_id: uuid.UUID,
    today: dt.date,
    days: int,
) -> tuple[dict[uuid.UUID, list[FeedSlotEntry]], dict[uuid.UUID, dt.date]]:
    """For first-available mode: per-event 5-day window starting from the first slot date.

    Returns (slots_by_event, window_starts).
    """
    # CTE: first slot date >= today per event
    first_dates_cte = (
        select(
            col(DutySlot.event_id),
            func.min(col(DutySlot.date)).label("first_date"),
        )
        .where(
            col(DutySlot.event_id).in_(event_ids),
            col(DutySlot.date) >= today,
        )
        .group_by(col(DutySlot.event_id))
        .cte("first_dates")
    )

    cnt_sub = _booking_count_sub()
    my_exists = _my_booking_exists(user_id)

    query = (
        _slot_select(cnt_sub, my_exists)
        .join(first_dates_cte, col(DutySlot.event_id) == first_dates_cte.c.event_id)
        .where(
            col(DutySlot.date) >= first_dates_cte.c.first_date,
            col(DutySlot.date) <= first_dates_cte.c.first_date + (days - 1),
        )
        .order_by(col(DutySlot.date), col(DutySlot.start_time))
    )

    result = await session.execute(query)
    slots_by_event: dict[uuid.UUID, list[FeedSlotEntry]] = defaultdict(list)
    window_starts: dict[uuid.UUID, dt.date] = {}
    for row in result.all():
        slots_by_event[row.event_id].append(_row_to_slot(row))

    # Derive window starts from the CTE result (query it once more, lightweight)
    fd_query = select(
        first_dates_cte.c.event_id,
        first_dates_cte.c.first_date,
    )
    fd_result = await session.execute(fd_query)
    for row in fd_result.all():
        window_starts[row.event_id] = row.first_date

    return dict(slots_by_event), window_starts


async def _get_aggregated_stats(
    session: AsyncSession,
    event_ids: list[uuid.UUID],
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> dict[uuid.UUID, tuple[int, int]]:
    """Return {event_id: (total_slots, available_slots)}."""
    if not event_ids:
        return {}

    cnt_sub = _booking_count_sub()

    query = (
        select(
            col(DutySlot.event_id),
            func.count().label("total_slots"),
            func.sum(
                case(
                    (func.coalesce(cnt_sub.c.cnt, 0) < col(DutySlot.max_bookings), 1),
                    else_=0,
                )
            ).label("available_slots"),
        )
        .outerjoin(cnt_sub, col(DutySlot.id) == cnt_sub.c.duty_slot_id)
        .where(col(DutySlot.event_id).in_(event_ids))
    )

    if date_from is not None:
        query = query.where(col(DutySlot.date) >= date_from)
    if date_to is not None:
        query = query.where(col(DutySlot.date) <= date_to)

    query = query.group_by(col(DutySlot.event_id))
    result = await session.execute(query)
    return {
        row.event_id: (row.total_slots, int(row.available_slots or 0))
        for row in result.all()
    }


# ---------------------------------------------------------------------------
# Builders per view
# ---------------------------------------------------------------------------


async def _build_list_feed(
    session: AsyncSession,
    events: list[Event],
    event_ids: list[uuid.UUID],
    user_id: uuid.UUID,
    focus_mode: FeedFocusMode,
    days: int,
) -> list[FeedEventItem]:
    today = dt.date.today()

    if focus_mode == "first_available":
        slots_by_event, window_starts = await _query_slots_first_available(
            session, event_ids, user_id, today, days
        )
    else:
        # today-centered: shared window for all events
        date_from = today
        date_to = today + dt.timedelta(days=days - 1)
        pairs = await _query_slots_with_bookings(
            session, event_ids, user_id, date_from, date_to
        )
        slots_by_event: dict[uuid.UUID, list[FeedSlotEntry]] = defaultdict(list)
        for eid, entry in pairs:
            slots_by_event[eid].append(entry)
        window_starts = dict.fromkeys(event_ids, today)

    items: list[FeedEventItem] = []
    for ev in events:
        ev_read = EventRead.model_validate(ev)
        items.append(
            FeedEventItem(
                **ev_read.model_dump(),
                slots=slots_by_event.get(ev.id, []),
                slot_window_start=window_starts.get(ev.id),
            )
        )
    return items


async def _build_aggregated_feed(
    session: AsyncSession,
    events: list[Event],
    event_ids: list[uuid.UUID],
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> list[FeedEventItem]:
    stats = await _get_aggregated_stats(session, event_ids, date_from, date_to)

    items: list[FeedEventItem] = []
    for ev in events:
        ev_read = EventRead.model_validate(ev)
        total, available = stats.get(ev.id, (0, 0))
        items.append(
            FeedEventItem(
                **ev_read.model_dump(),
                total_slots=total,
                available_slots=available,
            )
        )
    return items


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/feed", response_model=EventFeedResponse)
async def event_feed(
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
) -> EventFeedResponse:
    """Unified feed endpoint — returns events with view-specific embedded data."""
    effective_status = None if current_user.is_admin else "published"
    booked_by_user_id = str(current_user.id) if my_bookings else None

    # For calendar view, also filter events by date overlap
    ev_date_from = date_from if view == "calendar" else None
    ev_date_to = date_to if view == "calendar" else None

    events = await crud_event.get_multi_filtered(
        session,
        skip=skip,
        limit=limit,
        search=search,
        status=effective_status,
        booked_by_user_id=booked_by_user_id,
        date_from=ev_date_from,
        date_to=ev_date_to,
    )
    total = await crud_event.get_count_filtered(
        session,
        search=search,
        status=effective_status,
        booked_by_user_id=booked_by_user_id,
        date_from=ev_date_from,
        date_to=ev_date_to,
    )

    if not events:
        return EventFeedResponse(items=[], total=total, skip=skip, limit=limit)

    event_ids = [e.id for e in events]

    if view == "list":
        items = await _build_list_feed(
            session, events, event_ids, current_user.id, focus_mode, days
        )
    else:
        # cards and calendar both get aggregated stats
        items = await _build_aggregated_feed(
            session, events, event_ids, date_from, date_to
        )

    return EventFeedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{event_id}/slot-window", response_model=SlotWindowResponse)
async def get_slot_window(
    event_id: str,
    session: DBDep,
    current_user: CurrentUser,
    start_date: dt.date = Query(...),
    days: int = Query(default=5, ge=1, le=31),
) -> SlotWindowResponse:
    """Get slots for a single event within a date window (for next/prev navigation)."""
    db_event = await crud_event.get(session, event_id, raise_404_error=True)
    if not current_user.is_admin and db_event.status != "published":
        raise_problem(403, code="event.not_published", detail="Event is not published")

    end_date = start_date + dt.timedelta(days=days - 1)
    pairs = await _query_slots_with_bookings(
        session,
        event_ids=[db_event.id],
        user_id=current_user.id,
        date_from=start_date,
        date_to=end_date,
    )

    return SlotWindowResponse(
        slots=[entry for _, entry in pairs],
        start_date=start_date,
        days=days,
    )
