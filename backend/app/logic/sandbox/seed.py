"""One event's worth of believable data, built around *now*.

The shape here is not arbitrary — it is dictated by the guided tour. Every
screen the tour stops on has an empty state, and an empty state is a worse
first impression than no demo at all, so the seed has a minimum it must satisfy:

* the event spans days either side of today, so the week columns have
  something in every direction and the event never reads as expired;
* shifts land in the past, today and the future, so fill-rate badges, the
  "happening now" markers and the booking history all have material;
* some shifts are full and some are half empty, because a board where
  everything is green teaches the reader nothing about what the app is for;
* the visitor already holds a booking, so "My bookings" is not blank on arrival;
* there are teammates with availabilities, because the staffing heatmap is one
  of the more convincing screens and it needs more than one person;
* the manager variant additionally gets a pending invitation and a pending join
  request, so the two decisions an organiser actually makes are on screen.

Shifts are produced through ``logic.shift_generator`` and recorded as a real
``ShiftBatch`` with the generation config stored on the task, rather than being
hand-rolled row by row. That is what makes the manager tour's "add more shifts"
step work: the regenerate screen reads that config back, and a task seeded
without it opens an empty form.

Rows are added with ``db.add`` and a single ``flush`` per stage rather than
through ``CRUDBase.create``, which flushes and refreshes once per row — the
difference is a few hundred round trips on every click of the demo button.
"""

import datetime as dt
import secrets
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.user_availability import user_availability as crud_user_availability
from app.logic.shift_generator import generate_shifts
from app.models.booking import Booking
from app.models.event import Event
from app.models.event_invitation import EventInvitation
from app.models.event_join_request import EventJoinRequest
from app.models.event_membership import EventMembership
from app.models.shift import Shift
from app.models.shift_batch import ShiftBatch
from app.models.task import Task
from app.models.user import User
from app.schemas.sandbox import SandboxRole
from app.schemas.user_availability import (
    UserAvailabilityCreate,
    UserAvailabilityDateInput,
)

# The demo is not a stress test — it is a screenshot that happens to be
# interactive. These numbers are what fills the screens the tour visits without
# making the first page load feel slow.
_DAYS_BEFORE_TODAY = 3
_DAYS_AFTER_TODAY = 11
_TEAMMATE_COUNT = 5


@dataclass(frozen=True, slots=True)
class _TaskSpec:
    """One seeded task, in the two languages the app ships."""

    name_en: str
    name_de: str
    description_en: str
    description_de: str
    location_en: str
    location_de: str
    category_en: str
    category_de: str
    day_offsets: tuple[int, ...]
    start_hour: int
    end_hour: int
    duration_minutes: int
    people_per_shift: int

    def name(self, lang: str) -> str:
        return self.name_de if lang == "de" else self.name_en

    def description(self, lang: str) -> str:
        return self.description_de if lang == "de" else self.description_en

    def location(self, lang: str) -> str:
        return self.location_de if lang == "de" else self.location_en

    def category(self, lang: str) -> str:
        return self.category_de if lang == "de" else self.category_en


