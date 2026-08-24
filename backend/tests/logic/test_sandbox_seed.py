"""What the seeded demo has to contain for the guided tour to be worth taking.

The failure mode this file exists to prevent is not an exception. It is an
empty screen. The tour stops on the task board, the staffing heatmap, "my
bookings", the regenerate dialog and — on the organiser track — the two pending
decisions, and every one of those screens has an empty state that reads as a
broken product rather than as a demo with nothing in it. A visitor who sees one
of those closes the tab, and nothing anywhere logs why.

So these are not assertions about the seeder's implementation. They are the
minimum contract the tour depends on, written down where a change to
``_TASK_SPECS`` or to the day offsets will trip over them: dates spanning today
in both directions, published tasks that can actually be regenerated, shifts
behind and ahead, a booking already in the visitor's name, teammates with
availabilities, and — for the organiser — one decision of each kind waiting.

The one thing here that is not about the tour is the last class. No account the
seeder creates may have an email address, and that is a safety property rather
than a presentation one: ``send_verify_email`` and ``request_password_reset``
both short-circuit on a missing address, so an address-less guest cannot be
mailed even by a future code path that forgets to check the ``sandbox|`` prefix.
"""

import datetime as dt
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.logic.sandbox.seed import guest_display_name
from app.models.booking import Booking
from app.models.event_invitation import EventInvitation
from app.models.event_join_request import EventJoinRequest
from app.models.event_membership import EventMembership
from app.models.shift import Shift
from app.models.shift_batch import ShiftBatch
from app.models.task import Task
from app.models.user import User
from app.models.user_availability import UserAvailability
from tests.fixtures.sandbox import SandboxFactory, SandboxSetup


async def _tasks(db: AsyncSession, sandbox: SandboxSetup) -> list[Task]:
    rows = await db.execute(
        select(Task)
        .where(col(Task.event_id) == sandbox.event.id)
        .order_by(col(Task.name))
    )
    return list(rows.scalars())


async def _shifts(db: AsyncSession, sandbox: SandboxSetup) -> list[Shift]:
    task_ids = [task.id for task in await _tasks(db, sandbox)]
    rows = await db.execute(select(Shift).where(col(Shift.task_id).in_(task_ids)))
    return list(rows.scalars())


async def _guests(db: AsyncSession, sandbox: SandboxSetup) -> list[User]:
    rows = await db.execute(
        select(User)
        .join(EventMembership, col(EventMembership.user_id) == col(User.id))
        .where(col(EventMembership.event_id) == sandbox.event.id)
    )
    return list(rows.scalars())


# ── The event itself ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestSeededEvent:
    """The frame every other screen is drawn inside."""

    async def test_spans_today_in_both_directions(
        self, test_sandbox: SandboxSetup
    ) -> None:
        """Test that the week view has columns either side of today.

        A demo event that started tomorrow leaves the past half of every
        calendar blank, and one that ended yesterday reads as expired before
        the visitor has clicked anything.
        """
        today = dt.date.today()

        assert test_sandbox.event.start_date < today
        assert test_sandbox.event.end_date > today
        assert test_sandbox.event.is_expired is False

    async def test_is_published_private_and_unfeatured(
        self, test_sandbox: SandboxSetup
    ) -> None:
        """Test the three flags that decide who else can find it.

        Published so the volunteer screens show anything at all; private so
        that visibility is the second lock behind the explicit ``is_sandbox``
        filters; never featured, because the home screen must not carry a card
        for an event that deletes itself within the hour.
        """
        assert test_sandbox.event.status == "published"
        assert test_sandbox.event.visibility == "private"
        assert test_sandbox.event.is_featured is False

    async def test_carries_a_deadline_and_belongs_to_its_guest(
        self, test_sandbox: SandboxSetup
    ) -> None:
        """Test the two columns the whole lifecycle hangs off.

        ``sandbox_expires_at`` is what the sweep selects on and what the demo
        banner counts down to; ``created_by_id`` is how ``event_id_for_guest``
        resolves which demo a session belongs to — from ownership rather than
        from the selection, which the guest can change.
        """
        assert test_sandbox.event.is_sandbox is True
        assert test_sandbox.event.sandbox_expires_at is not None
        assert test_sandbox.event.sandbox_expires_at > dt.datetime.now(
            dt.timezone.utc
        ).replace(tzinfo=None)
        assert test_sandbox.event.created_by_id == test_sandbox.guest.id

    async def test_the_guest_is_a_member_of_it(
        self, db_session: AsyncSession, test_sandbox: SandboxSetup
    ) -> None:
        """Test that the visitor is in their own event, and not alone in it."""
        guests = await _guests(db_session, test_sandbox)

        assert test_sandbox.guest.id in {guest.id for guest in guests}
        assert len(guests) >= 4, (
            "a staffing board with one person on it teaches nothing"
        )


