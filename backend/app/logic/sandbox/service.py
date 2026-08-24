"""Minting a demo: the gate, the ceiling, the guest, the seed, the session.

The order of the first three steps is the whole safety story of this feature,
and it is deliberately boring:

1. **The gate.** ``SANDBOX_ENABLED`` off means the endpoint does not exist, not
   that it fails politely. A deployment that does not want anonymous writes
   gets none.
2. **The sweep.** Expired demos are purged *before* the new one is counted.
   This is what makes the feature self-cleaning without a scheduler: the only
   way to accumulate sandboxes is to keep creating them, and creating one is
   exactly when the old ones are collected.
3. **The ceiling.** Counted in SQL against live rows. It has to be, because the
   rate limiter cannot serve as one — its counters live in a single worker
   process and it returns immediately when ``TESTING`` is set.

Only then is anything written.
"""

import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.core.config import settings
from app.core.errors import raise_problem
from app.core.logger import get_logger
from app.logic.auth import service as auth_service
from app.logic.auth.service import SignedInSession
from app.logic.sandbox.cleanup import count_active, purge_sandbox, sweep_expired
from app.logic.sandbox.seed import guest_display_name, seed_sandbox
from app.models.event import Event
from app.models.user import User
from app.schemas.sandbox import SandboxRole

logger = get_logger(__name__)

SANDBOX_SUBJECT_PREFIX = "sandbox|"


def utc_now() -> dt.datetime:
    """Naive UTC, matching every stored timestamp in this application.

    ``Base.created_at`` and every hand-written datetime column are
    ``TIMESTAMP WITHOUT TIME ZONE`` holding UTC. Writing an aware value into
    one is rejected by the driver; comparing an aware value against one raises.
    """
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


async def create_sandbox(
    db: AsyncSession,
    *,
    role: SandboxRole,
    language: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[SignedInSession, Event]:
    """Mint a guest, seed them an event, and sign them in.

    Returns the session and the event. The caller (``api.routes.auth``) owns
    the cookie and the status code; the transaction is committed by
    ``api.deps.get_db``, so a failure anywhere below leaves nothing behind.
    """
    if not settings.SANDBOX_ENABLED:
        raise_problem(
            404,
            code="sandbox.disabled",
            detail="The demo is not available on this deployment",
        )

    now = utc_now()
    swept = await sweep_expired(db, now=now)
    if swept:
        logger.info("swept expired sandboxes", extra={"count": swept})

    if await count_active(db, now=now) >= settings.SANDBOX_MAX_ACTIVE:
        raise_problem(
            503,
            code="sandbox.capacity_reached",
            detail="Too many demos are running right now. Please try again shortly.",
            headers={"Retry-After": "300"},
        )

    guest = User(
        subject=f"{SANDBOX_SUBJECT_PREFIX}{uuid.uuid4().hex}",
        # No address, on purpose and load-bearing. ``send_verify_email`` and
        # ``request_password_reset`` both short-circuit on a missing one, so a
        # guest cannot be mailed even by a future code path that forgets to
        # check the subject prefix. Nothing about the demo needs an inbox.
        email=None,
        # ``password_hash`` stays NULL, which ``verify_password`` folds to a
        # failed comparison — this account can never be logged into, only
        # handed out here.
        password_hash=None,
        name=guest_display_name(language),
        email_verified=False,
        is_active=True,
        is_sandbox=True,
        preferred_language=language,
        roles=[],
    )
    db.add(guest)
    await db.flush()

    event = await seed_sandbox(
        db,
        owner=guest,
        role=role,
        language=language,
        now=now,
        expires_at=now + dt.timedelta(minutes=settings.SANDBOX_TTL_MINUTES),
    )

    # Set directly rather than through ``PUT /users/me/selected-event``: this is
    # what lets the app open on the dashboard instead of the event picker, and
    # the membership check that endpoint performs is one we have just satisfied
    # ourselves. Doing it before the sign-in means the profile in the response
    # already carries it, so the client never renders a picker frame.
    guest.selected_event_id = event.id
    db.add(guest)
    await db.flush()

    signed_in = await auth_service.sign_in_user(
        db, user=guest, user_agent=user_agent, ip_address=ip_address
    )
    logger.info(
        "sandbox created",
        extra={
            "event_id": str(event.id),
            "user_id": str(guest.id),
            "role": role,
            "expires_at": event.sandbox_expires_at.isoformat()
            if event.sandbox_expires_at
            else None,
        },
    )
    return signed_in, event


async def event_id_for_guest(db: AsyncSession, *, user: User) -> uuid.UUID | None:
    """Which sandbox this guest is in, if they are a guest at all.

    Resolved from ``created_by_id`` rather than from ``selected_event_id``,
    because the selection is a preference the guest can change and the
    ownership is not.
    """
    if not user.is_sandbox:
        return None
    return (
        (
            await db.execute(
                select(col(Event.id)).where(
                    col(Event.is_sandbox).is_(True),
                    col(Event.created_by_id) == user.id,
                )
            )
        )
        .scalars()
        .first()
    )


async def end_sandbox(db: AsyncSession, *, user: User) -> None:
    """Tear down the demo this guest is in. Raises 403 for a real account.

    Idempotent: a guest whose demo the sweep already collected still gets a
    clean answer, because their session is gone either way and the frontend
    only needs to know it may return to the landing page.
    """
    if not user.is_sandbox:
        raise_problem(
            403,
            code="sandbox.forbidden",
            detail="This is not a demo session",
        )
    event_id = await event_id_for_guest(db, user=user)
    if event_id is not None:
        await purge_sandbox(db, event_id=event_id)
