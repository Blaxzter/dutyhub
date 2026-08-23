"""Cryptographic primitives for local, database-backed authentication.

Three unrelated jobs live here because they share one property: every one of
them is a place where a subtle mistake is invisible until it is exploited.

* **Passwords** — bcrypt, salted per hash, verified in constant time by the
  library. The only knobs are the work factor (``bcrypt.gensalt()`` defaults to
  12 rounds) and the 72-byte input ceiling that bcrypt 5.0 turned from silent
  truncation into a hard ``ValueError``.
* **Opaque tokens** — refresh tokens and the email-borne verify/reset tokens.
  They are generated here and stored *hashed*, so a leaked database dump does
  not hand out live sessions. SHA-256 is deliberate and sufficient: unlike a
  password these values already carry 256 bits of entropy, so there is nothing
  for an attacker to brute-force and no reason to pay bcrypt's cost per refresh.
* **Access tokens** — short-lived HS256 JWTs signed with ``settings.SECRET_KEY``.
  Verification is local, which is the whole point of the migration away from a
  remote issuer: no network round-trip, no JWKS cache, no outage. Give that key
  at least 32 bytes (``openssl rand -hex 32``); below that PyJWT emits an
  ``InsecureKeyLengthWarning`` on every encode and decode, which is exactly what
  the placeholder ``"changethis"`` triggers locally.

Note that ``hash_password`` and ``verify_password`` are *synchronous and slow by
design* — roughly a quarter of a second each. Called straight from an ``async``
route they block that worker's event loop for the duration. That is accepted
here (login and registration are rare, and the process runs with
``--workers 4``); if a future code path needs to hash in bulk, push it through
``starlette.concurrency.run_in_threadpool`` rather than lowering the work factor.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Final

import bcrypt
import jwt

from app.core.config import settings

# bcrypt hashes at most 72 bytes of input and, since 5.0, raises rather than
# quietly truncating. Measure BYTES, not characters: this project ships a `de`
# locale and every umlaut costs two bytes, so "Sträußchen…" hits the ceiling
# well before 72 characters do.
MAX_PASSWORD_BYTES: Final = 72

ALGORITHM: Final = "HS256"
ACCESS_TOKEN_TYPE: Final = "access"

# secrets.token_urlsafe(32) is the house standard for opaque tokens (see
# crud/calendar_feed.py and crud/event_invitation.py) — 32 random bytes
# rendered as ~43 URL-safe characters.
TOKEN_ENTROPY_BYTES: Final = 32

# sha256 hexdigests are exactly 64 characters, which is why both token tables
# declare `sa.String(64)`.
TOKEN_HASH_LENGTH: Final = 64


class AuthTokenError(Exception):
    """Raised when a token cannot be turned into claims we are willing to trust.

    ``code`` is the ``auth.*`` problem code the caller should surface, so a
    route or dependency can translate the failure without re-inspecting the
    exception type::

        except AuthTokenError as exc:
            raise_problem(401, code=exc.code, detail=str(exc))

    The message is a user-facing sentence for exactly that reason.
    """

    def __init__(self, message: str, *, code: str = "auth.invalid_token") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class AccessClaims:
    """The validated payload of an access token.

    ``session_id`` is the ``auth_sessions`` row the token was minted for (the
    JWT ``jti``). Carrying it means a caller can tie a stateless access token
    back to a revocable session without a second lookup path.

    ``issued_at`` and ``expires_at`` are **naive UTC**, matching every other
    datetime in this codebase — the JWT itself stores them as epoch seconds, so
    this is the one conversion point where the convention could slip.
    """

    user_id: uuid.UUID
    session_id: uuid.UUID
    token_type: str
    issued_at: datetime
    expires_at: datetime


def _utc_now() -> datetime:
    """Return the current time as a naive UTC datetime (the house convention)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# A valid bcrypt hash that no password will ever match, computed once on first
# use. Verifying against it lets the no-password path burn the same CPU as a
# real check, so an attacker cannot tell "this account has no password" (or
# "this email is unknown", if the caller feeds us a placeholder) apart from
# "wrong password" by timing the response.
_dummy_hash: str | None = None


def _dummy_password_hash() -> str:
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password(secrets.token_urlsafe(16))
    return _dummy_hash


