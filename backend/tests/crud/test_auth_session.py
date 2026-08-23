"""Unit tests for the ``auth_sessions`` persistence layer.

The flows that use this CRUD object are covered end to end in
``tests/api/routes/test_auth.py``. What is left here is the behaviour the rows
themselves have to exhibit, and it is worth separate coverage because two of
the choices in ``app.crud.auth_session`` look like bugs until you know why they
were made:

* ``get_by_token_hash`` deliberately returns **revoked and expired** rows.
  Adding a ``revoked_at IS NULL`` filter reads as tightening security and
  silently removes it — a stolen token would become indistinguishable from one
  that never existed, and reuse detection would never fire again.
* ``revoke`` keeps the row and the *first* ``revoked_at`` it was given. When a
  session died is evidence, so a second logout must not overwrite the moment a
  theft was actually detected.

The cascade test at the bottom is a regression guard rather than a feature
test: a user FK written as ``SET NULL`` in this schema turns an ordinary
account deletion into a foreign-key violation (see
``app/models/CLAUDE.md``).
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_token, hash_token
from app.crud.auth_session import auth_session as crud_auth_session
from app.models.auth_session import AuthSession
from app.models.user import User
from app.schemas.auth import AuthSessionCreate

# Long enough to exceed the columns they are clipped to. Both values arrive
# from client-controlled headers, so "too long" is a thing that will happen.
OVERLONG_USER_AGENT = "Mozilla/5.0 " + "x" * 400
OVERLONG_IP_ADDRESS = "203.0.113.7" + "0" * 60


def _naive_utc_now() -> datetime:
    """The house datetime: UTC, with the tzinfo taken off again.

    ``expires_at`` is a naive column. Comparing it against an aware ``now()``
    raises ``TypeError``, and it would do so inside the refresh path on a live
    session rather than anywhere a test would notice.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _make_session(
    db: AsyncSession,
    *,
    user: User,
    raw_token: str | None = None,
    expires_at: datetime | None = None,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[AuthSession, str]:
    """Create one session row, returning it with the raw token that opens it."""
    token = raw_token or generate_token()
    row = await crud_auth_session.create(
        db,
        obj_in=AuthSessionCreate(
            user_id=user.id,
            refresh_token_hash=hash_token(token),
            expires_at=expires_at or _naive_utc_now() + timedelta(days=30),
            user_agent=user_agent,
            ip_address=ip_address,
        ),
    )
    return row, token


@pytest.mark.asyncio
class TestGetByTokenHash:
    """Looking a session up by the secret a client presented.

    The lookup is by digest, never by the value itself — which is the whole
    reason a leaked database dump does not hand out live sessions. And it is
    deliberately unfiltered, so that the *caller* decides what a dead row
    means: expired says "sign in again", revoked says "this may be theft".
    """

    async def test_finds_a_live_session(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that hashing the presented token finds its row."""
        created, token = await _make_session(db_session, user=test_user)

        found = await crud_auth_session.get_by_token_hash(
            db_session, token_hash=hash_token(token)
        )

        assert found is not None
        assert found.id == created.id

    async def test_stores_only_the_digest(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that the raw token never reaches the row."""
        created, token = await _make_session(db_session, user=test_user)

        assert created.refresh_token_hash != token
        assert len(created.refresh_token_hash) == 64
        assert created.refresh_token_hash == hash_token(token)

    async def test_an_unknown_digest_is_none(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that a token this server never issued matches nothing."""
        _ = await _make_session(db_session, user=test_user)

        found = await crud_auth_session.get_by_token_hash(
            db_session, token_hash=hash_token("never-issued")
        )

        assert found is None

    async def test_a_revoked_session_is_still_returned(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that revocation does not hide the row from this lookup.

        This is the single fact reuse detection is built on. If a revoked
        session answered ``None`` here, replaying a stolen cookie would look
        exactly like presenting a made-up one and the account would never be
        swept.
        """
        created, token = await _make_session(db_session, user=test_user)
        _ = await crud_auth_session.revoke(db_session, db_obj=created)

        found = await crud_auth_session.get_by_token_hash(
            db_session, token_hash=hash_token(token)
        )

        assert found is not None
        assert found.revoked_at is not None

    async def test_an_expired_session_is_still_returned(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that a lapsed session can still be told apart from a bogus one."""
        _, token = await _make_session(
            db_session,
            user=test_user,
            expires_at=_naive_utc_now() - timedelta(minutes=1),
        )

        found = await crud_auth_session.get_by_token_hash(
            db_session, token_hash=hash_token(token)
        )

        assert found is not None
        assert found.expires_at < _naive_utc_now()


@pytest.mark.asyncio
class TestListActiveForUser:
    """What the Security settings card is allowed to show.

    "Kept" and "shown" are two different questions here: revoked rows survive
    in the table for reuse detection, and an expired one is a device that
    stopped being signed in without anybody telling it so. Listing either would
    tell someone their account is signed in somewhere it is not.
    """

    async def test_lists_only_this_users_sessions(
        self, db_session: AsyncSession, test_user: User, test_outsider_user: User
    ) -> None:
        """Test that the query is scoped to one account."""
        mine, _ = await _make_session(db_session, user=test_user)
        _ = await _make_session(db_session, user=test_outsider_user)

        rows = await crud_auth_session.list_active_for_user(
            db_session, user_id=test_user.id
        )

        assert [row.id for row in rows] == [mine.id]

    async def test_excludes_revoked_sessions(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that a signed-out device drops off the list."""
        live, _ = await _make_session(db_session, user=test_user)
        revoked, _ = await _make_session(db_session, user=test_user)
        _ = await crud_auth_session.revoke(db_session, db_obj=revoked)

        rows = await crud_auth_session.list_active_for_user(
            db_session, user_id=test_user.id
        )

        assert [row.id for row in rows] == [live.id]

    async def test_excludes_expired_sessions(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that a lapsed session is not presented as a signed-in device."""
        live, _ = await _make_session(db_session, user=test_user)
        _ = await _make_session(
            db_session,
            user=test_user,
            expires_at=_naive_utc_now() - timedelta(seconds=1),
        )

        rows = await crud_auth_session.list_active_for_user(
            db_session, user_id=test_user.id
        )

        assert [row.id for row in rows] == [live.id]

    async def test_orders_by_newest_sign_in_first(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that the most recent sign-in heads the list.

        ``last_used_at`` would be the more informative sort key but is NULL
        until the first refresh, and NULLS ordering differs by dialect — so the
        stable ``created_at`` decides and the UI renders both timestamps.
        """
        older, _ = await _make_session(db_session, user=test_user)
        newer, _ = await _make_session(db_session, user=test_user)
        older.created_at = _naive_utc_now() - timedelta(days=2)
        newer.created_at = _naive_utc_now() - timedelta(minutes=5)
        db_session.add_all([older, newer])
        await db_session.flush()

        rows = await crud_auth_session.list_active_for_user(
            db_session, user_id=test_user.id
        )

        assert [row.id for row in rows] == [newer.id, older.id]

    async def test_a_user_with_no_sessions_gets_an_empty_list(
        self, db_session: AsyncSession, test_outsider_user: User
    ) -> None:
        """Test that never having signed in is an empty list, not an error."""
        rows = await crud_auth_session.list_active_for_user(
            db_session, user_id=test_outsider_user.id
        )

        assert list(rows) == []


@pytest.mark.asyncio
class TestRevoke:
    """Ending one session without losing the fact that it existed.

    Rows are stamped, never deleted. Two things depend on that: reuse detection
    needs the dead digest to keep matching something, and the timestamp is the
    only record of *when* a session was closed.
    """

    async def test_stamps_the_row_instead_of_deleting_it(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that revoking sets ``revoked_at`` and keeps the row."""
        created, _ = await _make_session(db_session, user=test_user)

        revoked = await crud_auth_session.revoke(db_session, db_obj=created)

        assert revoked.revoked_at is not None
        surviving = await db_session.execute(
            select(func.count()).select_from(AuthSession)
        )
        assert surviving.scalar_one() == 1

    async def test_is_idempotent_and_keeps_the_first_timestamp(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that a second revocation does not rewrite when the session died.

        A double-submitted logout, or a logout after a theft sweep, must not
        move the timestamp: the moment a session was closed is the evidence an
        operator has when asking whether an account was compromised.
        """
        created, _ = await _make_session(db_session, user=test_user)
        first = await crud_auth_session.revoke(db_session, db_obj=created)
        first_stamp = first.revoked_at

        second = await crud_auth_session.revoke(db_session, db_obj=created)

        assert second.revoked_at == first_stamp


@pytest.mark.asyncio
class TestRevokeAllForUser:
    """Signing an account out everywhere — with, or without, one exemption.

    Three flows share this: a password reset and reuse detection close
    *everything*, while a deliberate password change spares the session doing
    the changing. The count it returns is what the routes log, so it has to
    mean "sessions actually closed" rather than "rows looked at".
    """

    async def test_revokes_every_live_session_and_counts_them(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that all of a user's sessions are closed at once."""
        _ = await _make_session(db_session, user=test_user)
        _ = await _make_session(db_session, user=test_user)

        revoked = await crud_auth_session.revoke_all_for_user(
            db_session, user_id=test_user.id
        )

        assert revoked == 2
        remaining = await crud_auth_session.list_active_for_user(
            db_session, user_id=test_user.id
        )
        assert list(remaining) == []

    async def test_spares_the_named_session(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that ``except_session_id`` keeps the caller's own device signed in.

        This is what makes a password change survivable: being signed out of
        the tab you just typed your new password into reads as a failure rather
        than as a security measure.
        """
        keeper, _ = await _make_session(db_session, user=test_user)
        _ = await _make_session(db_session, user=test_user)

        revoked = await crud_auth_session.revoke_all_for_user(
            db_session, user_id=test_user.id, except_session_id=keeper.id
        )

        assert revoked == 1
        remaining = await crud_auth_session.list_active_for_user(
            db_session, user_id=test_user.id
        )
        assert [row.id for row in remaining] == [keeper.id]

    async def test_already_revoked_sessions_are_not_counted_again(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that a second sweep reports nothing left to do."""
        _ = await _make_session(db_session, user=test_user)
        assert (
            await crud_auth_session.revoke_all_for_user(
                db_session, user_id=test_user.id
            )
            == 1
        )

        assert (
            await crud_auth_session.revoke_all_for_user(
                db_session, user_id=test_user.id
            )
            == 0
        )

    async def test_leaves_other_accounts_alone(
        self, db_session: AsyncSession, test_user: User, test_outsider_user: User
    ) -> None:
        """Test that a sweep is scoped to one user.

        Reuse detection calls this on the strength of one presented token. An
        unscoped ``UPDATE`` here would turn one stolen cookie into a
        platform-wide sign-out.
        """
        _ = await _make_session(db_session, user=test_user)
        theirs, _ = await _make_session(db_session, user=test_outsider_user)

        _ = await crud_auth_session.revoke_all_for_user(
            db_session, user_id=test_user.id
        )

        untouched = await crud_auth_session.list_active_for_user(
            db_session, user_id=test_outsider_user.id
        )
        assert [row.id for row in untouched] == [theirs.id]


@pytest.mark.asyncio
class TestDeviceLabels:
    """The ``user_agent`` and ``ip_address`` shown against a device.

    Both are self-reported strings, stored as labels and never read as an
    authentication signal. They are *clipped* to fit their columns rather than
    validated, because a browser sending a 400-character ``User-Agent`` must
    not be unable to sign in — and a ``ValidationError`` raised while building
    an internal schema is a 500, not a 422.
    """

    async def test_an_overlong_user_agent_is_truncated_not_rejected(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that a long ``User-Agent`` is clipped to the column width."""
        created, _ = await _make_session(
            db_session, user=test_user, user_agent=OVERLONG_USER_AGENT
        )

        assert created.user_agent is not None
        assert len(created.user_agent) == 255
        assert created.user_agent == OVERLONG_USER_AGENT[:255]

    async def test_an_overlong_address_is_truncated_not_rejected(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that a nonsense forwarded address still fits its 45-char column."""
        created, _ = await _make_session(
            db_session, user=test_user, ip_address=OVERLONG_IP_ADDRESS
        )

        assert created.ip_address is not None
        assert len(created.ip_address) == 45

    async def test_both_labels_are_optional(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that a client that reports neither still gets a session."""
        created, _ = await _make_session(db_session, user=test_user)

        assert created.user_agent is None
        assert created.ip_address is None


@pytest.mark.asyncio
class TestUserDeletionCascades:
    """Deleting an account must take its sessions with it.

    ``auth_sessions.user_id`` is ``ondelete="CASCADE"`` and must stay that way.
    A ``SET NULL`` on a user FK in this schema is not merely wrong in principle
    — Postgres applies it inside the same statement as the cascade that removes
    the user's events, and the re-checked row then points at a parent that is
    already gone, so an ordinary account deletion fails with a foreign-key
    violation nowhere near the code that caused it.
    """

    async def test_deleting_the_user_deletes_their_sessions(
        self, db_session: AsyncSession, test_outsider_user: User
    ) -> None:
        """Test that no orphaned session row survives its account."""
        _ = await _make_session(db_session, user=test_outsider_user)

        await db_session.delete(test_outsider_user)
        await db_session.flush()

        remaining = await db_session.execute(
            select(func.count()).select_from(AuthSession)
        )
        assert remaining.scalar_one() == 0
