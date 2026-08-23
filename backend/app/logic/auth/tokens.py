"""The lifecycle of every long-lived secret this application hands out.

Two kinds live here, and they are deliberately kept apart from the access
token, which has no lifecycle at all — it is signed, it is short, it expires,
and nothing server-side remembers it.

**Refresh tokens** (``auth_sessions``). One per signed-in device. Opaque, 30
days, stored only as a sha256 digest, and rotated on every use. Rotation is
what turns a stolen cookie from a permanent key into a race the thief has to
keep winning: the moment either party refreshes, the other's copy is dead, and
presenting a dead token is treated as evidence of theft (see
``rotate_refresh_session``).

**Email-borne tokens** (``user_tokens``). One per outstanding verification or
reset link. Also opaque and also stored hashed, so a leak of that table hands
out nothing. They are single-use and purpose-bound: a verification link that
escapes an inbox cannot be replayed as a password reset.

Every failure in this module is raised as an ``auth.*`` problem, because in
every case the honest answer to the caller is an HTTP status and a sentence,
and there is nothing further up the stack that could decide better.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import raise_problem
from app.core.logger import get_logger
from app.core.security import generate_token, hash_token
from app.crud.auth_session import auth_session as crud_auth_session
from app.crud.user_token import user_token as crud_user_token
from app.models.auth_session import AuthSession
from app.models.user_token import UserToken
from app.schemas.auth import AuthSessionCreate, UserTokenCreate, UserTokenPurpose

logger = get_logger(__name__)


def _now() -> datetime:
    """Naive UTC, matching every stored timestamp in this schema.

    Comparing a naive column against an aware ``datetime.now(timezone.utc)``
    raises ``TypeError`` — and it would do so in the refresh path, on a live
    session, rather than anywhere a test would notice.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _refresh_expiry() -> datetime:
    """When a refresh token minted right now should lapse.

    The window slides: every rotation gets the full period again, so a person
    who uses the app weekly stays signed in indefinitely while an abandoned
    session dies thirty days after it was last touched. That is the property
    worth having — an absolute cap would sign out the active majority to
    inconvenience nobody.
    """
    return _now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


def _user_token_expiry(purpose: UserTokenPurpose) -> datetime:
    """When an email-borne token of this purpose should lapse.

    The two lifetimes differ by more than an order of magnitude on purpose. A
    reset link is a live password sitting in an inbox, so it gets an hour. A
    verification link grants nothing on its own — sign-in is not blocked on an
    unverified address — and is routinely opened the next day on a phone, so it
    gets two days.
    """
    hours = (
        settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS
        if purpose == "reset_password"
        else settings.EMAIL_VERIFY_TOKEN_EXPIRE_HOURS
    )
    return _now() + timedelta(hours=hours)


@dataclass(frozen=True, slots=True)
class IssuedRefreshToken:
    """A freshly minted session and the raw token that opens it.

    The raw value exists only here and in the response that carries it into the
    client's cookie; the row holds nothing but its digest. Pairing the two in
    one object is what stops a caller from persisting the session and then
    forgetting to hand the secret back.
    """

    session: AuthSession
    raw_token: str


# ── Refresh sessions ──────────────────────────────────────────────