# Deliberately mundane. A demo event about a summer festival invites the reader
# to imagine their own rota; one about "Demo Task 1" invites them to close the
# tab. Offsets are relative to today, so the data is always current.
_TASK_SPECS: tuple[_TaskSpec, ...] = (
    _TaskSpec(
        name_en="Welcome desk",
        name_de="Empfang",
        description_en=(
            "Greet arrivals, hand out programmes and point people at the right "
            "hall. The busiest hour is the first one."
        ),
        description_de=(
            "Ankommende begrüßen, Programme austeilen und den Weg zur richtigen "
            "Halle zeigen. Die erste Stunde ist die vollste."
        ),
        location_en="Main entrance",
        location_de="Haupteingang",
        category_en="Front of house",
        category_de="Empfang",
        day_offsets=(-2, 0, 1, 3, 5),
        start_hour=9,
        end_hour=15,
        duration_minutes=120,
        people_per_shift=2,
    ),
    _TaskSpec(
        name_en="Café counter",
        name_de="Cafétheke",
        description_en=(
            "Coffee, cake and washing up. Two people per shift, one on the "
            "machine and one on the till."
        ),
        description_de=(
            "Kaffee, Kuchen und Abwasch. Zwei Personen pro Schicht, eine an der "
            "Maschine und eine an der Kasse."
        ),
        location_en="Foyer café",
        location_de="Foyer-Café",
        category_en="Catering",
        category_de="Verpflegung",
        day_offsets=(-1, 0, 2, 4, 6),
        start_hour=10,
        end_hour=16,
        duration_minutes=90,
        people_per_shift=2,
    ),
    _TaskSpec(
        name_en="Stage crew",
        name_de="Bühnentechnik",
        description_en=(
            "Set up between acts, mind the cables and pack down at the end. "
            "Some heavy lifting."
        ),
        description_de=(
            "Zwischen den Auftritten umbauen, auf die Kabel achten und am Ende "
            "abbauen. Teilweise schweres Heben."
        ),
        location_en="Main hall",
        location_de="Große Halle",
        category_en="Technical",
        category_de="Technik",
        day_offsets=(1, 4, 7, 9),
        start_hour=14,
        end_hour=20,
        duration_minutes=120,
        people_per_shift=3,
    ),
    _TaskSpec(
        name_en="Closing tidy-up",
        name_de="Aufräumen",
        description_en=(
            "The unglamorous one. Chairs stacked, bins out, floor swept — an "
            "hour with enough hands, an evening without."
        ),
        description_de=(
            "Die undankbare Schicht. Stühle stapeln, Müll rausbringen, fegen — "
            "mit genug Händen eine Stunde, ohne einen ganzen Abend."
        ),
        location_en="Whole venue",
        location_de="Gesamtes Gelände",
        category_en="Logistics",
        category_de="Logistik",
        day_offsets=(0, 3, 6, 8, 10),
        start_hour=18,
        end_hour=21,
        duration_minutes=90,
        people_per_shift=4,
    ),
)

_TEAMMATE_NAMES: tuple[tuple[str, str], ...] = (
    ("Mira Lindqvist", "Empfang"),
    ("Tomas Neruda", "Verpflegung"),
    ("Adaeze Okafor", "Technik"),
    ("Ben Halvorsen", "Logistik"),
    ("Yuki Tanabe", "Empfang"),
)

_EVENT_NAME = {
    "en": "Riverside Summer Festival",
    "de": "Sommerfest am Fluss",
}
_EVENT_DESCRIPTION = {
    "en": (
        "A three-weekend village festival run entirely by volunteers. This is a "
        "demo event: everything in it is made up, and it disappears when you "
        "leave."
    ),
    "de": (
        "Ein Dorffest über drei Wochenenden, komplett ehrenamtlich gestemmt. "
        "Dies ist ein Demo-Event: alles darin ist erfunden und verschwindet, "
        "sobald du gehst."
    ),
}
_GUEST_NAME = {"en": "Demo visitor", "de": "Demo-Gast"}


def guest_display_name(language: str) -> str:
    """What the guest is called on every shift they book.

    Exposed because ``service`` mints the user before the event exists, and a
    guest showing up as ``None`` on the staffing board undoes the illusion.
    """
    return _GUEST_NAME.get(language, _GUEST_NAME["en"])


