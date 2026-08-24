"""The two endpoints behind the "check out a test event" button.

Written against HTTP rather than against ``logic.sandbox``, for the same reason
``test_auth.py`` is: in this corner of the application the transport *is* half
the behaviour. The demo is handed out as an ordinary session — an access token
in the body and a rotating refresh token in an httpOnly cookie — and the cookie
is where the expensive mistake lives.

``REFRESH_COOKIE_PATH`` is ``/api/v1/auth``. A sandbox endpoint that set its
cookie at any other path would look perfect in every test that only reads the
response body, and would then kill the demo at the first fifteen-minute token
renewal: the browser simply would not send a cookie scoped elsewhere, the
refresh would 401, and the visitor would be thrown back to the landing page
several minutes after they stopped watching, with nothing in any log to explain
it. ``test_survives_a_refresh_round_trip`` is the test that catches that, and it
catches it because httpx's cookie jar enforces cookie paths exactly as a
browser does.

Two mechanics are worth knowing before reading further:

* **The rate limiter is not a ceiling here.** ``RateLimiter.check`` returns
  immediately while ``settings.TESTING`` is true, which it is for the whole
  suite. The ceiling that can be tested — and the only one that holds across
  worker processes in production — is ``SANDBOX_MAX_ACTIVE``, counted in SQL.
* **The organiser variant seeds two extra rows**, a pending invitation and a
  pending join request, and the applicant behind the latter is itself a guest
  account. ``seed.py::_seed_pending_decisions`` flushes it before the rows that
  reference it: neither ``EventJoinRequest`` nor ``EventMembership`` declares an
  ORM relationship to ``User``, so SQLAlchemy would otherwise order those
  INSERTs by mapper sort key and put the child first.
"""

import datetime as dt
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.core.config import settings
from app.core.rate_limit import sandbox_limiter
from app.models.event import Event
from app.models.event_membership import EventMembership
from app.models.user import User
from tests.fixtures.auth import AuthHeadersFactory
from tests.fixtures.sandbox import SandboxSetup
from tests.fixtures.users import TEST_USER_PASSWORD

AUTH = f"{settings.API_V1_STR}/auth"


@pytest.fixture(autouse=True)
def fresh_rate_limit_window() -> None:
    """Start every test here with an empty per-IP counter.

    ``RateLimiter.check`` short-circuits under ``TESTING``, so today this
    resets a counter that was never incremented. It is here because the counter
    is module-level and shared: were that flag ever false, the third demo in
    this file would 429 and every test after it would fail for a reason
    unrelated to what it asserts.
    """
    sandbox_limiter.reset()