async def issue_refresh_session(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> IssuedRefreshToken:
    """Open a new session for a user and return its refresh token."""
    raw_token = generate_token()
    session_row = await crud_auth_session.create(
        db,
        obj_in=AuthSessionCreate(
            user_id=user_id,
            refresh_token_hash=hash_token(raw_token),
            expires_at=_refresh_expiry(),
            user_agent=user_agent,
            ip_address=ip_address,
        ),
    )
    return IssuedRefreshToken(session=session_row, raw_token=raw_token)


async def rotate_refresh_session(
    db: AsyncSession, *, raw_token: str
) -> IssuedRefreshToken:
    """Spend a refresh token and return its replacement.

    The presented session is **revoked and a new row takes its place**, rather
    than the hash being swapped in place. That costs a row per refresh and buys
    the one thing this design exists for: after rotation the old digest still
    matches something, and what it matches is a dead session. A thief replaying
    a token the legitimate client has already spent therefore lands in the
    branch below instead of looking indistinguishable from a typo.

    Four outcomes, in order:

    * **No such token** — 401. Nothing to act on; the value never existed here,
      or the row was cascaded away with a deleted account.
    * **Already revoked** — theft, until proven otherwise. Either this token was
      rotated away (so someone is holding a copy of a secret they should have
      discarded) or the session was ended deliberately and someone kept the
      cookie. Both mean the account may be in two pairs of hands, so *every*
      session it owns is revoked and everyone signs in again. This is D7 in the
      migration spec, and it is the whole reason revoked rows are kept.
    * **Expired** — 401, and the row is closed on the way out so a later replay
      of the same value takes the theft branch rather than the expiry branch.
    * **Live** — revoke, mint, hand back.

    The known false positive: two tabs refreshing in the same instant, where the
    second still holds the token the first just spent, signs the account out
    everywhere. The client dedupes concurrent refreshes behind a single promise
    precisely so this stays a theoretical race, and the alternative — a grace
    window in which a spent token still works — is exactly the hole rotation is
    meant to close.
    """
    presented = await crud_auth_session.get_by_token_hash(
        db, token_hash=hash_token(raw_token)
    )
    if presented is None:
        raise_problem(
            401,
            code="auth.invalid_token",
            detail="Your session could not be renewed. Please sign in again.",
        )

    if presented.revoked_at is not None:
        revoked_count = await crud_auth_session.revoke_all_for_user(
            db, user_id=presented.user_id
        )
        # Commit before raising. ``deps.get_db`` owns this transaction inside an
        # exit stack, and unwinding it with an exception rolls it back — so the
        # 401 below would otherwise undo the very revocation it is reporting,
        # leaving reuse detection as a log line and nothing more. Every other
        # write in this codebase can rely on the ambient transaction precisely
        # because it does not also raise; this one does.
        await db.commit()
        # Logged at WARNING with no token material: the user id is what an
        # operator needs to answer "was this account compromised?", and the
        # digest would tell them nothing they could act on.
        logger.warning(
            f"Refresh token reuse detected for user {presented.user_id}; "
            f"revoked {revoked_count} remaining session(s)."
        )
        raise_problem(
            401,
            code="auth.session_revoked",
            detail=(
                "This session was ended for security reasons. Please sign in again."
            ),
        )

    if presented.expires_at <= _now():
        _ = await crud_auth_session.revoke(db, db_obj=presented)
        raise_problem(
            401,
            code="auth.token_expired",
            detail="Your session has expired. Please sign in again.",
        )

    _ = await crud_auth_session.revoke(db, db_obj=presented)
    issued = await issue_refresh_session(
        db,
        user_id=presented.user_id,
        user_agent=presented.user_agent,
        ip_address=presented.ip_address,
    )

    # The successor inherits the original sign-in time. Without this the
    # Security settings card would show every active device as having signed in
    # fifteen minutes ago — ``AuthSessionRead.created_at`` is documented as
    # "when this device signed in", and ``list_active_for_user`` orders by it to
    # put the newest sign-in first. Both statements stay true only if the
    # timestamp survives rotation.
    issued.session.created_at = presented.created_at
    issued.session.last_used_at = _now()
    db.add(issued.session)
    await db.flush()

    return issued


async def revoke_refresh_session(db: AsyncSession, *, raw_token: str | None) -> bool:
    """End the session a refresh token belongs to. Never raises.

    This is sign-out, and sign-out has exactly one acceptable outcome: the
    client ends up signed out. An unknown, malformed or missing token means the
    session is already gone, which is the state the caller asked for — telling
    them off for it would only leave a dead cookie in a browser that tried to
    do the right thing.

    Returns whether a live session was actually closed, for logging.
    """
    if not raw_token:
        return False
    session_row = await crud_auth_session.get_by_token_hash(
        db, token_hash=hash_token(raw_token)
    )
    if session_row is None or session_row.revoked_at is not None:
        return False
    _ = await crud_auth_session.revoke(db, db_obj=session_row)
    return True


async def revoke_all_sessions(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    except_session_id: uuid.UUID | None = None,
) -> int:
    """Sign a user out of every device, optionally sparing one.

    A thin pass-through to CRUD, kept so the flows in ``service.py`` never
    reach across into the persistence layer for a decision that is theirs:
    *which* sessions survive a password change is policy.
    """
    return await crud_auth_session.revoke_all_for_user(
        db, user_id=user_id, except_session_id=except_session_id
    )


# ── Email-borne tokens ────────────────────────────────────────────


async def issue_user_token(
    db: AsyncSession, *, user_id: uuid.UUID, purpose: UserTokenPurpose
) -> str:
    """Mint a verification or reset token and return the raw value to mail out.

    Outstanding tokens of the same purpose are left alone. A "resend" must not
    break the mail already sitting in the recipient's inbox — the usual reason
    for one is that the first message went to spam and is being hunted for
    rather than that it never arrived. They are burned when a flow *succeeds*
    instead; see ``crud.user_token.consume_outstanding``.
    """
    raw_token = generate_token()
    _ = await crud_user_token.create(
        db,
        obj_in=UserTokenCreate(
            user_id=user_id,
            purpose=purpose,
            token_hash=hash_token(raw_token),
            expires_at=_user_token_expiry(purpose),
        ),
    )
    return raw_token


async def consume_user_token(
    db: AsyncSession, *, raw_token: str, purpose: UserTokenPurpose
) -> UserToken:
    """Validate a link's secret, mark it spent, and return the row.

    The purpose check is a real gate, not bookkeeping: without it a
    verification link — which is mailed to an address that has not yet proven
    it belongs to anybody — would be redeemable as a password reset.

    All three refusals carry the codes from the migration spec's fixed list
    rather than a fourth, unlisted one for "already used"; the sentence
    distinguishes that case for the person reading it, and inventing a code the
    frontend's ``errorCodes`` namespace has no entry for would render as a raw
    string on screen.
    """
    token_row = await crud_user_token.get_by_token_hash(
        db, token_hash=hash_token(raw_token)
    )
    if token_row is None or token_row.purpose != purpose:
        raise_problem(
            400,
            code="auth.invalid_token",
            detail="This link is not valid. Please request a new one.",
        )
    if token_row.consumed_at is not None:
        raise_problem(
            400,
            code="auth.invalid_token",
            detail="This link has already been used. Please request a new one.",
        )
    if token_row.expires_at <= _now():
        raise_problem(
            400,
            code="auth.token_expired",
            detail="This link has expired. Please request a new one.",
        )
    return await crud_user_token.consume(db, db_obj=token_row)