async def seed_sandbox(
    db: AsyncSession,
    *,
    owner: User,
    role: SandboxRole,
    language: str,
    now: dt.datetime,
    expires_at: dt.datetime,
) -> Event:
    """Build the demo event and everything in it. Returns the event.

    ``owner`` must already exist and be flushed — the memberships and the
    ``created_by_id`` below need its id.
    """
    lang = "de" if language == "de" else "en"
    today = now.date()
    rng = _DeterministicRng(seed=owner.id.int)

    event = Event(
        name=_EVENT_NAME[lang],
        description=_EVENT_DESCRIPTION[lang],
        start_date=today - dt.timedelta(days=_DAYS_BEFORE_TODAY),
        end_date=today + dt.timedelta(days=_DAYS_AFTER_TODAY),
        default_start_time=dt.time(hour=9),
        default_end_time=dt.time(hour=21),
        status="published",
        # Private, not public. A sandbox is excluded from Discover by an
        # explicit filter, but visibility is the second lock on that door and
        # costs nothing.
        visibility="private",
        is_featured=False,
        is_sandbox=True,
        sandbox_expires_at=expires_at,
        created_by_id=owner.id,
    )
    db.add(event)
    await db.flush()

    # The role is the whole configuration of the demo. ``member`` hides every
    # management screen behind the router's requiresEventManager guard, which
    # is exactly what the helper track wants to show; ``owner`` opens them.
    db.add(
        EventMembership(
            user_id=owner.id,
            event_id=event.id,
            role="owner" if role == "manager" else "member",
        )
    )

    teammates = _build_teammates(lang=lang, count=_TEAMMATE_COUNT)
    for teammate in teammates:
        db.add(teammate)
    await db.flush()

    for teammate in teammates:
        db.add(EventMembership(user_id=teammate.id, event_id=event.id, role="member"))

    _tasks, shifts = await _seed_tasks_and_shifts(
        db, event=event, owner=owner, lang=lang, today=today
    )
    await _seed_bookings(
        db,
        shifts=shifts,
        owner=owner,
        teammates=teammates,
        today=today,
        rng=rng,
    )
    await _seed_availabilities(db, event=event, teammates=teammates, rng=rng)

    if role == "manager":
        await _seed_pending_decisions(db, event=event, owner=owner, lang=lang, now=now)

    await db.flush()
    return event


async def _seed_tasks_and_shifts(
    db: AsyncSession,
    *,
    event: Event,
    owner: User,
    lang: str,
    today: dt.date,
) -> tuple[list[Task], list[Shift]]:
    """Create each task with a real batch, so the regenerate screen works."""
    tasks: list[Task] = []
    for spec in _TASK_SPECS:
        dates = [today + dt.timedelta(days=offset) for offset in spec.day_offsets]
        task = Task(
            name=spec.name(lang),
            description=spec.description(lang),
            start_date=min(dates),
            end_date=max(dates),
            status="published",
            created_by_id=owner.id,
            event_id=event.id,
            is_sandbox=True,
            location=spec.location(lang),
            category=spec.category(lang),
            shift_duration_minutes=spec.duration_minutes,
            default_start_time=dt.time(hour=spec.start_hour),
            default_end_time=dt.time(hour=spec.end_hour),
            people_per_shift=spec.people_per_shift,
            schedule_overrides=None,
        )
        db.add(task)
        tasks.append(task)
    await db.flush()

    shifts: list[Shift] = []
    for spec, task in zip(_TASK_SPECS, tasks, strict=True):
        dates = [today + dt.timedelta(days=offset) for offset in spec.day_offsets]
        batch = ShiftBatch(
            task_id=task.id,
            label=None,
            start_date=min(dates),
            end_date=max(dates),
            location=spec.location(lang),
            category=spec.category(lang),
            default_start_time=dt.time(hour=spec.start_hour),
            default_end_time=dt.time(hour=spec.end_hour),
            shift_duration_minutes=spec.duration_minutes,
            people_per_shift=spec.people_per_shift,
            remainder_mode="drop",
            schedule_overrides=None,
        )
        db.add(batch)
        await db.flush()

        generated = generate_shifts(
            task_id=task.id,
            task_name=task.name,
            start_date=min(dates),
            end_date=max(dates),
            default_start_time=dt.time(hour=spec.start_hour),
            default_end_time=dt.time(hour=spec.end_hour),
            shift_duration_minutes=spec.duration_minutes,
            people_per_shift=spec.people_per_shift,
            remainder_mode="drop",
            location=spec.location(lang),
            category=spec.category(lang),
            specific_dates=dates,
        )
        for shift_in in generated:
            shift = Shift(
                task_id=task.id,
                batch_id=batch.id,
                title=shift_in.title,
                description=shift_in.description,
                date=shift_in.date,
                start_time=shift_in.start_time,
                end_time=shift_in.end_time,
                location=shift_in.location,
                category=shift_in.category,
                max_bookings=shift_in.max_bookings,
            )
            db.add(shift)
            shifts.append(shift)
    await db.flush()
    return tasks, shifts


