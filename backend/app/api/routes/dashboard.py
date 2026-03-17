# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownArgumentType=false
# SQLAlchemy column-level selects produce types that basedpyright cannot resolve.
from fastapi import APIRouter
from sqlalchemy import func, select
from sqlmodel import col

from app.api.deps import CurrentUser, DBDep
from app.crud.event import event as crud_event
from app.crud.event_group import event_group as crud_event_group
from app.models.booking import Booking
from app.models.duty_slot import DutySlot
from app.models.user import User
from app.schemas.dashboard import (
    DashboardBookingItem,
    DashboardEvent,
    DashboardEventGroup,
    DashboardFeedResponse,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/feed", response_model=DashboardFeedResponse)
async def dashboard_feed(
    session: DBDep,
    current_user: CurrentUser,
) -> DashboardFeedResponse:
    """Single endpoint powering the /app/home dashboard."""
    effective_status = None if current_user.is_admin else "published"

    # Events + count
    events_list, event_count, groups_list = await _load_events_and_groups(
        session, effective_status
    )

    # User's confirmed bookings with slot info (single query, no N+1)
    bookings, booking_count = await _load_bookings(session, current_user.id)

    # Pending user count (admin only)
    pending_user_count = None
    if current_user.is_admin:
        pending_user_count = await _count_pending_users(session)

    return DashboardFeedResponse(
        events=[DashboardEvent.model_validate(e) for e in events_list],
        event_count=event_count,
        event_groups=[DashboardEventGroup.model_validate(g) for g in groups_list],
        bookings=bookings,
        booking_count=booking_count,
        pending_user_count=pending_user_count,
    )


async def _load_events_and_groups(session, effective_status):  # noqa: ANN001, ANN202
    events_list = await crud_event.get_multi_filtered(
        session, limit=100, status=effective_status
    )
    event_count = await crud_event.get_count_filtered(
        session, status=effective_status
    )
    groups_list = await crud_event_group.get_multi_filtered(
        session, limit=100, status=effective_status
    )
    return events_list, event_count, groups_list


async def _load_bookings(
    session, user_id,  # noqa: ANN001
) -> tuple[list[DashboardBookingItem], int]:
    """Fetch confirmed bookings joined with slot data in a single query."""
    query = (
        select(
            col(Booking.id),
            col(DutySlot.id).label("slot_id"),
            col(DutySlot.date),
            col(DutySlot.title),
            col(DutySlot.start_time),
            col(DutySlot.end_time),
        )
        .join(DutySlot, col(Booking.duty_slot_id) == col(DutySlot.id))
        .where(
            col(Booking.user_id) == user_id,
            col(Booking.status) == "confirmed",
        )
        .order_by(col(DutySlot.date), col(DutySlot.start_time))
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

    # Count
    count_query = (
        select(func.count())
        .select_from(Booking)
        .where(
            col(Booking.user_id) == user_id,
            col(Booking.status) == "confirmed",
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