async def _start_demo(
    client: AsyncClient, *, role: str = "helper", language: str = "en"
) -> dict[str, Any]:
    """Click the button, and insist the click worked."""
    response = await client.post(
        f"{AUTH}/sandbox", json={"role": role, "language": language}
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


def _bearer(body: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {body['access_token']}"}


async def _membership_role(
    db: AsyncSession, *, user_id: object, event_id: object
) -> str | None:
    row = (
        await db.execute(
            select(EventMembership).where(
                col(EventMembership.user_id) == user_id,
                col(EventMembership.event_id) == event_id,
            )
        )
    ).scalar_one_or_none()
    return row.role if row else None


# ── Handing the demo out ──────────────────────────────────────────


@pytest.mark.asyncio
class TestStartSandbox:
    """``POST /auth/sandbox`` — the only endpoint that writes for an anonymous caller."""

    async def test_hands_back_an_ordinary_signed_in_session(
        self, unauthenticated_client: AsyncClient
    ) -> None:
        """Test that the response is a login response with a demo bolted on.

        The shape matters as much as the contents: the client installs this
        through exactly the same code path as a real sign-in, so a body that
        differed from ``TokenResponse`` would make the demo a special rendering
        mode rather than an ordinary session.
        """
        body = await _start_demo(unauthenticated_client)

        assert body["token_type"] == "bearer"
        assert body["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        assert body["role"] == "helper"
        assert body["event_id"]
        assert body["expires_at"]
        assert "refresh_token" not in body

        user = body["user"]
        assert user["is_sandbox"] is True
        assert user["email"] is None, "a guest must have no address to mail"
        assert str(user["sub"]).startswith("sandbox|")

    async def test_opens_on_the_dashboard_rather_than_the_event_picker(
        self, unauthenticated_client: AsyncClient
    ) -> None:
        """Test that the guest's selection is already the seeded event.

        Set during creation rather than by a follow-up call, so the profile in
        this very response already carries it and the client never renders a
        picker frame on the way to the dashboard.
        """
        body = await _start_demo(unauthenticated_client)
        user = body["user"]

        assert user["selected_event_id"] == body["event_id"]
        assert user["sandbox_expires_at"] == body["expires_at"]

    async def test_the_access_token_opens_authenticated_endpoints(
        self, unauthenticated_client: AsyncClient
    ) -> None:
        """Test that the token is real, not a placeholder the client displays."""
        body = await _start_demo(unauthenticated_client)

        me = await unauthenticated_client.get(
            f"{settings.API_V1_STR}/users/me", headers=_bearer(body)
        )

        assert me.status_code == 200, me.text
        assert me.json()["id"] == body["user"]["id"]
        assert me.json()["is_sandbox"] is True

    async def test_the_refresh_cookie_is_scoped_to_the_auth_path(
        self, unauthenticated_client: AsyncClient
    ) -> None:
        """Test the cookie attributes, one by one, because each is a silent failure.

        A wrong ``Path`` kills the demo at the first renewal. A ``Domain``
        would broadcast a live session credential to every other application on
        the shared apex. A missing ``HttpOnly`` would put it within reach of any
        script on the page.
        """
        response = await unauthenticated_client.post(
            f"{AUTH}/sandbox", json={"role": "helper", "language": "en"}
        )
        assert response.status_code == 201, response.text

        raw_cookie = response.headers["set-cookie"]
        assert raw_cookie.startswith(f"{settings.REFRESH_COOKIE_NAME}=")
        assert f"Path={settings.API_V1_STR}/auth" in raw_cookie
        assert "HttpOnly" in raw_cookie
        assert "Domain=" not in raw_cookie
        assert unauthenticated_client.cookies.get(settings.REFRESH_COOKIE_NAME)

    async def test_survives_a_refresh_round_trip(
        self, unauthenticated_client: AsyncClient
    ) -> None:
        """Test that the demo's own cookie renews the demo's own access token.

        This is the regression test for the cookie-path trap described at the
        top of this file. httpx's jar applies cookie paths the way a browser
        does, so a cookie set anywhere but ``/api/v1/auth`` simply would not be
        attached to this request and the refresh would 401 — fifteen minutes
        into a session, in production, with no error to trace it back to.
        """
        body = await _start_demo(unauthenticated_client)
        first_token = body["access_token"]

        refreshed = await unauthenticated_client.post(f"{AUTH}/refresh")

        assert refreshed.status_code == 200, refreshed.text
        assert refreshed.json()["access_token"]
        assert refreshed.json()["access_token"] != first_token

        # And the rotated token still belongs to the guest.
        me = await unauthenticated_client.get(
            f"{settings.API_V1_STR}/users/me",
            headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"},
        )
        assert me.status_code == 200, me.text
        assert me.json()["is_sandbox"] is True

    async def test_helper_joins_the_event_as_a_member(
        self, unauthenticated_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that the helper track gets the volunteer half of the app.

        ``member`` is what hides every management screen behind the router's
        ``requiresEventManager`` guard, so the role recorded here is the whole
        configuration of which tour the visitor is about to see.
        """
        body = await _start_demo(unauthenticated_client, role="helper")

        role = await _membership_role(
            db_session,
            user_id=body["user"]["id"],
            event_id=body["event_id"],
        )
        assert role == "member"

    async def test_manager_owns_the_event(
        self, unauthenticated_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that the organiser track owns its event and can reach its screens."""
        body = await _start_demo(unauthenticated_client, role="manager")

        assert body["role"] == "manager"
        role = await _membership_role(
            db_session,
            user_id=body["user"]["id"],
            event_id=body["event_id"],
        )
        assert role == "owner"

    async def test_defaults_to_the_helper_track_in_english(
        self, unauthenticated_client: AsyncClient
    ) -> None:
        """Test that an empty body is a valid request, not a 422.

        The landing page posts ``{}`` from the plain button; the role and
        language pickers are the elaborated path, not the only one.
        """
        response = await unauthenticated_client.post(f"{AUTH}/sandbox", json={})

        assert response.status_code == 201, response.text
        assert response.json()["role"] == "helper"
        assert response.json()["user"]["preferred_language"] == "en"

    async def test_seeds_the_demo_in_the_language_that_was_clicked(
        self, unauthenticated_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that a German landing page does not open an English demo."""
        body = await _start_demo(unauthenticated_client, language="de")

        assert body["user"]["preferred_language"] == "de"
        assert body["user"]["name"] == "Demo-Gast"
        event = (
            await db_session.execute(
                select(Event).where(col(Event.id) == body["event_id"])
            )
        ).scalar_one()
        assert event.name == "Sommerfest am Fluss"

    async def test_rejects_a_role_the_application_does_not_have(
        self, unauthenticated_client: AsyncClient
    ) -> None:
        """Test that the role is a closed set rather than a free string."""
        response = await unauthenticated_client.post(
            f"{AUTH}/sandbox", json={"role": "superadmin", "language": "en"}
        )

        assert response.status_code == 422, response.text


# ── The gate and the ceiling ──────────────────────────────────────


@pytest.mark.asyncio
class TestSandboxLimits:
    """The three fences in front of the only anonymous write in the application."""

    async def test_a_deployment_with_the_demo_switched_off_answers_404(
        self, unauthenticated_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that switching the feature off makes the endpoint *not exist*.

        404 rather than 403 deliberately: an installation that does not want
        anonymous writes should not advertise that it could have had them. The
        frontend hides the button on the same signal, so this is the belt to
        that braces.
        """
        monkeypatch.setattr(settings, "SANDBOX_ENABLED", False)

        response = await unauthenticated_client.post(f"{AUTH}/sandbox", json={})

        assert response.status_code == 404, response.text
        assert response.json()["code"] == "sandbox.disabled"

    async def test_writes_nothing_when_the_demo_is_switched_off(
        self,
        unauthenticated_client: AsyncClient,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that the gate is checked before the first row is written.

        The order in ``create_sandbox`` is gate, sweep, ceiling, *then* write.
        A gate checked after the guest account was minted would leave an
        orphaned account per refused click.
        """
        monkeypatch.setattr(settings, "SANDBOX_ENABLED", False)

        await unauthenticated_client.post(f"{AUTH}/sandbox", json={})

        guests = await db_session.execute(
            select(func.count()).select_from(User).where(col(User.is_sandbox).is_(True))
        )
        assert guests.scalar_one() == 0

    async def test_a_full_deployment_answers_503_with_a_retry_after(
        self, unauthenticated_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test the hard ceiling, counted in SQL against live rows.

        This is the fence that actually holds. The rate limiter's counters live
        in one worker process and it returns immediately under ``TESTING``, so
        it can neither be tested here nor relied on in production — which is
        why the ceiling exists as a database count in the first place.
        """
        monkeypatch.setattr(settings, "SANDBOX_MAX_ACTIVE", 1)
        await _start_demo(unauthenticated_client)

        response = await unauthenticated_client.post(f"{AUTH}/sandbox", json={})

        assert response.status_code == 503, response.text
        assert response.json()["code"] == "sandbox.capacity_reached"
        assert response.headers["Retry-After"] == "300"

    async def test_an_expired_demo_frees_its_slot(
        self,
        unauthenticated_client: AsyncClient,
        db_session: AsyncSession,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that the sweep runs before the ceiling is counted.

        That order is what makes the feature self-cleaning without a
        scheduler: the only way to accumulate demos is to keep creating them,
        and creating one is exactly when the old ones are collected. Counted
        first, a deployment would wedge at its ceiling until someone noticed.
        """
        monkeypatch.setattr(settings, "SANDBOX_MAX_ACTIVE", 1)
        first = await _start_demo(unauthenticated_client)
        stale = (
            await db_session.execute(
                select(Event).where(col(Event.id) == first["event_id"])
            )
        ).scalar_one()
        stale.sandbox_expires_at = dt.datetime.now(dt.timezone.utc).replace(
            tzinfo=None
        ) - dt.timedelta(minutes=1)
        db_session.add(stale)
        await db_session.flush()

        second = await _start_demo(unauthenticated_client)

        assert second["event_id"] != first["event_id"]
        survivors = await db_session.execute(
            select(col(Event.id)).where(col(Event.is_sandbox).is_(True))
        )
        assert [str(row) for row in survivors.scalars()] == [str(second["event_id"])]


# ── Taking it away ────────────────────────────────────────────────


@pytest.mark.asyncio
class TestExitSandbox:
    """``DELETE /auth/sandbox`` — for the visitor who is done and wants it gone."""

    async def test_deletes_the_whole_demo(
        self, unauthenticated_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that leaving takes the event, the tasks and every guest with it."""
        body = await _start_demo(unauthenticated_client)

        response = await unauthenticated_client.request(
            "DELETE", f"{AUTH}/sandbox", headers=_bearer(body)
        )

        assert response.status_code == 204, response.text
        events = await db_session.execute(
            select(func.count())
            .select_from(Event)
            .where(col(Event.id) == body["event_id"])
        )
        assert events.scalar_one() == 0
        guests = await db_session.execute(
            select(func.count()).select_from(User).where(col(User.is_sandbox).is_(True))
        )
        assert guests.scalar_one() == 0

    async def test_clears_the_refresh_cookie(
        self, unauthenticated_client: AsyncClient
    ) -> None:
        """Test that the browser is not left holding a credential for a dead account.

        Every attribute of the clearing ``Set-Cookie`` has to match the one
        that set it, path included. A mismatch creates a *second*, empty cookie
        and leaves the original in place — which reads as "leaving the demo
        does nothing" and is close to invisible from the server.
        """
        body = await _start_demo(unauthenticated_client)
        assert unauthenticated_client.cookies.get(settings.REFRESH_COOKIE_NAME)

        response = await unauthenticated_client.request(
            "DELETE", f"{AUTH}/sandbox", headers=_bearer(body)
        )

        assert response.status_code == 204, response.text
        assert f"Path={settings.API_V1_STR}/auth" in response.headers["set-cookie"]
        assert not unauthenticated_client.cookies.get(settings.REFRESH_COOKIE_NAME)

    async def test_refuses_a_real_account(
        self,
        unauthenticated_client: AsyncClient,
        auth_headers: AuthHeadersFactory,
        test_user: User,
        test_event: Event,
    ) -> None:
        """Test that a signed-in person cannot delete their own event through here.

        This endpoint hard-deletes an event *and the accounts of its members*.
        Reachable for anything that matters, it would be the most destructive
        route in the application.
        """
        response = await unauthenticated_client.request(
            "DELETE", f"{AUTH}/sandbox", headers=auth_headers(test_user)
        )

        assert response.status_code == 403, response.text
        assert response.json()["code"] == "sandbox.forbidden"

    async def test_takes_the_guest_session_with_it(
        self, unauthenticated_client: AsyncClient
    ) -> None:
        """Test that the guest's access token stops working immediately.

        Sessions are deleted explicitly rather than left to the account's
        cascade, so a guest whose demo is purged mid-request stops being
        authenticated now rather than at the end of their fifteen-minute token.
        """
        body = await _start_demo(unauthenticated_client)
        await unauthenticated_client.request(
            "DELETE", f"{AUTH}/sandbox", headers=_bearer(body)
        )

        me = await unauthenticated_client.get(
            f"{settings.API_V1_STR}/users/me", headers=_bearer(body)
        )

        assert me.status_code == 401, me.text


# ── What a guest may not do to their account ──────────────────────


@pytest.mark.asyncio
class TestGuestAccountSettings:
    """The account screens a guest must be turned away from, with a code to show.

    Both refusals carry ``sandbox.not_available`` so the frontend can say "not
    part of the demo" rather than surfacing the generic error underneath, which
    in one case sends the visitor into a loop: a guest has no password, the
    generic answer is "use the reset link", and the reset flow answers 202 and
    mails nothing because the account has no address.
    """

    async def test_a_guest_cannot_change_a_password_they_do_not_have(
        self, unauthenticated_client: AsyncClient
    ) -> None:
        """Test that change-password is refused with the demo's own code."""
        body = await _start_demo(unauthenticated_client)

        response = await unauthenticated_client.post(
            f"{AUTH}/change-password",
            json={
                "current_password": TEST_USER_PASSWORD,
                "new_password": "a-completely-different-password",
            },
            headers=_bearer(body),
        )

        assert response.status_code == 403, response.text
        assert response.json()["code"] == "sandbox.not_available"

    async def test_a_guest_cannot_ask_for_a_verification_mail(
        self, unauthenticated_client: AsyncClient
    ) -> None:
        """Test that resend-verification is refused rather than quietly accepted.

        It would answer a flat 202 without this — the endpoint's normal reply
        when there is nothing to send — and the demo would show a "check your
        inbox" toast for an account that has no inbox.
        """
        body = await _start_demo(unauthenticated_client)

        response = await unauthenticated_client.post(
            f"{AUTH}/resend-verification", headers=_bearer(body)
        )

        assert response.status_code == 403, response.text
        assert response.json()["code"] == "sandbox.not_available"

    async def test_a_real_account_still_reaches_both(
        self,
        unauthenticated_client: AsyncClient,
        auth_headers: AuthHeadersFactory,
        test_user: User,
    ) -> None:
        """Test that the guard tests ``is_sandbox`` and not merely "is signed in".

        Without this, a guard broadened to every caller would look identical in
        the two tests above while having locked the account settings for
        everybody.
        """
        response = await unauthenticated_client.post(
            f"{AUTH}/resend-verification", headers=auth_headers(test_user)
        )

        assert response.status_code == 202, response.text


# ── The fixture the rest of the suite leans on ────────────────────


@pytest.mark.asyncio
class TestSandboxFixture:
    """``tests/fixtures/sandbox.py`` mints demos the same way the route does.

    Worth one assertion of its own: three test files build their sandboxes
    through that factory rather than through HTTP, and a factory that drifted
    from the endpoint would make all of them quietly test something else.
    """

    async def test_matches_what_the_endpoint_hands_out(
        self, db_session: AsyncSession, test_sandbox: SandboxSetup
    ) -> None:
        """Test that the fixture produces a guest, an event and a live session."""
        assert test_sandbox.guest.is_sandbox is True
        assert test_sandbox.guest.subject.startswith("sandbox|")
        assert test_sandbox.guest.selected_event_id == test_sandbox.event.id
        assert test_sandbox.event.is_sandbox is True
        assert test_sandbox.event.sandbox_expires_at is not None
        assert test_sandbox.session.refresh_token
        assert (
            await _membership_role(
                db_session,
                user_id=test_sandbox.guest.id,
                event_id=test_sandbox.event.id,
            )
            == "member"
        )