async def _seed_bookings(
    db: AsyncSession,
    *,
    shifts: list[Shift],
    owner: User,
    teammates: list[User],
    today: dt.date,
    rng: "_DeterministicRng",
) -> None:
    """Fill the rota unevenly, and put the visitor on it.

    Uneven on purpose: a board where every shift is full says nothing about
    what the app is for. Past shifts are filled harder than future ones,
    because that is what a real rota looks like and it makes the reporting
    charts show a trend rather than a flat line.
    """
    taken: dict[uuid.UUID, int] = {}

    def _book(shift: Shift, user: User) -> None:
        used = taken.get(shift.id, 0)
        if used >= shift.max_bookings:
            return
        taken[shift.id] = used + 1
        db.add(Booking(shift_id=shift.id, user_id=user.id, status="confirmed"))

    for shift in shifts:
        past = shift.date < today
        # Roughly 85% of past capacity filled, 45% of what is still to come.
        fill_chance = 85 if past else 45
        for teammate in teammates:
            if rng.percent() < fill_chance:
                _book(shift, teammate)

    # The visitor's own bookings — one already behind them and two ahead, so
    # "My bookings" has both a history and something to look forward to, and
    # the dashboard counter is never zero.
    upcoming = [s for s in shifts if s.date >= today]
    past_shifts = [s for s in shifts if s.date < today]
    for shift in _pick_spread(upcoming, 2) + _pick_spread(past_shifts, 1):
        # Force room for the guest even on a shift the loop above filled.
        taken[shift.id] = min(taken.get(shift.id, 0), shift.max_bookings - 1)
        _book(shift, owner)


async def _seed_availabilities(
    db: AsyncSession,
    *,
    event: Event,
    teammates: list[User],
    rng: "_DeterministicRng",
) -> None:
    """Give the staffing heatmap a spread of greens rather than one flat block."""
    event_days = [
        event.start_date + dt.timedelta(days=offset)
        for offset in range((event.end_date - event.start_date).days + 1)
    ]
    windows = ((9, 17), (10, 18), (8, 16), (14, 22))

    for index, teammate in enumerate(teammates):
        kind = index % 3
        dates: list[dt.date | UserAvailabilityDateInput] = []
        start_time: dt.time | None = None
        end_time: dt.time | None = None

        if kind == 0:
            availability_type = "fully_available"
        elif kind == 1:
            availability_type = "time_range"
            window = windows[index % len(windows)]
            start_time = dt.time(hour=window[0])
            end_time = dt.time(hour=window[1])
        else:
            availability_type = "specific_dates"
            for day in event_days:
                if rng.percent() < 60:
                    continue
                if rng.percent() < 50:
                    dates.append(day)
                else:
                    first = 8 + (rng.percent() % 5)
                    dates.append(
                        UserAvailabilityDateInput(
                            date=day,
                            start_time=dt.time(hour=first),
                            end_time=dt.time(hour=min(21, first + 6)),
                        )
                    )
            if not dates:
                dates.append(event_days[0])

        await crud_user_availability.upsert_for_user(
            db,
            user_id=teammate.id,
            event_id=event.id,
            obj_in=UserAvailabilityCreate(
                availability_type=availability_type,  # type: ignore[arg-type]
                default_start_time=start_time,
                default_end_time=end_time,
                dates=dates,
            ),
        )