# ── Tasks and shifts ──────────────────────────────────────────────


@pytest.mark.asyncio
class TestSeededTasks:
    """The board the tour opens on, and the dialog it opens next."""

    async def test_has_several_published_tasks(
        self, db_session: AsyncSession, test_sandbox: SandboxSetup
    ) -> None:
        """Test that the task list is populated and visible to a member.

        Published, not draft: drafts are hidden from anyone below ``admin`` in
        the event, so a helper-track visitor would open the app on an empty
        board.
        """
        tasks = await _tasks(db_session, test_sandbox)

        assert len(tasks) >= 2
        assert {task.status for task in tasks} == {"published"}
        assert all(task.is_sandbox for task in tasks), (
            "the denormalised flag is what keeps a task hidden after its event "
            "is gone — tasks.event_id is ON DELETE SET NULL"
        )

    async def test_every_task_can_be_regenerated(
        self, db_session: AsyncSession, test_sandbox: SandboxSetup
    ) -> None:
        """Test that each task carries a batch *and* the config that produced it.

        The organiser tour's "add more shifts" step reads the stored
        generation config back into the regenerate form. A task seeded without
        it opens that form empty, which is the one screen in the tour where an
        empty state looks like the visitor broke something.
        """
        tasks = await _tasks(db_session, test_sandbox)

        for task in tasks:
            assert task.shift_duration_minutes, task.name
            assert task.default_start_time is not None, task.name
            assert task.default_end_time is not None, task.name
            assert task.people_per_shift, task.name

            batch = (
                await db_session.execute(
                    select(ShiftBatch).where(col(ShiftBatch.task_id) == task.id)
                )
            ).scalar_one()
            assert batch.shift_duration_minutes == task.shift_duration_minutes
            assert batch.people_per_shift == task.people_per_shift
            assert batch.default_start_time == task.default_start_time
            assert batch.default_end_time == task.default_end_time

    async def test_every_shift_belongs_to_a_batch(
        self, db_session: AsyncSession, test_sandbox: SandboxSetup
    ) -> None:
        """Test that shifts were generated rather than hand-rolled row by row.

        A shift with no batch cannot be edited or removed as a group, which is
        the workflow the manager screens are built around.
        """
        shifts = await _shifts(db_session, test_sandbox)

        assert shifts
        assert all(shift.batch_id is not None for shift in shifts)

    async def test_shifts_land_behind_today_on_it_and_ahead_of_it(
        self, db_session: AsyncSession, test_sandbox: SandboxSetup
    ) -> None:
        """Test all three of past, today and future are populated.

        Each carries a different screen: past shifts give the reporting charts
        a trend rather than a flat line, today's drive the "happening now"
        markers, and future ones are the only shifts a visitor can actually
        book during the tour.
        """
        today = dt.date.today()
        dates = {shift.date for shift in await _shifts(db_session, test_sandbox)}

        assert any(date < today for date in dates), "nothing behind today"
        assert today in dates, "nothing happening today"
        assert any(date > today for date in dates), "nothing to book"

    async def test_the_rota_is_filled_unevenly(
        self, db_session: AsyncSession, test_sandbox: SandboxSetup
    ) -> None:
        """Test that some shifts are full and some are not.

        A board where every shift is green teaches the reader nothing about
        what the application is for — the gaps are the product.
        """
        shifts = await _shifts(db_session, test_sandbox)
        booked: dict[uuid.UUID | None, int] = {}
        rows = await db_session.execute(
            select(col(Booking.shift_id)).where(
                col(Booking.shift_id).in_([shift.id for shift in shifts])
            )
        )
        for shift_id in rows.scalars():
            booked[shift_id] = booked.get(shift_id, 0) + 1

        fill_rates = {booked.get(shift.id, 0) / shift.max_bookings for shift in shifts}
        assert any(rate >= 1 for rate in fill_rates), "no shift is full"
        assert any(rate < 1 for rate in fill_rates), "no shift has room"


# ── The visitor's own presence in the data ────────────────────────


