# pyright: reportPrivateUsage=false
"""Unit tests for the notification dispatch triggers.

Every trigger opens its own session through the module-level ``async_session``
factory (BackgroundTasks run after the request session is closed), so each
database test patches ``triggers.async_session`` to hand back the transactional
``db_session`` fixture instead of opening a real connection.

Assertions are made against the persisted ``notifications`` rows rather than a
mocked ``NotificationService``, so the trigger → service → persistence contract
is actually exercised: the exact recipient set, the localized title/body, and —
for every trigger — at least one user who must *not* be notified (an unrelated
bystander, the acting user, an opted-out user, or an inactive one).

``NotificationService`` resolves a recipient's channels from the
``notification_types`` row, and silently drops the notification when the type
code is unknown, so every database test seeds the whole code registry first via
the ``seeded_types`` fixture.

No delivery channel is ever reached: email/push/Telegram are reported as
unconfigured and the batched email send is replaced by an ``AsyncMock``.
"""

import datetime as dt
import uuid
from collections.abc import AsyncGenerator, Callable, Coroutine, Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.crud.notification_type import notification_type as crud_notification_type
from app.logic.notifications import triggers
from app.logic.notifications.seeder import seed_notification_types
from app.models.notification import Notification, NotificationSubscription
from app.models.user import User

MODULE = "app.logic.notifications.triggers"
SERVICE = "app.logic.notifications.service"

# A trigger call, pre-bound with arguments, ready to await.
TriggerCall = Callable[[], Coroutine[Any, Any, None]]


# ── fixtures ──────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def seeded_types(db_session: AsyncSession) -> None:
    """Upsert every notification type from the code registry.

    Without the type row, ``resolve_channels`` returns ``None`` and the service
    treats the notification as muted, so a trigger would produce no rows at all
    for reasons that have nothing to do with the behaviour under test.
    """
    await seed_notification_types(db_session)


# ── helpers ───────────────────────────────────────────────────────


