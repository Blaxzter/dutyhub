"""Unit tests for the check_upcoming_shifts cron script."""

import datetime as dt
from types import TracebackType
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.models.booking import Booking
from app.models.notification import Notification, NotificationType
from app.models.shift import Shift
from app.models.task import Task
from app.models.user import User
from app.scripts.check_upcoming_shifts import LOOKAHEAD_MINUTES, check_upcoming_shifts

TYPE_CODE = "shift.starting_soon_unfilled"

# The script derives `now` from the wall clock and compares plain times
# (`start_time >= now.time()` and `start_time <= (now + 30min).time()`), so the
# window wraps around midnight. With a real clock every "shift inside the
# window" test would fail for runs starting between 23:30 and 00:00 UTC.
# The clock is therefore frozen to a fixed instant and every row below is built
# relative to it, which keeps the assertions deterministic.
FROZEN_NOW = dt.datetime(2026, 5, 24, 12, 0, tzinfo=dt.timezone.utc)
NOW = FROZEN_NOW.replace(tzinfo=None)
TODAY = NOW.date()


class _SessionContext:
    """Async context manager standing in for `async_session()`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None


async def _run_check(db: AsyncSession) -> int:
    """Run the cron entry point against the test session with a frozen clock."""
    fake_dt = MagicMock()
    fake_dt.datetime.now.return_value = FROZEN_NOW
    fake_dt.timedelta = dt.timedelta
    fake_dt.timezone = dt.timezone

    with (
        patch(
            "app.scripts.check_upcoming_shifts.async_session",
            MagicMock(return_value=_SessionContext(db)),
        ),
        patch("app.scripts.check_upcoming_shifts.dt", fake_dt),
        patch(
            "app.logic.notifications.service.EmailChannel.is_configured",
            return_value=False,
        ),
        patch(
            "app.logic.notifications.service.PushChannel.is_configured",
            return_value=False,
        ),
        patch(
            "app.logic.notifications.service.TelegramChannel.is_configured",
            return_value=False,
        ),
    ):
        return await check_upcoming_shifts()


@pytest.mark.asyncio
class TestCheckUpcomingShifts:
    """Test suite for the upcoming-unfilled-shift cron check."""

    async def _seed_type(self, db: AsyncSession) -> NotificationType:
        """Register the notification type the script dispatches."""
        nt = NotificationType(
            code=TYPE_CODE,
            name="Shift Starting Soon (Unfilled)",
            description="Alert when a shift starts soon but still has open spots",
            category="shift",
            is_admin_only=True,
            default_channels=["email"],
            is_active=True,
        )
        db.add(nt)
        await db.flush()
        await db.refresh(nt)
        return nt

    async def _make_shift(
        self,
        db: AsyncSession,
        task: Task,
        *,
        starts_in: dt.timedelta,
        on_date: dt.date | None = None,
        max_bookings: int = 2,
    ) -> Shift:
        """Create a shift starting `starts_in` from the frozen now."""
        start = NOW + starts_in
        shift = Shift(
            task_id=task.id,
            title="Einlasskontrolle",
            description="Einlass am Haupteingang",
            date=on_date or TODAY,
            start_time=start.time(),
            end_time=(start + dt.timedelta(hours=2)).time(),
            location="Haupteingang",
            max_bookings=max_bookings,
        )
        db.add(shift)
        await db.flush()
        await db.refresh(shift)
        return shift

    async def _make_booking(
        self, db: AsyncSession, shift: Shift, user: User, status: str
    ) -> Booking:
        """Create a booking for a shift with an explicit status."""
        booking = Booking(shift_id=shift.id, user_id=user.id, status=status)
        db.add(booking)
        await db.flush()
        await db.refresh(booking)
        return booking

    async def _make_previous_alert(
        self,
        db: AsyncSession,
        shift: Shift,
        recipient: User,
        *,
        age: dt.timedelta,
    ) -> Notification:
        """Insert an already-dispatched alert for `shift`, created `age` ago."""
        data: dict[str, str | int | None] = {"slot_id": str(shift.id)}
        notif = Notification(
            recipient_id=recipient.id,
            notification_type_code=TYPE_CODE,
            title="Unfilled Shift Starting Soon",
            body="Previously dispatched alert",
            data=data,
            created_at=NOW - age,
        )
        db.add(notif)
        await db.flush()
        await db.refresh(notif)
        return notif

    async def _alerts(self, db: AsyncSession) -> list[Notification]:
        """All dispatched unfilled-shift alerts currently in the database."""
        result = await db.execute(
            select(Notification).where(
                col(Notification.notification_type_code) == TYPE_CODE
            )
        )
        return list(result.scalars().all())

    async def test_notifies_admin_about_unfilled_shift(
        self,
        db_session: AsyncSession,
        test_task: Task,
        test_admin_user: User,
    ) -> None:
        """A shift starting inside the window with open spots alerts admins."""
        await self._seed_type(db_session)
        shift = await self._make_shift(
            db_session, test_task, starts_in=dt.timedelta(minutes=10)
        )

        sent = await _run_check(db_session)

        assert sent == 1
        alerts = await self._alerts(db_session)
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.recipient_id == test_admin_user.id
        assert alert.notification_type_code == TYPE_CODE
        assert alert.data is not None
        assert alert.data["slot_id"] == str(shift.id)
        assert alert.data["task_id"] == str(test_task.id)
        assert alert.data["open_spots"] == 2
        assert alert.data["confirmed"] == 0
        assert alert.data["max_bookings"] == 2
        assert shift.title in alert.body
        assert f"~{LOOKAHEAD_MINUTES} minutes" in alert.body
        assert "0/2 filled" in alert.body

    async def test_skips_full_shift(
        self,
        db_session: AsyncSession,
        test_task: Task,
        test_user: User,
        test_admin_user: User,
    ) -> None:
        """A shift whose confirmed bookings fill every spot is skipped."""
        _ = test_admin_user  # an admin must exist, else nothing could be sent
        await self._seed_type(db_session)
        shift = await self._make_shift(
            db_session,
            test_task,
            starts_in=dt.timedelta(minutes=10),
            max_bookings=1,
        )
        await self._make_booking(db_session, shift, test_user, "confirmed")

        sent = await _run_check(db_session)

        assert sent == 0
        assert await self._alerts(db_session) == []

    async def test_cancelled_bookings_do_not_fill_the_shift(
        self,
        db_session: AsyncSession,
        test_task: Task,
        test_user: User,
        test_admin_user: User,
    ) -> None:
        """Only confirmed bookings count toward a shift being full."""
        _ = test_admin_user
        await self._seed_type(db_session)
        shift = await self._make_shift(
            db_session,
            test_task,
            starts_in=dt.timedelta(minutes=10),
            max_bookings=1,
        )
        await self._make_booking(db_session, shift, test_user, "cancelled")

        sent = await _run_check(db_session)

        assert sent == 1
        alerts = await self._alerts(db_session)
        assert len(alerts) == 1
        assert alerts[0].data is not None
        assert alerts[0].data["confirmed"] == 0
        assert alerts[0].data["open_spots"] == 1

    async def test_ignores_shift_outside_lookahead_window(
        self,
        db_session: AsyncSession,
        test_task: Task,
        test_admin_user: User,
    ) -> None:
        """A shift starting well after the lookahead window is ignored."""
        _ = test_admin_user
        await self._seed_type(db_session)
        await self._make_shift(
            db_session,
            test_task,
            starts_in=dt.timedelta(minutes=LOOKAHEAD_MINUTES + 90),
        )

        sent = await _run_check(db_session)

        assert sent == 0
        assert await self._alerts(db_session) == []

    async def test_ignores_shift_that_already_started(
        self,
        db_session: AsyncSession,
        test_task: Task,
        test_admin_user: User,
    ) -> None:
        """A shift that started before now is no longer 'upcoming'."""
        _ = test_admin_user
        await self._seed_type(db_session)
        await self._make_shift(
            db_session, test_task, starts_in=dt.timedelta(minutes=-10)
        )

        sent = await _run_check(db_session)

        assert sent == 0
        assert await self._alerts(db_session) == []

    async def test_ignores_shift_on_another_date(
        self,
        db_session: AsyncSession,
        test_task: Task,
        test_admin_user: User,
    ) -> None:
        """A shift at the right time of day but on another date is ignored."""
        _ = test_admin_user
        await self._seed_type(db_session)
        await self._make_shift(
            db_session,
            test_task,
            starts_in=dt.timedelta(minutes=10),
            on_date=TODAY + dt.timedelta(days=1),
        )

        sent = await _run_check(db_session)

        assert sent == 0
        assert await self._alerts(db_session) == []

    async def test_skips_shift_alerted_within_the_last_hour(
        self,
        db_session: AsyncSession,
        test_task: Task,
        test_admin_user: User,
    ) -> None:
        """A shift alerted about 10 minutes ago is not alerted about again."""
        await self._seed_type(db_session)
        shift = await self._make_shift(
            db_session, test_task, starts_in=dt.timedelta(minutes=10)
        )
        await self._make_previous_alert(
            db_session, shift, test_admin_user, age=dt.timedelta(minutes=10)
        )

        sent = await _run_check(db_session)

        assert sent == 0
        # Only the pre-existing alert remains — nothing new was dispatched.
        alerts = await self._alerts(db_session)
        assert len(alerts) == 1
        assert alerts[0].body == "Previously dispatched alert"

    async def test_alerts_again_when_previous_alert_is_stale(
        self,
        db_session: AsyncSession,
        test_task: Task,
        test_admin_user: User,
    ) -> None:
        """An alert older than an hour no longer suppresses a new one."""
        await self._seed_type(db_session)
        shift = await self._make_shift(
            db_session, test_task, starts_in=dt.timedelta(minutes=10)
        )
        await self._make_previous_alert(
            db_session, shift, test_admin_user, age=dt.timedelta(hours=3)
        )

        sent = await _run_check(db_session)

        assert sent == 1
        alerts = await self._alerts(db_session)
        assert len(alerts) == 2
        bodies = [a.body for a in alerts]
        assert "Previously dispatched alert" in bodies
        assert any(shift.title in body for body in bodies)

    async def test_returns_zero_when_no_shifts_exist(
        self,
        db_session: AsyncSession,
        test_admin_user: User,
    ) -> None:
        """An empty schedule sends nothing and reports zero."""
        _ = test_admin_user
        await self._seed_type(db_session)

        sent = await _run_check(db_session)

        assert sent == 0
        assert await self._alerts(db_session) == []