@pytest.mark.asyncio
class TestSeededBookings:
    """ "My bookings" must not be the first empty screen the visitor sees."""

    async def test_the_visitor_already_holds_bookings(
        self, db_session: AsyncSession, test_sandbox: SandboxSetup
    ) -> None:
        """Test that the guest arrives with a history and something ahead of them.

        Both halves matter: without a past booking the history tab is blank,
        and without a future one the dashboard counter reads zero on arrival —
        which is the number the visitor is being shown the app to avoid.
        """
        shift_by_id = {
            shift.id: shift for shift in await _shifts(db_session, test_sandbox)
        }
        rows = await db_session.execute(
            select(Booking).where(col(Booking.user_id) == test_sandbox.guest.id)
        )
        bookings = list(rows.scalars())
        today = dt.date.today()

        assert bookings
        assert {booking.status for booking in bookings} == {"confirmed"}
        dates = [shift_by_id[booking.shift_id].date for booking in bookings]  # type: ignore[index]
        assert any(date >= today for date in dates), "nothing upcoming"
        assert any(date < today for date in dates), "no history"

    async def test_the_teammates_have_availabilities(
        self, db_session: AsyncSession, test_sandbox: SandboxSetup
    ) -> None:
        """Test that the staffing heatmap has more than one colour on it.

        It is one of the more convincing screens in the application and it
        needs a spread — a single availability type across every teammate
        renders as one flat block.
        """
        rows = await db_session.execute(
            select(UserAvailability).where(
                col(UserAvailability.event_id) == test_sandbox.event.id
            )
        )
        availabilities = list(rows.scalars())

        assert len(availabilities) >= 3
        assert len({a.availability_type for a in availabilities}) >= 2


# ── The two tracks ────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRoleShapesTheDemo:
    """The role picked on the landing page is the whole configuration of the tour."""

    async def test_a_helper_is_a_plain_member(
        self, db_session: AsyncSession, test_sandbox: SandboxSetup
    ) -> None:
        """Test that the volunteer track cannot reach the organiser screens.

        ``member`` is what leaves the management routes behind the frontend's
        ``requiresEventManager`` guard, which is the half of the application
        the helper tour is deliberately not about.
        """
        membership = (
            await db_session.execute(
                select(EventMembership).where(
                    col(EventMembership.user_id) == test_sandbox.guest.id,
                    col(EventMembership.event_id) == test_sandbox.event.id,
                )
            )
        ).scalar_one()

        assert membership.role == "member"

    async def test_a_helper_gets_no_pending_decisions(
        self, db_session: AsyncSession, test_sandbox: SandboxSetup
    ) -> None:
        """Test that the volunteer track is not given an organiser's inbox.

        A helper cannot open either screen, so an invitation and a join request
        seeded for them would be rows nobody could ever see or act on — and
        rows the purge would still have to remember to remove.
        """
        invitations = await db_session.execute(
            select(EventInvitation).where(
                col(EventInvitation.event_id) == test_sandbox.event.id
            )
        )
        requests = await db_session.execute(
            select(EventJoinRequest).where(
                col(EventJoinRequest.event_id) == test_sandbox.event.id
            )
        )

        assert invitations.scalars().all() == []
        assert requests.scalars().all() == []

    async def test_a_manager_owns_the_event(
        self, db_session: AsyncSession, make_sandbox: SandboxFactory
    ) -> None:
        """Test that the organiser track can reach the screens it is about."""
        sandbox = await make_sandbox(role="manager")

        membership = (
            await db_session.execute(
                select(EventMembership).where(
                    col(EventMembership.user_id) == sandbox.guest.id,
                    col(EventMembership.event_id) == sandbox.event.id,
                )
            )
        ).scalar_one()

        assert membership.role == "owner"

    async def test_a_manager_gets_one_decision_of_each_kind(
        self, db_session: AsyncSession, make_sandbox: SandboxFactory
    ) -> None:
        """Test that both organiser inboxes have exactly one thing waiting.

        Approving a request and inviting someone are the two decisions running
        an event actually consists of, and both screens read as broken when
        empty. The invitation address is on ``example.invalid`` — reserved by
        RFC 2606 and guaranteed never to resolve — because nothing in a demo
        may reach a real inbox even if a send path is added later.
        """
        sandbox = await make_sandbox(role="manager")

        invitations = list(
            (
                await db_session.execute(
                    select(EventInvitation).where(
                        col(EventInvitation.event_id) == sandbox.event.id
                    )
                )
            ).scalars()
        )
        requests = list(
            (
                await db_session.execute(
                    select(EventJoinRequest).where(
                        col(EventJoinRequest.event_id) == sandbox.event.id
                    )
                )
            ).scalars()
        )

        assert len(invitations) == 1
        assert invitations[0].email is not None
        assert invitations[0].email.endswith("@example.invalid")
        assert len(requests) == 1
        assert requests[0].status == "pending"

    async def test_the_applicant_is_a_member_so_the_purge_finds_them(
        self, db_session: AsyncSession, make_sandbox: SandboxFactory
    ) -> None:
        """Test that the seeded applicant is enumerable as a guest of the demo.

        ``purge_sandbox`` finds the accounts to delete by joining through
        ``event_memberships``. An applicant seeded without one would survive
        every purge and every sweep, as an account nothing points at.
        """
        sandbox = await make_sandbox(role="manager")
        request = (
            await db_session.execute(
                select(EventJoinRequest).where(
                    col(EventJoinRequest.event_id) == sandbox.event.id
                )
            )
        ).scalar_one()

        membership = (
            await db_session.execute(
                select(EventMembership).where(
                    col(EventMembership.user_id) == request.user_id,
                    col(EventMembership.event_id) == sandbox.event.id,
                )
            )
        ).scalar_one_or_none()

        assert membership is not None