@contextmanager
def _dispatch_env(db: AsyncSession) -> Generator[MagicMock, None, None]:
    """Point the triggers at ``db`` and stub out every delivery channel.

    The triggers do ``async with async_session() as db``; a real session would
    be closed (and its transaction discarded) on exit, so the replacement is a
    context manager that yields the test session and leaves it open. Yields the
    factory mock so tests can assert a trigger returned *before* opening one.
    """

    @asynccontextmanager
    async def _session_cm() -> AsyncGenerator[AsyncSession, None]:
        yield db

    factory = MagicMock(side_effect=_session_cm)
    with (
        patch(f"{SERVICE}.EmailChannel.is_configured", return_value=False),
        patch(f"{SERVICE}.PushChannel.is_configured", return_value=False),
        patch(f"{SERVICE}.TelegramChannel.is_configured", return_value=False),
        patch(
            f"{SERVICE}.EmailChannel.send_batch",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(f"{MODULE}.async_session", factory),
    ):
        yield factory


async def _make_user(
    db: AsyncSession,
    *,
    tag: str,
    is_active: bool = True,
    roles: list[str] | None = None,
    language: str = "en",
) -> User:
    """Persist an extra user; ``tag`` keeps auth0_sub/email unique per test."""
    user = User(
        auth0_sub=f"auth0|{tag}",
        email=f"{tag}@example.com",
        name=f"User {tag}",
        roles=roles if roles is not None else [],
        is_active=is_active,
        preferred_language=language,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _mute(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    type_code: str,
    scope_type: str = "global",
    scope_id: uuid.UUID | None = None,
) -> None:
    """Record an explicit opt-out for a user at the given scope level."""
    notif_type = await crud_notification_type.get_by_code(db, type_code)
    assert notif_type is not None, f"{type_code} is missing from notification_types"
    db.add(
        NotificationSubscription(
            user_id=user_id,
            notification_type_id=notif_type.id,
            scope_type=scope_type,
            scope_id=scope_id,
            is_muted=True,
        )
    )
    await db.flush()


async def _rows(db: AsyncSession, type_code: str | None = None) -> list[Notification]:
    """Every persisted notification, optionally narrowed to one type code."""
    query = select(Notification)
    if type_code is not None:
        query = query.where(col(Notification.notification_type_code) == type_code)
    result = await db.execute(query)
    return list(result.scalars().all())


async def _recipients(db: AsyncSession, type_code: str) -> set[uuid.UUID]:
    """The exact set of users that received a notification of this type."""
    return {row.recipient_id for row in await _rows(db, type_code)}


async def _single(db: AsyncSession, type_code: str, user_id: uuid.UUID) -> Notification:
    """The one notification of ``type_code`` addressed to ``user_id``."""
    matches = [row for row in await _rows(db, type_code) if row.recipient_id == user_id]
    assert len(matches) == 1, f"expected exactly 1 {type_code} row, got {len(matches)}"
    return matches[0]


def _all_invocations(user_id: uuid.UUID) -> list[tuple[str, TriggerCall]]:
    """Every trigger, bound with the minimum arguments to reach its ``try``."""
    slot_id = uuid.uuid4()
    task_id = uuid.uuid4()
    event_id = uuid.uuid4()
    return [
        (
            "dispatch_booking_confirmed",
            lambda: triggers.dispatch_booking_confirmed(
                booking_id=uuid.uuid4(),
                user_id=user_id,
                slot_title="Shift",
                slot_id=slot_id,
                task_id=task_id,
            ),
        ),
        (
            "dispatch_booking_cobooked",
            lambda: triggers.dispatch_booking_cobooked(
                slot_id=slot_id,
                slot_title="Shift",
                task_id=task_id,
                new_user_name="Alice",
                existing_user_ids=[user_id],
            ),
        ),
        (
            "dispatch_booking_cancelled_by_user",
            lambda: triggers.dispatch_booking_cancelled_by_user(
                booking_id=uuid.uuid4(),
                user_id=user_id,
                slot_title="Shift",
                slot_id=slot_id,
                task_id=task_id,
            ),
        ),
        (
            "dispatch_booking_cancelled_by_admin",
            lambda: triggers.dispatch_booking_cancelled_by_admin(
                user_ids=[user_id],
                slot_title="Shift",
                task_id=task_id,
            ),
        ),
        (
            "dispatch_shift_time_changed",
            lambda: triggers.dispatch_shift_time_changed(
                slot_id=slot_id,
                slot_title="Shift",
                task_id=task_id,
                booked_user_ids=[user_id],
            ),
        ),
        (
            "dispatch_task_published",
            lambda: triggers.dispatch_task_published(task_id=task_id, task_name="Task"),
        ),
        (
            "dispatch_event_published",
            lambda: triggers.dispatch_event_published(
                event_id=event_id, event_name="Event"
            ),
        ),
        (
            "dispatch_user_registered",
            lambda: triggers.dispatch_user_registered(
                user_id=user_id, user_name="Alice", user_email="alice@example.com"
            ),
        ),
        (
            "dispatch_user_approved",
            lambda: triggers.dispatch_user_approved(user_id=user_id),
        ),
        (
            "dispatch_user_rejected",
            lambda: triggers.dispatch_user_rejected(user_id=user_id, reason="Spam"),
        ),
    ]


# ── _build_scope_chain ────────────────────────────────────────────


class TestBuildScopeChain:
    """Table tests for the pure ``_build_scope_chain`` helper."""

    @pytest.mark.parametrize(
        ("with_slot", "with_task", "with_event", "expected"),
        [
            (False, False, False, []),
            (True, False, False, ["shift"]),
            (False, True, False, ["task"]),
            (False, False, True, ["event"]),
            (True, True, False, ["shift", "task"]),
            (True, False, True, ["shift", "event"]),
            (False, True, True, ["task", "event"]),
            (True, True, True, ["shift", "task", "event"]),
        ],
    )
    def test_scope_chain_combinations(
        self,
        with_slot: bool,
        with_task: bool,
        with_event: bool,
        expected: list[str],
    ) -> None:
        """Test that only present ids appear, most specific scope first."""
        slot_id = uuid.uuid4() if with_slot else None
        task_id = uuid.uuid4() if with_task else None
        event_id = uuid.uuid4() if with_event else None

        chain = triggers._build_scope_chain(slot_id, task_id, event_id)

        assert [scope for scope, _ in chain] == expected

        by_scope: dict[str, uuid.UUID | None] = {
            "shift": slot_id,
            "task": task_id,
            "event": event_id,
        }
        for scope, scope_id in chain:
            assert scope_id == by_scope[scope]

    def test_no_arguments_yields_empty_chain(self) -> None:
        """Test that the helper defaults every id to absent."""
        assert triggers._build_scope_chain() == []


# ── booking.confirmed ─────────────────────────────────────────────


@pytest.mark.asyncio
class TestDispatchBookingConfirmed:
    """Test suite for dispatch_booking_confirmed."""

    async def test_notifies_only_the_booker(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test that only the booking's owner is notified."""
        bystander = await _make_user(db_session, tag="bystander-confirmed")

        with _dispatch_env(db_session):
            await triggers.dispatch_booking_confirmed(
                booking_id=uuid.uuid4(),
                user_id=test_user.id,
                slot_title="Morning Shift",
                slot_date=dt.date(2026, 3, 14),
                slot_start_time=dt.time(9, 30),
                slot_end_time=dt.time(11, 0),
                slot_location="Main Hall",
                task_name="Kitchen Duty",
                slot_id=uuid.uuid4(),
                task_id=uuid.uuid4(),
            )

        assert await _recipients(db_session, "booking.confirmed") == {test_user.id}
        assert bystander.id not in await _recipients(db_session, "booking.confirmed")

    async def test_english_body_renders_every_detail(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test that the date/time/location fragments are formatted."""
        booking_id = uuid.uuid4()
        slot_id = uuid.uuid4()
        task_id = uuid.uuid4()

        with _dispatch_env(db_session):
            await triggers.dispatch_booking_confirmed(
                booking_id=booking_id,
                user_id=test_user.id,
                slot_title="Morning Shift",
                slot_date=dt.date(2026, 3, 14),
                slot_start_time=dt.time(9, 30),
                slot_end_time=dt.time(11, 0),
                slot_location="Main Hall",
                task_name="Kitchen Duty",
                slot_id=slot_id,
                task_id=task_id,
            )

        notif = await _single(db_session, "booking.confirmed", test_user.id)
        assert "Booking Confirmed" in notif.title
        assert "Morning Shift" in notif.body
        assert "14.03.2026" in notif.body
        assert "09:30" in notif.body
        assert "11:00" in notif.body
        assert "Main Hall" in notif.body
        assert "Kitchen Duty" in notif.body
        assert notif.data == {
            "booking_id": str(booking_id),
            "slot_id": str(slot_id),
            "task_id": str(task_id),
        }

    async def test_german_body_when_recipient_prefers_german(
        self,
        db_session: AsyncSession,
        seeded_types: None,
    ) -> None:
        """Test that the message factory follows the recipient's language."""
        german = await _make_user(db_session, tag="de-confirmed", language="de")

        with _dispatch_env(db_session):
            await triggers.dispatch_booking_confirmed(
                booking_id=uuid.uuid4(),
                user_id=german.id,
                slot_title="Morning Shift",
                slot_date=dt.date(2026, 3, 14),
                slot_id=uuid.uuid4(),
                task_id=uuid.uuid4(),
            )

        notif = await _single(db_session, "booking.confirmed", german.id)
        assert "Buchung best" in notif.title
        assert "Ihre Buchung wurde" in notif.body

    async def test_optional_details_render_as_blanks(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test the factory's falsy branches for date, time, location, task."""
        with _dispatch_env(db_session):
            await triggers.dispatch_booking_confirmed(
                booking_id=uuid.uuid4(),
                user_id=test_user.id,
                slot_title="Morning Shift",
                slot_id=uuid.uuid4(),
                task_id=uuid.uuid4(),
                event_id=uuid.uuid4(),
            )

        notif = await _single(db_session, "booking.confirmed", test_user.id)
        assert "Morning Shift" in notif.body
        assert "14.03.2026" not in notif.body
        assert "09:30" not in notif.body
        assert "Main Hall" not in notif.body

    async def test_opted_out_user_receives_nothing(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test that a globally muted recipient gets no notification row."""
        await _mute(db_session, user_id=test_user.id, type_code="booking.confirmed")

        with _dispatch_env(db_session):
            await triggers.dispatch_booking_confirmed(
                booking_id=uuid.uuid4(),
                user_id=test_user.id,
                slot_title="Morning Shift",
                slot_id=uuid.uuid4(),
                task_id=uuid.uuid4(),
            )

        assert await _rows(db_session, "booking.confirmed") == []

    async def test_shift_scoped_mute_is_honoured(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test that muting the shift scope wins over the global default."""
        slot_id = uuid.uuid4()
        await _mute(
            db_session,
            user_id=test_user.id,
            type_code="booking.confirmed",
            scope_type="shift",
            scope_id=slot_id,
        )

        with _dispatch_env(db_session):
            await triggers.dispatch_booking_confirmed(
                booking_id=uuid.uuid4(),
                user_id=test_user.id,
                slot_title="Morning Shift",
                slot_id=slot_id,
                task_id=uuid.uuid4(),
                event_id=uuid.uuid4(),
            )

        assert await _rows(db_session, "booking.confirmed") == []


# ── booking.shift_cobooked ────────────────────────────────────────


@pytest.mark.asyncio
class TestDispatchBookingCobooked:
    """Test suite for dispatch_booking_cobooked."""

    async def test_notifies_existing_bookers_not_the_new_booker(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test that the acting user is excluded from their own co-booking."""
        existing_a = await _make_user(db_session, tag="cobooked-a")
        existing_b = await _make_user(db_session, tag="cobooked-b")
        bystander = await _make_user(db_session, tag="cobooked-bystander")

        with _dispatch_env(db_session):
            await triggers.dispatch_booking_cobooked(
                slot_id=uuid.uuid4(),
                slot_title="Morning Shift",
                task_id=uuid.uuid4(),
                new_user_name="Alice",
                existing_user_ids=[existing_a.id, existing_b.id],
            )

        recipients = await _recipients(db_session, "booking.shift_cobooked")
        assert recipients == {existing_a.id, existing_b.id}
        assert test_user.id not in recipients
        assert bystander.id not in recipients

    async def test_body_names_the_new_booker(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test the rendered English co-booking body."""
        with _dispatch_env(db_session):
            await triggers.dispatch_booking_cobooked(
                slot_id=uuid.uuid4(),
                slot_title="Morning Shift",
                task_id=uuid.uuid4(),
                new_user_name="Alice",
                existing_user_ids=[test_user.id],
            )

        notif = await _single(db_session, "booking.shift_cobooked", test_user.id)
        assert notif.body == 'Alice also booked the shift "Morning Shift".'

    async def test_missing_name_falls_back_to_someone(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test the ``new_user_name or "Someone"`` fallback."""
        with _dispatch_env(db_session):
            await triggers.dispatch_booking_cobooked(
                slot_id=uuid.uuid4(),
                slot_title="Evening Shift",
                task_id=uuid.uuid4(),
                event_id=uuid.uuid4(),
                new_user_name=None,
                existing_user_ids=[test_user.id],
            )

        notif = await _single(db_session, "booking.shift_cobooked", test_user.id)
        assert notif.body == 'Someone also booked the shift "Evening Shift".'

    async def test_empty_recipient_list_returns_before_opening_a_session(
        self,
        db_session: AsyncSession,
        seeded_types: None,
    ) -> None:
        """Test the early-return guard for an empty existing_user_ids list."""
        with _dispatch_env(db_session) as factory:
            await triggers.dispatch_booking_cobooked(
                slot_id=uuid.uuid4(),
                slot_title="Morning Shift",
                task_id=uuid.uuid4(),
                new_user_name="Alice",
                existing_user_ids=[],
            )

        assert factory.call_count == 0
        assert await _rows(db_session) == []

    async def test_opted_out_booker_receives_nothing(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test that only the non-muted existing booker is notified."""
        other = await _make_user(db_session, tag="cobooked-other")
        await _mute(
            db_session, user_id=test_user.id, type_code="booking.shift_cobooked"
        )

        with _dispatch_env(db_session):
            await triggers.dispatch_booking_cobooked(
                slot_id=uuid.uuid4(),
                slot_title="Morning Shift",
                task_id=uuid.uuid4(),
                new_user_name="Alice",
                existing_user_ids=[test_user.id, other.id],
            )

        assert await _recipients(db_session, "booking.shift_cobooked") == {other.id}


# ── booking.cancelled_by_user ─────────────────────────────────────


@pytest.mark.asyncio
class TestDispatchBookingCancelledByUser:
    """Test suite for dispatch_booking_cancelled_by_user."""

    async def test_notifies_only_the_cancelling_user(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test that nobody but the cancelling user is notified."""
        bystander = await _make_user(db_session, tag="cancel-bystander")
        booking_id = uuid.uuid4()
        slot_id = uuid.uuid4()
        task_id = uuid.uuid4()

        with _dispatch_env(db_session):
            await triggers.dispatch_booking_cancelled_by_user(
                booking_id=booking_id,
                user_id=test_user.id,
                slot_title="Morning Shift",
                slot_id=slot_id,
                task_id=task_id,
                event_id=uuid.uuid4(),
            )

        recipients = await _recipients(db_session, "booking.cancelled_by_user")
        assert recipients == {test_user.id}
        assert bystander.id not in recipients

        notif = await _single(db_session, "booking.cancelled_by_user", test_user.id)
        assert notif.body == 'Your booking for "Morning Shift" has been cancelled.'
        assert notif.data == {
            "booking_id": str(booking_id),
            "slot_id": str(slot_id),
            "task_id": str(task_id),
        }

    async def test_opted_out_user_receives_nothing(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test that a muted recipient produces no notification row."""
        await _mute(
            db_session, user_id=test_user.id, type_code="booking.cancelled_by_user"
        )

        with _dispatch_env(db_session):
            await triggers.dispatch_booking_cancelled_by_user(
                booking_id=uuid.uuid4(),
                user_id=test_user.id,
                slot_title="Morning Shift",
                slot_id=uuid.uuid4(),
                task_id=uuid.uuid4(),
            )

        assert await _rows(db_session, "booking.cancelled_by_user") == []


# ── booking.cancelled_by_admin ────────────────────────────────────


@pytest.mark.asyncio
class TestDispatchBookingCancelledByAdmin:
    """Test suite for dispatch_booking_cancelled_by_admin."""

    async def test_empty_user_list_returns_before_opening_a_session(
        self,
        db_session: AsyncSession,
        seeded_types: None,
    ) -> None:
        """Test the early-return guard for an empty user_ids list."""
        with _dispatch_env(db_session) as factory:
            await triggers.dispatch_booking_cancelled_by_admin(
                user_ids=[],
                slot_title="Morning Shift",
                task_name="Kitchen Duty",
                reason="Shift removed",
            )

        assert factory.call_count == 0
        assert await _rows(db_session) == []

    async def test_notifies_listed_users_only(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test that a user outside the cancelled set is not notified."""
        affected = await _make_user(db_session, tag="admincancel-affected")
        bystander = await _make_user(db_session, tag="admincancel-bystander")
        task_id = uuid.uuid4()
        event_id = uuid.uuid4()

        with _dispatch_env(db_session):
            await triggers.dispatch_booking_cancelled_by_admin(
                user_ids=[test_user.id, affected.id],
                slot_title="Morning Shift",
                task_name="Kitchen Duty",
                task_id=task_id,
                event_id=event_id,
                reason="Shift removed",
            )

        recipients = await _recipients(db_session, "booking.cancelled_by_admin")
        assert recipients == {test_user.id, affected.id}
        assert bystander.id not in recipients

        notif = await _single(db_session, "booking.cancelled_by_admin", test_user.id)
        assert notif.data == {"task_id": str(task_id), "event_id": str(event_id)}

    async def test_english_body_with_task_and_reason(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test the English task_label and detail fragments."""
        with _dispatch_env(db_session):
            await triggers.dispatch_booking_cancelled_by_admin(
                user_ids=[test_user.id],
                slot_title="Morning Shift",
                task_name="Kitchen Duty",
                reason="Shift removed",
            )

        notif = await _single(db_session, "booking.cancelled_by_admin", test_user.id)
        assert notif.body == (
            'Your booking for "Morning Shift" for task "Kitchen Duty" '
            "was cancelled by an administrator. (Reason: Shift removed)"
        )

    async def test_english_body_without_task_or_reason(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test that both English conditional fragments collapse to empty."""
        with _dispatch_env(db_session):
            await triggers.dispatch_booking_cancelled_by_admin(
                user_ids=[test_user.id],
                slot_title="Morning Shift",
            )

        notif = await _single(db_session, "booking.cancelled_by_admin", test_user.id)
        assert notif.body == (
            'Your booking for "Morning Shift" was cancelled by an administrator.'
        )
        assert notif.data == {"task_id": None, "event_id": None}

    async def test_german_body_with_task_and_reason(
        self,
        db_session: AsyncSession,
        seeded_types: None,
    ) -> None:
        """Test the German task_label and detail fragments."""
        german = await _make_user(db_session, tag="de-admincancel", language="de")

        with _dispatch_env(db_session):
            await triggers.dispatch_booking_cancelled_by_admin(
                user_ids=[german.id],
                slot_title="Morning Shift",
                task_name="Kitchen Duty",
                reason="Zu wenig Anmeldungen",
            )

        notif = await _single(db_session, "booking.cancelled_by_admin", german.id)
        assert "das Task" in notif.body
        assert "Kitchen Duty" in notif.body
        assert "(Grund: Zu wenig Anmeldungen)" in notif.body
        assert "Administrator storniert." in notif.body

    async def test_german_body_without_task_or_reason(
        self,
        db_session: AsyncSession,
        seeded_types: None,
    ) -> None:
        """Test that both German conditional fragments collapse to empty."""
        german = await _make_user(db_session, tag="de-admincancel-bare", language="de")

        with _dispatch_env(db_session):
            await triggers.dispatch_booking_cancelled_by_admin(
                user_ids=[german.id],
                slot_title="Morning Shift",
            )

        notif = await _single(db_session, "booking.cancelled_by_admin", german.id)
        assert "das Task" not in notif.body
        assert "Grund:" not in notif.body
        assert "Administrator storniert." in notif.body

    async def test_opted_out_user_receives_nothing(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test that a muted user is dropped from the cancelled set."""
        other = await _make_user(db_session, tag="admincancel-other")
        await _mute(
            db_session, user_id=test_user.id, type_code="booking.cancelled_by_admin"
        )

        with _dispatch_env(db_session):
            await triggers.dispatch_booking_cancelled_by_admin(
                user_ids=[test_user.id, other.id],
                slot_title="Morning Shift",
            )

        assert await _recipients(db_session, "booking.cancelled_by_admin") == {other.id}


# ── shift.time_changed ────────────────────────────────────────────


@pytest.mark.asyncio
class TestDispatchShiftTimeChanged:
    """Test suite for dispatch_shift_time_changed."""

    async def test_empty_booking_list_returns_before_opening_a_session(
        self,
        db_session: AsyncSession,
        seeded_types: None,
    ) -> None:
        """Test the early-return guard for an empty booked_user_ids list."""
        with _dispatch_env(db_session) as factory:
            await triggers.dispatch_shift_time_changed(
                slot_id=uuid.uuid4(),
                slot_title="Morning Shift",
                task_id=uuid.uuid4(),
                booked_user_ids=[],
            )

        assert factory.call_count == 0
        assert await _rows(db_session) == []

    async def test_notifies_booked_users_only(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test that a user without a booking on the shift is not notified."""
        booked = await _make_user(db_session, tag="timechange-booked")
        bystander = await _make_user(db_session, tag="timechange-bystander")
        slot_id = uuid.uuid4()
        task_id = uuid.uuid4()

        with _dispatch_env(db_session):
            await triggers.dispatch_shift_time_changed(
                slot_id=slot_id,
                slot_title="Morning Shift",
                task_id=task_id,
                event_id=uuid.uuid4(),
                booked_user_ids=[test_user.id, booked.id],
            )

        recipients = await _recipients(db_session, "shift.time_changed")
        assert recipients == {test_user.id, booked.id}
        assert bystander.id not in recipients

        notif = await _single(db_session, "shift.time_changed", test_user.id)
        assert notif.body == (
            'The time for shift "Morning Shift" has been updated. '
            "Please check the new schedule."
        )
        assert notif.data == {"slot_id": str(slot_id), "task_id": str(task_id)}

    async def test_opted_out_user_receives_nothing(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test that a muted booker is dropped from the notified set."""
        other = await _make_user(db_session, tag="timechange-other")
        await _mute(db_session, user_id=test_user.id, type_code="shift.time_changed")

        with _dispatch_env(db_session):
            await triggers.dispatch_shift_time_changed(
                slot_id=uuid.uuid4(),
                slot_title="Morning Shift",
                task_id=uuid.uuid4(),
                booked_user_ids=[test_user.id, other.id],
            )

        assert await _recipients(db_session, "shift.time_changed") == {other.id}


# ── task.published ────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDispatchTaskPublished:
    """Test suite for dispatch_task_published."""

    async def test_notifies_active_users_and_skips_inactive_and_muted(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
        test_inactive_user: User,
    ) -> None:
        """Test that inactive and opted-out users are both excluded."""
        active = await _make_user(db_session, tag="taskpub-active")
        muted = await _make_user(db_session, tag="taskpub-muted")
        await _mute(db_session, user_id=muted.id, type_code="task.published")
        task_id = uuid.uuid4()

        with _dispatch_env(db_session):
            await triggers.dispatch_task_published(
                task_id=task_id, task_name="Kitchen Duty"
            )

        recipients = await _recipients(db_session, "task.published")
        assert recipients == {test_user.id, active.id}
        assert test_inactive_user.id not in recipients
        assert muted.id not in recipients

        notif = await _single(db_session, "task.published", test_user.id)
        assert (
            notif.body == 'A new task "Kitchen Duty" has been published. Check it out!'
        )
        assert notif.data == {"task_id": str(task_id)}

    async def test_event_id_extends_the_scope_chain(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test that an event-scoped mute applies once event_id is passed."""
        event_id = uuid.uuid4()
        other = await _make_user(db_session, tag="taskpub-scoped-other")
        await _mute(
            db_session,
            user_id=test_user.id,
            type_code="task.published",
            scope_type="event",
            scope_id=event_id,
        )

        with _dispatch_env(db_session):
            await triggers.dispatch_task_published(
                task_id=uuid.uuid4(),
                task_name="Kitchen Duty",
                event_id=event_id,
            )

        assert await _recipients(db_session, "task.published") == {other.id}

    async def test_no_active_users_creates_nothing(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_inactive_user: User,
    ) -> None:
        """Test that the trigger short-circuits when no user is active."""
        with _dispatch_env(db_session):
            await triggers.dispatch_task_published(
                task_id=uuid.uuid4(), task_name="Kitchen Duty"
            )

        assert test_inactive_user.is_active is False
        assert await _rows(db_session) == []


# ── event.published ───────────────────────────────────────────────


@pytest.mark.asyncio
class TestDispatchEventPublished:
    """Test suite for dispatch_event_published."""

    async def test_notifies_active_users_and_skips_inactive_and_muted(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
        test_inactive_user: User,
    ) -> None:
        """Test that inactive and opted-out users are both excluded."""
        active = await _make_user(db_session, tag="eventpub-active")
        muted = await _make_user(db_session, tag="eventpub-muted")
        await _mute(db_session, user_id=muted.id, type_code="event.published")
        event_id = uuid.uuid4()

        with _dispatch_env(db_session):
            await triggers.dispatch_event_published(
                event_id=event_id, event_name="Summer Fest"
            )

        recipients = await _recipients(db_session, "event.published")
        assert recipients == {test_user.id, active.id}
        assert test_inactive_user.id not in recipients
        assert muted.id not in recipients

        notif = await _single(db_session, "event.published", test_user.id)
        assert notif.body == 'Task group "Summer Fest" has been published.'
        assert notif.data == {"event_id": str(event_id)}

    async def test_event_scoped_mute_is_honoured(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test that the ``[("event", event_id)]`` scope chain is applied."""
        event_id = uuid.uuid4()
        other = await _make_user(db_session, tag="eventpub-scoped-other")
        await _mute(
            db_session,
            user_id=test_user.id,
            type_code="event.published",
            scope_type="event",
            scope_id=event_id,
        )

        with _dispatch_env(db_session):
            await triggers.dispatch_event_published(
                event_id=event_id, event_name="Summer Fest"
            )

        assert await _recipients(db_session, "event.published") == {other.id}

    async def test_no_active_users_creates_nothing(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_inactive_user: User,
    ) -> None:
        """Test that the trigger short-circuits when no user is active."""
        with _dispatch_env(db_session):
            await triggers.dispatch_event_published(
                event_id=uuid.uuid4(), event_name="Summer Fest"
            )

        assert test_inactive_user.is_active is False
        assert await _rows(db_session) == []


# ── user.registered ───────────────────────────────────────────────


@pytest.mark.asyncio
class TestDispatchUserRegistered:
    """Test suite for dispatch_user_registered."""

    async def test_notifies_active_admins_only(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
        test_admin_user: User,
    ) -> None:
        """Test that non-admins and inactive admins are excluded."""
        second_admin = await _make_user(
            db_session, tag="registered-admin2", roles=["admin"]
        )
        inactive_admin = await _make_user(
            db_session,
            tag="registered-admin-off",
            roles=["admin"],
            is_active=False,
        )
        new_user_id = uuid.uuid4()

        with _dispatch_env(db_session):
            await triggers.dispatch_user_registered(
                user_id=new_user_id,
                user_name="Alice",
                user_email="alice@example.com",
            )

        recipients = await _recipients(db_session, "user.registered")
        assert recipients == {test_admin_user.id, second_admin.id}
        assert test_user.id not in recipients
        assert inactive_admin.id not in recipients

        notif = await _single(db_session, "user.registered", test_admin_user.id)
        assert notif.body == (
            'A new user "Alice" has registered and is pending approval.'
        )
        assert notif.data == {"user_id": str(new_user_id)}

    async def test_missing_name_falls_back_to_email(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_admin_user: User,
    ) -> None:
        """Test the ``user_name or user_email`` fallback."""
        with _dispatch_env(db_session):
            await triggers.dispatch_user_registered(
                user_id=uuid.uuid4(),
                user_name=None,
                user_email="alice@example.com",
            )

        notif = await _single(db_session, "user.registered", test_admin_user.id)
        assert "alice@example.com" in notif.body

    async def test_missing_name_and_email_falls_back_to_unknown(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_admin_user: User,
    ) -> None:
        """Test the final ``"Unknown"`` fallback."""
        with _dispatch_env(db_session):
            await triggers.dispatch_user_registered(
                user_id=uuid.uuid4(), user_name=None, user_email=None
            )

        notif = await _single(db_session, "user.registered", test_admin_user.id)
        assert '"Unknown"' in notif.body

    async def test_opted_out_admin_receives_nothing(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_admin_user: User,
    ) -> None:
        """Test that a muted admin is dropped from the admin broadcast."""
        second_admin = await _make_user(
            db_session, tag="registered-admin-muted-peer", roles=["admin"]
        )
        await _mute(db_session, user_id=test_admin_user.id, type_code="user.registered")

        with _dispatch_env(db_session):
            await triggers.dispatch_user_registered(
                user_id=uuid.uuid4(), user_name="Alice", user_email=None
            )

        assert await _recipients(db_session, "user.registered") == {second_admin.id}


# ── user.approved ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDispatchUserApproved:
    """Test suite for dispatch_user_approved."""

    async def test_notifies_only_the_approved_user(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
        test_admin_user: User,
    ) -> None:
        """Test that neither the approving admin nor bystanders are notified."""
        with _dispatch_env(db_session):
            await triggers.dispatch_user_approved(user_id=test_user.id)

        recipients = await _recipients(db_session, "user.approved")
        assert recipients == {test_user.id}
        assert test_admin_user.id not in recipients

        notif = await _single(db_session, "user.approved", test_user.id)
        assert notif.body == (
            "Your account has been approved! You can now access all features."
        )

    async def test_opted_out_user_receives_nothing(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test that a muted recipient produces no notification row."""
        await _mute(db_session, user_id=test_user.id, type_code="user.approved")

        with _dispatch_env(db_session):
            await triggers.dispatch_user_approved(user_id=test_user.id)

        assert await _rows(db_session, "user.approved") == []


# ── user.rejected ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestDispatchUserRejected:
    """Test suite for dispatch_user_rejected."""

    async def test_english_body_with_reason(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
        test_admin_user: User,
    ) -> None:
        """Test the English detail fragment and the exact recipient set."""
        with _dispatch_env(db_session):
            await triggers.dispatch_user_rejected(
                user_id=test_user.id, reason="Duplicate account"
            )

        recipients = await _recipients(db_session, "user.rejected")
        assert recipients == {test_user.id}
        assert test_admin_user.id not in recipients

        notif = await _single(db_session, "user.rejected", test_user.id)
        assert notif.body == (
            "Your account request has been rejected. Reason: Duplicate account"
        )

    async def test_english_body_without_reason(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test that the English detail fragment collapses to empty."""
        with _dispatch_env(db_session):
            await triggers.dispatch_user_rejected(user_id=test_user.id)

        notif = await _single(db_session, "user.rejected", test_user.id)
        assert notif.body == "Your account request has been rejected."

    async def test_german_body_with_reason(
        self,
        db_session: AsyncSession,
        seeded_types: None,
    ) -> None:
        """Test the German detail fragment."""
        german = await _make_user(db_session, tag="de-rejected", language="de")

        with _dispatch_env(db_session):
            await triggers.dispatch_user_rejected(
                user_id=german.id, reason="Doppeltes Konto"
            )

        notif = await _single(db_session, "user.rejected", german.id)
        assert notif.body == (
            "Ihre Kontoanfrage wurde abgelehnt. Grund: Doppeltes Konto"
        )

    async def test_german_body_without_reason(
        self,
        db_session: AsyncSession,
        seeded_types: None,
    ) -> None:
        """Test that the German detail fragment collapses to empty."""
        german = await _make_user(db_session, tag="de-rejected-bare", language="de")

        with _dispatch_env(db_session):
            await triggers.dispatch_user_rejected(user_id=german.id)

        notif = await _single(db_session, "user.rejected", german.id)
        assert notif.body == "Ihre Kontoanfrage wurde abgelehnt."

    async def test_opted_out_user_receives_nothing(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test that a muted recipient produces no notification row."""
        await _mute(db_session, user_id=test_user.id, type_code="user.rejected")

        with _dispatch_env(db_session):
            await triggers.dispatch_user_rejected(
                user_id=test_user.id, reason="Duplicate account"
            )

        assert await _rows(db_session, "user.rejected") == []


# ── error handling ────────────────────────────────────────────────


@pytest.mark.asyncio
class TestTriggerErrorHandling:
    """Every trigger logs and swallows failures so BackgroundTasks survive."""

    async def test_service_failure_is_logged_and_never_propagates(
        self,
        db_session: AsyncSession,
        seeded_types: None,
        test_user: User,
    ) -> None:
        """Test each trigger's except branch with a service that blows up."""
        for name, invoke in _all_invocations(test_user.id):
            with (
                _dispatch_env(db_session),
                patch(
                    f"{MODULE}.NotificationService",
                    side_effect=RuntimeError("service down"),
                ),
                patch(f"{MODULE}.logger") as mock_logger,
            ):
                await invoke()

            assert mock_logger.exception.call_count == 1, name
            assert await _rows(db_session) == [], name

    async def test_unknown_type_code_produces_no_rows(
        self,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that an unseeded type code is treated as muted, not an error."""
        with _dispatch_env(db_session):
            await triggers.dispatch_user_approved(user_id=test_user.id)

        assert await _rows(db_session) == []
