"""Tests for the parts of ``app.logic.auth`` that a request cannot reach.

The flows themselves (register, login, refresh, reset) are covered end to end
through ``tests/api/routes/test_auth.py``, where the cookie, the status code and
the background task are as much of the behaviour as the database write is. What
is left here falls into three groups, each of which is invisible from the HTTP
side for a different reason:

* **The helpers the flows share** — ``sync_superadmin_role`` and
  ``build_user_profile``. Both are called from several places, and a regression
  in either surfaces as a deployment with no administrator, or a signed-in user
  with no navigation.
* **The password policy** — the schema layer rejects a bad password first, as a
  422 the registration form can render next to the input, so the flow layer's
  own copy of the rule is never exercised by a request. It exists for callers
  with no request behind them, which is exactly the situation in which a rule
  enforced only at the boundary quietly stops existing.
* **Branches only a race or a deletion can produce** — the concurrent-signup
  collision, and a link redeemed a moment after its account was removed. Both
  are one-line guards whose absence is a 500 in production and nothing at all
  in a test suite that cannot provoke them.
"""

import uuid
from typing import Any, cast

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import MAX_PASSWORD_BYTES, verify_password
from app.crud.user import user as crud_user
from app.logic.auth.passwords import (
    hash_new_password,
    password_policy_violation,
    validate_password_strength,
)
from app.logic.auth.service import (
    build_user_profile,
    register_user,
    reset_password,
    sync_superadmin_role,
    verify_email,
)
from app.logic.auth.tokens import issue_user_token
from app.models.event import Event
from app.models.user import User
from app.schemas.auth import RegisterRequest

# 36 umlauts is 72 bytes and 36 characters; 40 is 80 bytes and 40 characters.
# The pair is what tells a byte-counting rule from a character-counting one.
UMLAUTS_AT_LIMIT = "ä" * 36
UMLAUTS_OVER_LIMIT = "ä" * 40


def _problem_code(exc: HTTPException) -> str:
    """The ``auth.*`` code carried in a ``raise_problem`` exception.

    The cast is unavoidable: Starlette declares ``HTTPException.detail`` as
    ``str``, FastAPI widens the constructor parameter to ``Any`` and serialises
    whatever it is given, and ``raise_problem`` puts the whole problem+json
    payload there. The ``isinstance`` check keeps the cast honest at runtime.
    """
    assert isinstance(exc.detail, dict), "raise_problem always builds a dict detail"
    detail = cast(dict[str, str], exc.detail)
    return detail["code"]


