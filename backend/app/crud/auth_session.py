import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.crud.base import CRUDBase
from app.models.auth_session import AuthSession
from app.schemas.auth import AuthSessionCreate, AuthSessionUpdate


def _now() -> datetime:
    """Naive UTC, matching how every timestamp in this schema is stored."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CRUDAuthSession(CRUDBase[AuthSession, AuthSessionCreate, AuthSessionUpdate]):
    """Refresh sessions: the server-side half of every signed-in device.

    Rows are never deleted here, only stamped. A revoked session still answers
    ``get_by_token_hash``, and that is the entire mechanism behind reuse
    detection: a refresh token that was already rotated away is either a replay
    of a stale request or a stolen cookie, and telling those apart is impossible
    — so the row survives to say "this token existed and is dead", which the
    logic layer answers by revoking every session the user has.
    """

    async def get_by_token_hash(
        self, db: AsyncSession, *, token_hash: str
    ) -> AuthSession | None:
        """Find a session by the hash of the refresh token presented.

        Deliberately unfiltered: revoked and expired rows come back too. Adding
        ``revoked_at IS NULL`` here looks like tightening security and quietly
        removes it, because a stolen token would then be indistinguishable from
        a token that never existed and reuse detection would never fire. The
        caller decides what the row's state means.
        """
        result = await db.execute(
            select(AuthSession).where(col(AuthSession.refresh_token_hash) == token_hash)
        )
        return result.scalar_one_or_none()

    async def list_active_for_user(
        self, db: AsyncSession, *, user_id: uuid.UUID
    ) -> Sequence[AuthSession]:
        """Sessions worth showing in Security settings: live, and still usable.

        Ordered newest sign-in first. ``last_used_at`` would be the more useful
        sort key, but it is NULL until the first refresh and NULLS ordering
        differs by dialect, so the stable ``created_at`` is used and the UI
        renders both timestamps.
        """
        result = await db.execute(
            select(AuthSession)
            .where(
                col(AuthSession.user_id) == user_id,
                col(AuthSession.revoked_at).is_(None),
                col(AuthSession.expires_at) > _now(),
            )
            .order_by(col(AuthSession.created_at).desc())
        )
        return result.scalars().all()

    async def revoke(self, db: AsyncSession, *, db_obj: AuthSession) -> AuthSession:
        """End a session, keeping the row.

        An already-revoked session keeps its original timestamp: the moment a
        session died is evidence, and re-stamping it on a second logout would
        erase when a theft was actually detected.
        """
        if db_obj.revoked_at is None:
            db_obj.revoked_at = _now()
            db.add(db_obj)
            await db.flush()
            await db.refresh(db_obj)
        return db_obj

    async def revoke_all_for_user(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        except_session_id: uuid.UUID | None = None,
    ) -> int:
        """Sign a user out everywhere, optionally sparing the caller's own device.

        Three flows need this: a password reset and reuse detection revoke
        *everything* (the account may be in someone else's hands), while a
        deliberate password change spares the session doing the changing, since
        being logged out of the tab you just used is confusing rather than safe.

        Rows are loaded and stamped one by one rather than bulk-updated. A
        person has a handful of devices, and going through the ORM keeps the
        identity map honest — a bulk ``UPDATE`` would leave any session object
        already loaded in this request claiming it is still live.

        Returns the number of sessions actually revoked.
        """
        query = select(AuthSession).where(
            col(AuthSession.user_id) == user_id,
            col(AuthSession.revoked_at).is_(None),
        )
        if except_session_id is not None:
            query = query.where(col(AuthSession.id) != except_session_id)

        result = await db.execute(query)
        revoked = list(result.scalars().all())

        now = _now()
        for session_row in revoked:
            session_row.revoked_at = now
            db.add(session_row)
        await db.flush()
        return len(revoked)


auth_session = CRUDAuthSession(AuthSession)
