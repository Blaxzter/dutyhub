"""Check for upcoming unfilled shifts and notify admins.

Run via cron every 5 minutes:
  */5 * * * * cd /app && python -m app.scripts.check_upcoming_shifts

Or via just:
  just check-upcoming-shifts
"""

import asyncio
import datetime as dt

from sqlalchemy import func, select
from sqlmodel import col

from app.core.db import async_session
from app.core.logger import get_logger
from app.logic.notifications.service import NotificationService
from app.models.booking import Booking
from app.models.notification import Notification
from app.models.shift import Shift

logger = get_logger(__name__)

LOOKAHEAD_MINUTES = 30


async def check_upcoming_shifts() -> int:
    """Find shifts starting within LOOKAHEAD_MINUTES that aren't fully booked.

    Returns the number of notifications sent.
    """
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    today = now.date()
    cutoff_time = (now + dt.timedelta(minutes=LOOKAHEAD_MINUTES)).time()

    async with async_session() as db:
        # Find shifts starting within the lookahead window that aren't full
        query = select(Shift).where(
            col(Shift.date) == today,
            col(Shift.start_time) >= now.time(),
            col(Shift.start_time) <= cutoff_time,
        )
        result = await db.execute(query)
        shifts = list(result.scalars().all())

        sent = 0
        svc = NotificationService(db)

        for shift in shifts:
            # Count confirmed bookings
            count_query = (
                select(func.count())
                .select_from(Booking)
                .where(
                    col(Booking.shift_id) == shift.id,
                    col(Booking.status) == "confirmed",
                )
            )
            count_result = await db.execute(count_query)
            confirmed = count_result.scalar_one()

            if confirmed >= shift.max_bookings:
                continue  # Shift is full, skip

            # Check if we already sent a notification for this shift recently
            recent_check = (
                select(func.count())
                .select_from(Notification)
                .where(
                    col(Notification.notification_type_code)
                    == "shift.starting_soon_unfilled",
                    Notification.data["slot_id"].astext == str(shift.id),  # type: ignore[union-attr]
                    col(Notification.created_at) >= now - dt.timedelta(hours=1),
                )
            )
            recent_result = await db.execute(recent_check)
            if recent_result.scalar_one() > 0:
                continue  # Already notified

            # Send notification to admins
            open_spots = shift.max_bookings - confirmed
            await svc.notify_admins(
                type_code="shift.starting_soon_unfilled",
                title="Unfilled Shift Starting Soon",
                body=(
                    f'Shift "{shift.title}" starts in ~{LOOKAHEAD_MINUTES} minutes '
                    f"with {open_spots} open spot(s) ({confirmed}/{shift.max_bookings} filled)."
                ),
                data={
                    "slot_id": str(shift.id),
                    "task_id": str(shift.task_id),
                    "open_spots": open_spots,
                    "confirmed": confirmed,
                    "max_bookings": shift.max_bookings,
                },
            )
            sent += 1

        await db.commit()

    logger.info(f"Checked upcoming shifts: sent {sent} notification(s)")
    return sent


if __name__ == "__main__":
    asyncio.run(check_upcoming_shifts())