class TestSyncSuperadminRole:
    """``sync_superadmin_role`` — the only mechanism that mints an admin.

    On a fresh deployment nobody holds the ``admin`` role, and no route can
    grant it: the endpoints that manage roles are themselves behind
    ``CurrentSuperuser``. The first person to register or sign in with an
    address listed in ``SUPERADMIN_EMAILS`` becomes the administrator, and
    without that there is no path to the admin screens at all.

    That makes this the most privileged comparison in the application, so the
    negative cases below are the point of the class: a superstring, a lookalike
    domain suffix and a truncated domain must all fail to match. Case is the one
    difference that is deliberately *tolerated* — an operator who wrote
    "Admin@example.com" in the env file while the account holds
    "admin@example.com" previously got no role and no explanation.
    """

    def test_listed_email_gains_admin_and_is_activated(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a listed address is granted the role and reactivated."""
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", ["boss@example.com"])
        user = User(
            subject="local|boss",
            email="boss@example.com",
            name="Boss",
            roles=[],
            is_active=False,
        )

        changed = sync_superadmin_role(user)

        assert changed is True
        assert user.roles == ["admin"]
        assert user.is_active is True

    def test_match_is_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that the comparison matches ``lower(email)``, as lookups do."""
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", ["Boss@Example.com"])
        user = User(
            subject="local|boss",
            email="boss@example.com",
            name="Boss",
            roles=[],
            is_active=True,
        )

        assert sync_superadmin_role(user) is True
        assert user.roles == ["admin"]

    def test_already_admin_and_active_reports_no_change(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a no-op returns False so the caller can skip the write."""
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", ["boss@example.com"])
        user = User(
            subject="local|boss",
            email="boss@example.com",
            name="Boss",
            roles=["admin"],
            is_active=True,
        )

        assert sync_superadmin_role(user) is False
        assert user.roles.count("admin") == 1

    def test_already_admin_but_suspended_is_reactivated(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that the list outranks a moderation decision.

        Locking the only administrator out of their own installation has no
        recovery path through the UI, which is why activation rides along with
        the role rather than being left to whoever suspended them.
        """
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", ["boss@example.com"])
        user = User(
            subject="local|boss",
            email="boss@example.com",
            name="Boss",
            roles=["admin"],
            is_active=False,
        )

        assert sync_superadmin_role(user) is True
        assert user.is_active is True

    def test_existing_roles_are_preserved(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that ``admin`` is appended rather than replacing the list.

        ``roles`` is a JSONB column, so the new list has to be *assigned* for
        SQLAlchemy to notice the mutation at all — appending in place would be
        flushed as no change.
        """
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", ["boss@example.com"])
        user = User(
            subject="local|boss",
            email="boss@example.com",
            name="Boss",
            roles=["moderator"],
            is_active=True,
        )

        assert sync_superadmin_role(user) is True
        assert user.roles == ["moderator", "admin"]

    @pytest.mark.parametrize(
        ("stored_email", "reason"),
        [
            ("xadmin@example.com", "an address containing the listed one"),
            ("admin@example.com.evil.com", "a lookalike domain suffix"),
            ("admin@example.co", "a truncated domain"),
            ("someone@example.com", "an unrelated address"),
        ],
    )
    def test_lookalike_emails_do_not_escalate(
        self,
        monkeypatch: pytest.MonkeyPatch,
        stored_email: str,
        reason: str,
    ) -> None:
        """Test that only an exact (case-folded) match may escalate."""
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", ["admin@example.com"])
        user = User(
            subject=f"local|{stored_email}",
            email=stored_email,
            name="Impostor",
            roles=[],
            is_active=False,
        )

        assert sync_superadmin_role(user) is False
        assert user.roles == [], f"{reason} must not gain the admin role"
        assert user.is_active is False, f"{reason} must not be activated"

    def test_user_without_email_is_never_escalated(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a NULL address short-circuits before the membership check.

        ``email`` is nullable — demo accounts have none — and ``None`` must not
        be coerced into a comparable value on the way past.
        """
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", ["admin@example.com"])
        user = User(subject="demo|noemail", email=None, name="No Email", roles=[])

        assert sync_superadmin_role(user) is False
        assert user.roles == []

    def test_removal_from_the_list_is_not_mirrored(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that taking an address off the list does not strip the role.

        Roles are also granted by hand through the admin screens, so a
        reconciliation in this direction would silently undo them. Demotion is a
        deliberate action in the user-management UI, not a side effect of an env
        file edit.
        """
        monkeypatch.setattr(settings, "SUPERADMIN_EMAILS", [])
        user = User(
            subject="local|former",
            email="former@example.com",
            name="Former",
            roles=["admin"],
            is_active=True,
        )

        assert sync_superadmin_role(user) is False
        assert user.roles == ["admin"]


@pytest.mark.asyncio
class TestBuildUserProfile:
    """``build_user_profile`` — the row plus the caller's role in each event.

    ``event_roles`` is not a column. The frontend renders its entire navigation
    from that map, so a profile that omits it shows a signed-in user with no
    events — which reads as data loss rather than as a serialisation bug.
    """

    async def test_includes_the_users_event_roles(
        self, db_session: AsyncSession, test_event_admin_user: User, test_event: Event
    ) -> None:
        """Test that a membership shows up keyed by event id."""
        profile = await build_user_profile(db_session, test_event_admin_user)

        assert profile.event_roles[str(test_event.id)] == "admin"

    async def test_event_roles_is_empty_for_an_outsider(
        self, db_session: AsyncSession, test_outsider_user: User
    ) -> None:
        """Test that belonging to nothing serialises as ``{}``, not as an error."""
        profile = await build_user_profile(db_session, test_outsider_user)

        assert profile.event_roles == {}

    async def test_subject_is_exposed_as_sub(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that the profile still calls the identity field ``sub``.

        ``UserProfile.sub`` keeps its alias so the frontend's identity handling
        needed no change when the column was renamed. Pinning it here means a
        future tidy-up of the alias breaks a test rather than the client.
        """
        profile = await build_user_profile(db_session, test_user)

        assert profile.sub == test_user.subject


class TestPasswordPolicy:
    """The rule as the flow layer enforces it, for callers with no request.

    The same two bounds are checked in three places — the request schema, this
    module, and ``hash_password`` itself — and the triplication only looks
    redundant until one of them is missing. The schema cannot cover a caller
    that is not an HTTP request; this layer cannot produce a per-field 422; and
    the primitive can only raise ``ValueError``, which is a 500.

    Every request-shaped path is stopped by the schema before reaching here, so
    these tests are the *only* thing keeping the middle copy honest. The upper
    bound in particular is bcrypt's, it is measured in bytes, and this project
    ships a German locale — so the boundary cases below are umlauts rather than
    ASCII on purpose.
    """

    def test_a_short_password_is_reported(self) -> None:
        """Test that a password under the configured minimum is refused."""
        violation = password_policy_violation("a" * (settings.PASSWORD_MIN_LENGTH - 1))

        assert violation is not None
        assert str(settings.PASSWORD_MIN_LENGTH) in violation

    def test_a_password_at_the_minimum_is_accepted(self) -> None:
        """Test that the lower bound is inclusive."""
        assert password_policy_violation("a" * settings.PASSWORD_MIN_LENGTH) is None

    def test_length_is_measured_in_bytes(self) -> None:
        """Test that forty umlauts are too long even though forty ASCII are not.

        The two strings are the same length in characters. Only a byte-counting
        rule tells them apart, and only a byte-counting rule agrees with the
        ``ValueError`` bcrypt would otherwise raise on the second one.
        """
        assert len(UMLAUTS_OVER_LIMIT) == 40
        assert len(UMLAUTS_OVER_LIMIT.encode("utf-8")) == 80

        assert password_policy_violation("a" * 40) is None

        violation = password_policy_violation(UMLAUTS_OVER_LIMIT)
        assert violation is not None
        assert str(MAX_PASSWORD_BYTES) in violation

    def test_exactly_seventy_two_bytes_is_still_acceptable(self) -> None:
        """Test that the upper bound is inclusive too."""
        assert len(UMLAUTS_AT_LIMIT.encode("utf-8")) == MAX_PASSWORD_BYTES
        assert password_policy_violation(UMLAUTS_AT_LIMIT) is None

    def test_validation_raises_the_weak_password_problem(self) -> None:
        """Test that a violation becomes a 422 with a translatable code.

        422 rather than 400: this is a complaint about one field of the body,
        which is what every surrounding validation error is, and the frontend
        already knows how to render one next to the input it belongs to.
        """
        with pytest.raises(HTTPException) as exc_info:
            validate_password_strength("short")

        assert exc_info.value.status_code == 422
        assert _problem_code(exc_info.value) == "auth.weak_password"

    def test_validation_passes_an_acceptable_password(self) -> None:
        """Test that a good password raises nothing."""
        validate_password_strength("a-perfectly-ordinary-passphrase")

    def test_hashing_refuses_before_bcrypt_can(self) -> None:
        """Test that an over-long password is a 422, never an unhandled ValueError.

        ``hash_new_password`` is the single entry point for *setting* a
        password. Reaching for ``core.security.hash_password`` directly skips
        the policy and turns this case into a 500.
        """
        with pytest.raises(HTTPException) as exc_info:
            _ = hash_new_password(UMLAUTS_OVER_LIMIT)

        assert exc_info.value.status_code == 422
        assert _problem_code(exc_info.value) == "auth.weak_password"

    def test_hashing_produces_something_the_verifier_accepts(self) -> None:
        """Test that the hash it returns is the one ``verify_password`` checks."""
        hashed = hash_new_password("a-perfectly-ordinary-passphrase")

        assert hashed != "a-perfectly-ordinary-passphrase"
        assert verify_password("a-perfectly-ordinary-passphrase", hashed) is True
        assert verify_password("something-else-entirely", hashed) is False


@pytest.mark.asyncio
class TestRegisterUserRace:
    """Two signups for one address, arriving at the same moment.

    The uniqueness check and the INSERT are not one statement, so a
    double-clicked submit button produces two requests that both pass the check
    and then race on ``ix_users_email_lower``. The loser has to receive the same
    409 an ordinary duplicate gets: a 500 for "you already have an account" is
    both alarming and unactionable, and it is the shape of failure that only
    ever appears under load.
    """

    async def test_a_unique_violation_becomes_the_same_409(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that an IntegrityError on insert is translated, not propagated."""

        async def _collide(db: AsyncSession, *, obj_in: Any) -> User:
            _ = (db, obj_in)
            raise IntegrityError(
                "INSERT INTO users ...",
                None,
                Exception("duplicate key value violates ix_users_email_lower"),
            )

        monkeypatch.setattr(crud_user, "create", _collide)

        with pytest.raises(HTTPException) as exc_info:
            _ = await register_user(
                db_session,
                data=RegisterRequest(
                    email="racer@example.com",
                    password="a-perfectly-ordinary-passphrase",
                    name="Racer",
                ),
            )

        assert exc_info.value.status_code == 409
        assert _problem_code(exc_info.value) == "auth.email_taken"


@pytest.mark.asyncio
class TestTokenOwnerVanished:
    """A link redeemed in the instant after its account was deleted.

    ``user_tokens.user_id`` cascades, so this is a window rather than a state:
    the token row is read, and only then is its user looked up. If the account
    went away in between, both flows have to answer with the ordinary dead-link
    problem instead of dereferencing ``None`` — which would be a 500 on a route
    that anyone on the internet may call with any string.
    """

    async def test_a_reset_link_becomes_an_ordinary_dead_link(
        self,
        db_session: AsyncSession,
        test_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that resetting against a vanished account is a 400, not a crash."""
        token = await issue_user_token(
            db_session, user_id=test_user.id, purpose="reset_password"
        )

        async def _gone(db: AsyncSession, user_id: uuid.UUID) -> User | None:
            _ = (db, user_id)
            return None

        monkeypatch.setattr(crud_user, "get", _gone)

        with pytest.raises(HTTPException) as exc_info:
            _ = await reset_password(
                db_session, token=token, new_password="a-perfectly-ordinary-passphrase"
            )

        assert exc_info.value.status_code == 400
        assert _problem_code(exc_info.value) == "auth.invalid_token"

    async def test_a_verification_link_becomes_an_ordinary_dead_link(
        self,
        db_session: AsyncSession,
        test_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that verifying against a vanished account is a 400, not a crash."""
        token = await issue_user_token(
            db_session, user_id=test_user.id, purpose="verify_email"
        )

        async def _gone(db: AsyncSession, user_id: uuid.UUID) -> User | None:
            _ = (db, user_id)
            return None

        monkeypatch.setattr(crud_user, "get", _gone)

        with pytest.raises(HTTPException) as exc_info:
            _ = await verify_email(db_session, token=token)

        assert exc_info.value.status_code == 400
        assert _problem_code(exc_info.value) == "auth.invalid_token"