async def _seed_pending_decisions(
    db: AsyncSession,
    *,
    event: Event,
    owner: User,
    lang: str,
    now: dt.datetime,
) -> None:
    """One invitation and one join request, both still waiting.

    Manager-only. These are the two decisions running an event actually
    consists of, and both screens read as broken when empty.

    The invitation address is on ``example.invalid`` — reserved by RFC 2606 and
    guaranteed never to resolve. Nothing in the demo may send mail, and the
    route-level guard is the thing that enforces that; this is the second lock,
    for the case where someone adds a new send path and forgets.
    """
    db.add(
        EventInvitation(
            event_id=event.id,
            email="sam.rivera@example.invalid",
            role="member",
            token=secrets.token_urlsafe(32),
            invited_by_id=owner.id,
            expires_at=now + dt.timedelta(days=14),
        )
    )
    requester = User(
        subject=f"sandbox|{uuid.uuid4().hex}",
        email=None,
        name="Ellis Vaughan" if lang == "en" else "Elli Vaughan",
        is_sandbox=True,
        is_active=True,
        email_verified=False,
        preferred_language=lang,
        roles=[],
    )
    db.add(requester)
    # Flushed before the two rows that point at it. Neither EventJoinRequest nor
    # EventMembership declares an ORM ``Relationship`` to User — both carry a
    # bare ``sa.ForeignKey`` — so SQLAlchemy's unit of work has no dependency
    # edge to order the INSERTs by and falls back to the mapper sort key, which
    # is the qualified class name. ``event_join_request`` sorts before ``user``,
    # so without this the join request is inserted first, every time, and the
    # request dies on a foreign-key violation. Deterministic, not a race.
    await db.flush()
    db.add(
        EventJoinRequest(
            user_id=requester.id,
            event_id=event.id,
            status="pending",
            message=(
                "I helped at the café last year and would like to again."
                if lang == "en"
                else "Ich habe letztes Jahr im Café geholfen und würde gern wieder."
            ),
        )
    )
    # The requester is a guest of this event too, so the purge finds and
    # removes them — membership is how ``cleanup`` enumerates the guests.
    db.add(EventMembership(user_id=requester.id, event_id=event.id, role="member"))


def _build_teammates(*, lang: str, count: int) -> list[User]:
    """Fake colleagues.

    ``email`` is None on every one of them, which is not laziness — it is what
    makes them unmailable by construction. ``send_verify_email`` and
    ``request_password_reset`` both short-circuit on a missing address, so even
    a future code path that forgets the ``sandbox|`` check cannot reach them.
    """
    return [
        User(
            subject=f"sandbox|{uuid.uuid4().hex}",
            email=None,
            name=name,
            is_sandbox=True,
            is_active=True,
            email_verified=False,
            preferred_language=lang,
            roles=[],
        )
        for name, _ in _TEAMMATE_NAMES[:count]
    ]


def _pick_spread(items: list[Shift], wanted: int) -> list[Shift]:
    """Take up to ``wanted`` items spread across the list rather than clumped."""
    if not items or wanted <= 0:
        return []
    if len(items) <= wanted:
        return list(items)
    step = len(items) // wanted
    return [items[i * step] for i in range(wanted)]


class _DeterministicRng:
    """A tiny reproducible generator, seeded from the guest's id.

    Not ``random.Random``: two visitors clicking the button in the same second
    should get differently shaped rotas, and the same visitor reloading should
    not see the rota reshuffle. Seeding from the account id gives both, and it
    makes a failing seed reproducible from the row alone.
    """

    __slots__ = ("_state",)

    def __init__(self, *, seed: int) -> None:
        self._state = seed & 0xFFFFFFFF or 0x9E3779B9

    def percent(self) -> int:
        """Next value in [0, 100)."""
        # xorshift32 — enough randomness for deciding who takes which shift.
        x = self._state
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= x >> 17
        x ^= (x << 5) & 0xFFFFFFFF
        self._state = x
        return x % 100
