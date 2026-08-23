"""Fixtures for the hand-rolled authentication stack.

This file used to hold four dicts of fake claims from a remote issuer. Nothing
mints tokens remotely any more, so what a test needs is not a claims dict but a
*real* token: signed with ``settings.SECRET_KEY``, carrying the ``sub``/``jti``/
``typ`` triple ``app.core.security.decode_access_token`` insists on, and
therefore accepted by exactly the same code path a browser's token would take.

The factories below are deliberately thin wrappers around
``create_access_token`` rather than hand-rolled ``jwt.encode`` calls. A test that
builds its own payload asserts against a token shape that only that test
believes in; if the claim names ever change, such a test keeps passing while
production breaks. The two places that *do* encode by hand
(``make_expired_access_token`` and ``make_tampered_access_token``) exist because
they must produce something the real minter cannot.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

import jwt
import pytest

from app.core.config import settings
from app.core.security import ACCESS_TOKEN_TYPE, ALGORITHM, create_access_token
from app.models.user import User


class AccessTokenFactory(Protocol):
    """Mints an access token for a user, optionally pinned to a session id."""

    def __call__(self, user: User, *, session_id: uuid.UUID | None = None) -> str: ...


class AuthHeadersFactory(Protocol):
    """Builds the ``Authorization`` header a signed-in client would send."""

    def __call__(
        self, user: User, *, session_id: uuid.UUID | None = None
    ) -> dict[str, str]: ...


class RawTokenFactory(Protocol):
    """Mints a token that ``decode_access_token`` must refuse."""

    def __call__(self, user: User) -> str: ...


@pytest.fixture
def make_access_token() -> AccessTokenFactory:
    """Return a factory for valid access tokens.

    ``session_id`` defaults to a fresh UUID. Pass a real ``auth_sessions.id``
    only where the *session* matters — "sign out my other devices" spares the
    session named by ``jti``, and a test of that behaviour is meaningless with
    an invented one. Everything else can take the default: nothing in the
    request path looks the session up, by design, which is what makes an access
    token verifiable without a database round-trip.
    """

    def _make(user: User, *, session_id: uuid.UUID | None = None) -> str:
        token, _ = create_access_token(
            user_id=user.id, session_id=session_id or uuid.uuid4()
        )
        return token

    return _make


@pytest.fixture
def auth_headers(make_access_token: AccessTokenFactory) -> AuthHeadersFactory:
    """Return a factory for ``Authorization: Bearer …`` headers.

    The convenience that matters is not saving a format string; it is that a
    route test written against these headers exercises the real dependency
    chain — ``HTTPBearer`` -> ``decode_access_token`` -> primary-key lookup —
    instead of the ``CurrentUser`` override the ``app`` fixture installs. Pair
    it with ``unauthenticated_client``.
    """

    def _headers(user: User, *, session_id: uuid.UUID | None = None) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {make_access_token(user, session_id=session_id)}"
        }

    return _headers


def _encode(payload: dict[str, Any], *, key: str) -> str:
    return jwt.encode(payload, key, algorithm=ALGORITHM)


@pytest.fixture
def make_expired_access_token() -> RawTokenFactory:
    """Return a factory for correctly signed tokens whose ``exp`` has passed.

    Signed with the real key on purpose: the point is to prove that expiry
    alone is refused — with ``auth.token_expired`` rather than the generic
    ``auth.invalid_token``, since the client's reaction differs (refresh and
    retry, versus sign in again).
    """

    def _make(user: User) -> str:
        issued = datetime.now(timezone.utc) - timedelta(hours=2)
        expired = issued + timedelta(minutes=15)
        return _encode(
            {
                "sub": str(user.id),
                "jti": str(uuid.uuid4()),
                "typ": ACCESS_TOKEN_TYPE,
                "iat": int(issued.timestamp()),
                "exp": int(expired.timestamp()),
            },
            key=settings.SECRET_KEY,
        )

    return _make


@pytest.fixture
def make_tampered_access_token() -> RawTokenFactory:
    """Return a factory for well-formed tokens signed with the wrong key.

    This is the forgery case: every claim is exactly what the application would
    have written, and the only thing wrong is the signature. It must fail the
    same flat way as garbage does.
    """

    def _make(user: User) -> str:
        now = datetime.now(timezone.utc)
        return _encode(
            {
                "sub": str(user.id),
                "jti": str(uuid.uuid4()),
                "typ": ACCESS_TOKEN_TYPE,
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(minutes=15)).timestamp()),
            },
            key="not-the-signing-key-this-application-uses",
        )

    return _make
