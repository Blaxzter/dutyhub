from fastapi import APIRouter, Request, Response

from app.api.deps import CurrentUser, DBDep
from app.core.errors import raise_problem
from app.crud.booking import booking as crud_booking
from app.crud.calendar_feed import crud_calendar_feed
from app.logic.calendar_feed import build_calendar
from app.schemas.calendar_feed import CalendarFeedRead

router = APIRouter(prefix="/calendar", tags=["calendar"])


def _build_feed_url(request: Request, token: str) -> str:
    """Build the public feed URL from the current request context."""
    return str(request.url_for("get_calendar_feed", token=token))


# ── Public feed endpoint (no auth — token IS the auth) ──────────────


@router.get("/feed/{token}.ics", include_in_schema=False, name="get_calendar_feed")
async def get_calendar_feed(token: str, session: DBDep) -> Response:
    """Return iCalendar feed for the given token. Consumed by calendar apps."""
    feed_token = await crud_calendar_feed.get_by_token(session, token=token)
    if feed_token is None:
        raise_problem(404, code="calendar_feed.not_found", detail="Not found")

    # Fetch all confirmed bookings with slot + event data
    bookings = await crud_booking.get_multi_by_user(
        session,
        user_id=feed_token.user_id,
        status="confirmed",
        with_slot=True,
        limit=500,
    )

    ical_bytes = build_calendar(bookings)

    # Track last access
    await crud_calendar_feed.update_last_accessed(session, db_obj=feed_token)

    return Response(
        content=ical_bytes,
        media_type="text/calendar",
        headers={
            "Content-Disposition": 'attachment; filename="wirksam-bookings.ics"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )


# ── Authenticated management endpoints ──────────────────────────────


@router.get("/feed-settings", response_model=CalendarFeedRead | None)
async def get_feed_settings(
    session: DBDep, current_user: CurrentUser, request: Request
) -> CalendarFeedRead | None:
    """Get the current user's calendar feed settings."""
    feed_token = await crud_calendar_feed.get_by_user(session, user_id=current_user.id)
    if feed_token is None:
        return None
    return CalendarFeedRead(
        id=feed_token.id,
        feed_url=_build_feed_url(request, feed_token.token),
        is_enabled=feed_token.is_enabled,
        last_accessed_at=feed_token.last_accessed_at,
        created_at=feed_token.created_at,
    )


@router.post("/feed-settings", response_model=CalendarFeedRead)
async def enable_feed(
    session: DBDep, current_user: CurrentUser, request: Request
) -> CalendarFeedRead:
    """Create or re-enable the user's calendar feed."""
    feed_token = await crud_calendar_feed.get_by_user(session, user_id=current_user.id)
    if feed_token is None:
        feed_token = await crud_calendar_feed.create_for_user(
            session, user_id=current_user.id
        )
    elif not feed_token.is_enabled:
        feed_token = await crud_calendar_feed.set_enabled(
            session, db_obj=feed_token, enabled=True
        )
    return CalendarFeedRead(
        id=feed_token.id,
        feed_url=_build_feed_url(request, feed_token.token),
        is_enabled=feed_token.is_enabled,
        last_accessed_at=feed_token.last_accessed_at,
        created_at=feed_token.created_at,
    )


@router.post("/feed-settings/regenerate", response_model=CalendarFeedRead)
async def regenerate_feed(
    session: DBDep, current_user: CurrentUser, request: Request
) -> CalendarFeedRead:
    """Regenerate the feed token. The old URL will stop working."""
    feed_token = await crud_calendar_feed.get_by_user(session, user_id=current_user.id)
    if feed_token is None:
        raise_problem(
            404,
            code="calendar_feed.not_found",
            detail="Calendar feed not found. Enable it first.",
        )
    feed_token = await crud_calendar_feed.regenerate_token(session, db_obj=feed_token)
    return CalendarFeedRead(
        id=feed_token.id,
        feed_url=_build_feed_url(request, feed_token.token),
        is_enabled=feed_token.is_enabled,
        last_accessed_at=feed_token.last_accessed_at,
        created_at=feed_token.created_at,
    )


@router.delete("/feed-settings", status_code=204)
async def disable_feed(session: DBDep, current_user: CurrentUser) -> None:
    """Disable the calendar feed. The URL will stop working."""
    feed_token = await crud_calendar_feed.get_by_user(session, user_id=current_user.id)
    if feed_token is None:
        return
    await crud_calendar_feed.set_enabled(session, db_obj=feed_token, enabled=False)
