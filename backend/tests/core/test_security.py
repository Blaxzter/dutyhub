# pyright: reportPrivateUsage=false
"""Tests for the cryptographic primitives in app.core.security.

The bcrypt cases are written against bcrypt 5.0's *raising* behaviour: it no
longer truncates a >72-byte password and it no longer returns False for a
malformed hash. Both of those turn into a 500 on a login attempt if the
wrappers here stop absorbing them, so each has its own test.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
import pytest

from app.core import security
from app.core.config import settings
from app.core.security import (
    ACCESS_TOKEN_TYPE,
    ALGORITHM,
    MAX_PASSWORD_BYTES,
    AccessClaims,
    AuthTokenError,
    create_access_token,
    decode_access_token,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)


def _encode(payload: dict[str, Any], *, key: str | None = None) -> str:
    """Sign an arbitrary payload the way a legitimate token would be signed."""
    return jwt.encode(payload, key or settings.SECRET_KEY, algorithm=ALGORITHM)


class TestHashPassword:
    def test_that_the_result_is_a_bcrypt_hash(self) -> None:
        """Test that hashing produces a modular-crypt bcrypt string."""
        hashed = hash_password("correct horse battery staple")
        assert hashed.startswith("$2b$")

    def test_that_the_same_password_hashes_differently_each_time(self) -> None:
        """Test that every hash gets a fresh salt."""
        assert hash_password("hunter2hunter2") != hash_password("hunter2hunter2")

    def test_that_the_hash_verifies(self) -> None:
        """Test that a produced hash is accepted by bcrypt itself."""
        hashed = hash_password("hunter2hunter2")
        assert bcrypt.checkpw(b"hunter2hunter2", hashed.encode("utf-8"))

    def test_that_exactly_72_bytes_is_allowed(self) -> None:
        """Test that the boundary value is accepted rather than rejected."""
        password = "a" * MAX_PASSWORD_BYTES
        assert verify_password(password, hash_password(password))

    def test_that_over_72_bytes_raises(self) -> None:
        """Test that an over-long password fails loudly instead of reaching bcrypt."""
        with pytest.raises(ValueError, match="72 bytes"):
            _ = hash_password("a" * (MAX_PASSWORD_BYTES + 1))

    def test_that_the_limit_is_counted_in_bytes_not_characters(self) -> None:
        """Test that a 40-character German password is rejected at 80 bytes."""
        password = "ä" * 40
        assert len(password) < MAX_PASSWORD_BYTES
        assert len(password.encode("utf-8")) > MAX_PASSWORD_BYTES
        with pytest.raises(ValueError):
            _ = hash_password(password)

    def test_that_non_ascii_passwords_round_trip(self) -> None:
        """Test that an umlauted password under the limit still verifies."""
        password = "Sträußchen-Passwort"
        assert verify_password(password, hash_password(password))


class TestVerifyPassword:
    def test_that_the_right_password_verifies(self) -> None:
        """Test that a matching password returns True."""
        assert verify_password("s3cret-phrase", hash_password("s3cret-phrase"))

    def test_that_the_wrong_password_does_not(self) -> None:
        """Test that a non-matching password returns False."""
        assert not verify_password("wrong-phrase", hash_password("s3cret-phrase"))

    def test_that_a_missing_hash_returns_false(self) -> None:
        """Test that a password-less account returns False instead of raising."""
        assert not verify_password("anything", None)

    def test_that_an_empty_hash_returns_false(self) -> None:
        """Test that an empty hash returns False rather than 'Invalid salt'."""
        assert not verify_password("anything", "")

    def test_that_a_malformed_hash_returns_false(self) -> None:
        """Test that garbage in password_hash returns False rather than raising."""
        assert not verify_password("anything", "not-a-bcrypt-hash")

    def test_that_a_truncated_hash_returns_false(self) -> None:
        """Test that a half-written hash returns False rather than raising."""
        assert not verify_password("anything", "$2b$12$short")

    def test_that_an_over_long_password_returns_false(self) -> None:
        """Test that a >72-byte candidate cannot raise out of a login attempt."""
        hashed = hash_password("s3cret-phrase")
        assert not verify_password("a" * (MAX_PASSWORD_BYTES + 1), hashed)


class TestDummyPasswordHash:
    def test_that_it_is_computed_once_and_reused(self) -> None:
        """Test that the timing-equaliser hash is cached after first use."""
        security._dummy_hash = None
        first = security._dummy_password_hash()
        assert security._dummy_password_hash() is first

    def test_that_it_is_a_usable_bcrypt_hash(self) -> None:
        """Test that the dummy hash really costs a bcrypt verification."""
        assert (
            bcrypt.checkpw(b"anything", security._dummy_password_hash().encode())
            is False
        )


class TestHashToken:
    def test_that_it_returns_a_64_character_hexdigest(self) -> None:
        """Test that the digest fits the sa.String(64) columns that store it."""
        digest = hash_token(generate_token())
        assert len(digest) == 64
        assert all(char in "0123456789abcdef" for char in digest)

    def test_that_it_is_deterministic(self) -> None:
        """Test that the same token always hashes to the same digest."""
        assert hash_token("token-value") == hash_token("token-value")

    def test_that_different_tokens_hash_differently(self) -> None:
        """Test that the digest actually discriminates between tokens."""
        assert hash_token("token-a") != hash_token("token-b")

    def test_that_it_is_plain_sha256(self) -> None:
        """Test that the digest is reproducible outside this module."""
        expected = hashlib.sha256(b"token-value").hexdigest()
        assert hash_token("token-value") == expected


class TestGenerateToken:
    def test_that_tokens_are_unique(self) -> None:
        """Test that repeated calls do not collide."""
        assert len({generate_token() for _ in range(100)}) == 100

    def test_that_tokens_are_url_safe(self) -> None:
        """Test that a token survives being put in a URL or a cookie."""
        token = generate_token()
        assert all(char.isalnum() or char in "-_" for char in token)

    def test_that_tokens_carry_at_least_32_bytes_of_entropy(self) -> None:
        """Test that the token is long enough to be unguessable."""
        assert len(generate_token()) >= 43


class TestCreateAccessToken:
    def test_that_it_reports_the_configured_lifetime(self) -> None:
        """Test that expires_in matches ACCESS_TOKEN_EXPIRE_MINUTES."""
        _, expires_in = create_access_token(
            user_id=uuid.uuid4(), session_id=uuid.uuid4()
        )
        assert expires_in == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    def test_that_the_payload_carries_the_expected_claims(self) -> None:
        """Test that sub, jti and typ are set from the arguments."""
        user_id = uuid.uuid4()
        session_id = uuid.uuid4()
        token, _ = create_access_token(user_id=user_id, session_id=session_id)
        payload: dict[str, Any] = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        assert payload["sub"] == str(user_id)
        assert payload["jti"] == str(session_id)
        assert payload["typ"] == ACCESS_TOKEN_TYPE

    def test_that_no_audience_claim_is_set(self) -> None:
        """Test that decode never needs an audience= argument."""
        token, _ = create_access_token(user_id=uuid.uuid4(), session_id=uuid.uuid4())
        payload: dict[str, Any] = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        assert "aud" not in payload

    def test_that_it_is_signed_with_hs256(self) -> None:
        """Test that the header pins the symmetric algorithm we verify with."""
        token, _ = create_access_token(user_id=uuid.uuid4(), session_id=uuid.uuid4())
        assert jwt.get_unverified_header(token)["alg"] == "HS256"

    def test_that_expiry_follows_issuance(self) -> None:
        """Test that exp sits one configured lifetime after iat."""
        token, expires_in = create_access_token(
            user_id=uuid.uuid4(), session_id=uuid.uuid4()
        )
        payload: dict[str, Any] = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        assert payload["exp"] - payload["iat"] == expires_in


class TestDecodeAccessToken:
    def test_that_a_fresh_token_round_trips(self) -> None:
        """Test that the claims come back as the ids they were minted from."""
        user_id = uuid.uuid4()
        session_id = uuid.uuid4()
        token, _ = create_access_token(user_id=user_id, session_id=session_id)
        claims = decode_access_token(token)
        assert isinstance(claims, AccessClaims)
        assert claims.user_id == user_id
        assert claims.session_id == session_id
        assert claims.token_type == ACCESS_TOKEN_TYPE

    def test_that_claim_datetimes_are_naive_utc(self) -> None:
        """Test that nothing tz-aware escapes into the naive-UTC codebase."""
        token, _ = create_access_token(user_id=uuid.uuid4(), session_id=uuid.uuid4())
        claims = decode_access_token(token)
        assert claims.issued_at.tzinfo is None
        assert claims.expires_at.tzinfo is None
        assert claims.expires_at > claims.issued_at

    def test_that_an_expired_token_is_reported_as_expired(self) -> None:
        """Test that expiry gets its own code, not the generic invalid one."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        token = _encode(
            {
                "sub": str(uuid.uuid4()),
                "jti": str(uuid.uuid4()),
                "typ": ACCESS_TOKEN_TYPE,
                "iat": int((past - timedelta(minutes=15)).timestamp()),
                "exp": int(past.timestamp()),
            }
        )
        with pytest.raises(AuthTokenError) as exc_info:
            _ = decode_access_token(token)
        assert exc_info.value.code == "auth.token_expired"

    def test_that_a_token_signed_with_another_key_is_rejected(self) -> None:
        """Test that a forged signature does not authenticate anyone."""
        token = _encode(
            {
                "sub": str(uuid.uuid4()),
                "jti": str(uuid.uuid4()),
                "typ": ACCESS_TOKEN_TYPE,
                "exp": int(
                    (datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()
                ),
            },
            key="a-different-signing-key",
        )
        with pytest.raises(AuthTokenError) as exc_info:
            _ = decode_access_token(token)
        assert exc_info.value.code == "auth.invalid_token"

    def test_that_garbage_is_rejected(self) -> None:
        """Test that a non-JWT string raises AuthTokenError, not a jwt error."""
        with pytest.raises(AuthTokenError):
            _ = decode_access_token("not.a.token")

    def test_that_an_unsigned_token_is_rejected(self) -> None:
        """Test that alg=none cannot talk the decoder out of verifying."""
        token = jwt.encode(
            {"sub": str(uuid.uuid4()), "typ": ACCESS_TOKEN_TYPE},
            key="",
            algorithm="none",
        )
        with pytest.raises(AuthTokenError):
            _ = decode_access_token(token)

    def test_that_another_token_type_is_rejected(self) -> None:
        """Test that only typ=access is accepted as a bearer credential."""
        token = _encode(
            {
                "sub": str(uuid.uuid4()),
                "jti": str(uuid.uuid4()),
                "typ": "refresh",
                "exp": int(
                    (datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()
                ),
            }
        )
        with pytest.raises(AuthTokenError, match="not an access token"):
            _ = decode_access_token(token)

    def test_that_a_missing_subject_is_rejected(self) -> None:
        """Test that a token with no sub cannot resolve to a user."""
        token = _encode({"jti": str(uuid.uuid4()), "typ": ACCESS_TOKEN_TYPE})
        with pytest.raises(AuthTokenError, match="missing required claims"):
            _ = decode_access_token(token)

    def test_that_a_missing_session_id_is_rejected(self) -> None:
        """Test that a token with no jti cannot be tied to a session."""
        token = _encode({"sub": str(uuid.uuid4()), "typ": ACCESS_TOKEN_TYPE})
        with pytest.raises(AuthTokenError, match="missing required claims"):
            _ = decode_access_token(token)

    def test_that_a_non_uuid_subject_is_rejected(self) -> None:
        """Test that a sub we cannot parse is refused, not passed on as text."""
        token = _encode(
            {"sub": "not-a-uuid", "jti": str(uuid.uuid4()), "typ": ACCESS_TOKEN_TYPE}
        )
        with pytest.raises(AuthTokenError, match="not valid"):
            _ = decode_access_token(token)

    def test_that_a_numeric_subject_is_rejected(self) -> None:
        """Test that a non-string sub is refused rather than coerced.

        PyJWT 2.13 rejects this one itself (``verify_sub`` defaults to true), so
        it never reaches the claim parsing below — assert the outcome, not which
        layer produced it.
        """
        token = _encode(
            {"sub": 12345, "jti": str(uuid.uuid4()), "typ": ACCESS_TOKEN_TYPE}
        )
        with pytest.raises(AuthTokenError, match="not valid"):
            _ = decode_access_token(token)

    def test_that_absent_timestamps_fail_closed(self) -> None:
        """Test that a token with no iat/exp reads as already expired."""
        token = _encode(
            {
                "sub": str(uuid.uuid4()),
                "jti": str(uuid.uuid4()),
                "typ": ACCESS_TOKEN_TYPE,
            }
        )
        before = datetime.now(timezone.utc).replace(tzinfo=None)
        claims = decode_access_token(token)
        assert claims.expires_at >= before
        assert claims.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None)


class TestAuthTokenError:
    def test_that_the_default_code_is_invalid_token(self) -> None:
        """Test that callers can map any raise site to a problem code."""
        assert AuthTokenError("nope").code == "auth.invalid_token"

    def test_that_the_message_is_the_detail(self) -> None:
        """Test that str(exc) is a sentence fit to show a user."""
        assert str(AuthTokenError("Sign in again.")) == "Sign in again."