# ── Nothing in here may be contactable ────────────────────────────


@pytest.mark.asyncio
class TestSeededAccounts:
    """No account the seeder creates may be reachable by mail, or signed into."""

    async def test_no_seeded_account_has_an_email_address(
        self, db_session: AsyncSession, test_sandbox: SandboxSetup
    ) -> None:
        """Test that every guest is unmailable by construction.

        Not laziness and not an oversight: ``send_verify_email`` and
        ``request_password_reset`` both short-circuit on a missing address, so
        a NULL here means even a future code path that forgets the ``sandbox|``
        prefix check cannot put anything in anyone's inbox.
        """
        guests = await _guests(db_session, test_sandbox)

        assert guests
        assert all(guest.email is None for guest in guests)
        assert all(guest.is_sandbox for guest in guests)
        assert all(guest.subject.startswith("sandbox|") for guest in guests)

    async def test_no_seeded_account_can_be_signed_into(
        self, db_session: AsyncSession, test_sandbox: SandboxSetup
    ) -> None:
        """Test that ``password_hash`` is NULL on every guest.

        ``verify_password`` folds a NULL hash to a failed comparison, so these
        accounts can only ever be handed out by ``POST /auth/sandbox`` — never
        logged into, and never recovered into by anyone who learns an id.
        """
        guests = await _guests(db_session, test_sandbox)

        assert all(guest.password_hash is None for guest in guests)

    async def test_no_seeded_account_holds_a_platform_role(
        self, db_session: AsyncSession, test_sandbox: SandboxSetup
    ) -> None:
        """Test that a demo cannot mint an administrator.

        ``roles`` is the one remaining platform-wide grant. An anonymous
        visitor being able to cause an ``admin`` row to exist would make this
        endpoint a privilege-escalation path rather than a demo.
        """
        guests = await _guests(db_session, test_sandbox)

        assert all(guest.roles == [] for guest in guests)
        assert all(not guest.is_admin for guest in guests)

    async def test_the_guest_is_named_in_the_language_they_clicked(
        self, make_sandbox: SandboxFactory
    ) -> None:
        """Test that the visitor appears on the staffing board under a real name.

        ``guest_display_name`` exists because the account is minted before the
        event does, and a guest showing up as ``None`` on every shift they hold
        undoes the illusion the demo is built on.
        """
        assert guest_display_name("en") == "Demo visitor"
        assert guest_display_name("de") == "Demo-Gast"
        assert guest_display_name("fr") == "Demo visitor", "unknown falls back to en"

        german = await make_sandbox(language="de")
        assert german.guest.name == "Demo-Gast"
        assert german.guest.preferred_language == "de"

    async def test_two_demos_are_shaped_differently(
        self, db_session: AsyncSession, make_sandbox: SandboxFactory
    ) -> None:
        """Test that the rota is seeded from the guest's id, not from a constant.

        Two visitors clicking the button in the same second should not get
        byte-identical rotas — and the same visitor reloading should not see
        theirs reshuffle, which is why the seed is the account id rather than
        the clock.

        Compared as the whole fill pattern rather than as a total: two totals
        can coincide by chance often enough to make this test flap, while two
        fifty-odd-shift patterns coinciding would mean the generator had
        stopped depending on its seed.
        """
        first = await make_sandbox()
        second = await make_sandbox()

        async def _fill_pattern(sandbox: SandboxSetup) -> tuple[int, ...]:
            shifts = sorted(
                await _shifts(db_session, sandbox),
                key=lambda s: (s.title or "", s.date, s.start_time),
            )
            rows = await db_session.execute(
                select(col(Booking.shift_id)).where(
                    col(Booking.shift_id).in_([shift.id for shift in shifts])
                )
            )
            taken: dict[uuid.UUID | None, int] = {}
            for shift_id in rows.scalars():
                taken[shift_id] = taken.get(shift_id, 0) + 1
            return tuple(taken.get(shift.id, 0) for shift in shifts)

        first_pattern = await _fill_pattern(first)
        second_pattern = await _fill_pattern(second)

        assert len(first_pattern) == len(second_pattern) > 0
        assert first_pattern != second_pattern