def hash_password(password: str) -> str:
    """Hash a password with a fresh bcrypt salt.

    Raises ``ValueError`` when the password exceeds bcrypt's 72-byte input
    limit. Callers that accept user input should have rejected it long before
    this point (``app.logic.auth.passwords`` and the request schemas both
    enforce the same ceiling); this guard exists so the failure is a clear
    error at the boundary rather than bcrypt's own message surfacing as a 500.
    """
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password must be at most {MAX_PASSWORD_BYTES} bytes (got {len(encoded)})."
        )
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Check a password against a stored hash. Never raises.

    ``hashed_password`` is nullable on purpose: accounts provisioned before
    local authentication existed — and the ``demo|`` / ``test|`` accounts — have
    no password at all. bcrypt would raise ``ValueError: Invalid salt`` on such
    a value, turning every login attempt against a legacy row into a 500 instead
    of a clean 401, so every failure mode here is folded into ``False``:

    * no hash stored -> False (after a dummy verification, for timing)
    * malformed or empty hash -> False
    * password longer than bcrypt's 72-byte limit -> False, since nothing we
      ever hashed could have matched it anyway
    """
    if not hashed_password:
        _ = _checkpw(plain_password, _dummy_password_hash())
        return False
    return _checkpw(plain_password, hashed_password)


def _checkpw(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except ValueError:
        # Invalid salt, or an over-long password. Both mean "these cannot
        # match", which is what False says.
        return False


def generate_token() -> str:
    """Return a new opaque token — the raw value, shown to the user exactly once."""
    return secrets.token_urlsafe(TOKEN_ENTROPY_BYTES)


def hash_token(raw_token: str) -> str:
    """Return the sha256 hexdigest (64 chars) stored in place of a raw token.

    Lookups hash the presented token and match on the digest, so the raw value
    exists only in the client's cookie or inbox — never in the database, a
    backup, or a query log.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_access_token(
    *, user_id: uuid.UUID, session_id: uuid.UUID
) -> tuple[str, int]:
    """Mint a short-lived HS256 access token.

    Returns ``(token, expires_in_seconds)``; the second element goes straight
    into ``TokenResponse.expires_in`` so the client can schedule its refresh
    without decoding the JWT.

    Claims are deliberately minimal — ``sub`` (the user id), ``jti`` (the
    ``auth_sessions`` row), ``typ``, ``iat`` and ``exp``. There is **no** ``aud``
    claim: setting one would oblige every ``jwt.decode`` call in the codebase to
    pass a matching ``audience=`` argument or raise, for no benefit in a system
    with exactly one issuer and one audience. Nothing role-shaped is embedded
    either, so a permission change takes effect on the next request rather than
    when the token happens to expire.
    """
    now = datetime.now(timezone.utc)
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    expires_at = now + timedelta(seconds=expires_in)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "jti": str(session_id),
        "typ": ACCESS_TOKEN_TYPE,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    return token, expires_in


def decode_access_token(token: str) -> AccessClaims:
    """Verify an access token and return its claims, or raise ``AuthTokenError``.

    ``algorithms`` is pinned explicitly: passing the list is what stops a forged
    header from talking us into ``none`` or into verifying an RS256 signature
    with our own secret as the public key.

    ``jwt.ExpiredSignatureError`` must be caught *before* ``InvalidTokenError``
    — it subclasses it, so the broad handler would otherwise swallow the one
    case worth distinguishing (an expired token means "refresh me", any other
    failure means "sign in again").
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise AuthTokenError(
            "Your session has expired. Please sign in again.",
            code="auth.token_expired",
        )
    except jwt.InvalidTokenError:
        raise AuthTokenError("The provided token is not valid.")

    token_type = payload.get("typ")
    if token_type != ACCESS_TOKEN_TYPE:
        # Refresh tokens are opaque and never reach this function, so a JWT with
        # any other `typ` is either a bug or an attempt to present the wrong
        # credential. Both deserve the same flat refusal.
        raise AuthTokenError("The provided token is not an access token.")

    return AccessClaims(
        user_id=_claim_as_uuid(payload, "sub"),
        session_id=_claim_as_uuid(payload, "jti"),
        token_type=ACCESS_TOKEN_TYPE,
        issued_at=_claim_as_datetime(payload, "iat"),
        expires_at=_claim_as_datetime(payload, "exp"),
    )


def _claim_as_uuid(payload: dict[str, Any], claim: str) -> uuid.UUID:
    value = payload.get(claim)
    if not isinstance(value, str):
        raise AuthTokenError("The provided token is missing required claims.")
    try:
        return uuid.UUID(value)
    except ValueError:
        raise AuthTokenError("The provided token is not valid.")


def _claim_as_datetime(payload: dict[str, Any], claim: str) -> datetime:
    """Convert an epoch-seconds claim to a naive UTC datetime.

    A token that PyJWT accepted always carries a numeric ``exp``; ``iat`` is
    ours to mint and equally always present. The fallback to "now" therefore
    only fires for a token this codebase did not create, and it fails closed —
    an absent ``exp`` reads as already expired rather than as valid forever.
    """
    value = payload.get(claim)
    if not isinstance(value, int | float):
        return _utc_now()
    return datetime.fromtimestamp(float(value), tz=timezone.utc).replace(tzinfo=None)
