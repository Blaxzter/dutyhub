import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.crud.base import CRUDBase
from app.models.user_token import UserToken
from app.schemas.auth import UserTokenCreate, UserTokenPurpose, UserTokenUpdate


def _now() -> datetime:
    """Naive UTC, matching how every timestamp in this schema is stored."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CRUDUserToken(CRUDBase[UserToken, UserTokenCreate, UserTokenUpdate]):
    """Single-use secrets that arrive by email: verify an address, reset a password.

    Only the sha256 of what was mailed is stored, so a leak of this table is not
    a leak of anybody's account. Redemption stamps ``consumed_at`` rather than
    deleting the row, which is what lets a second click on the same link be
    answered with "already used" instead of the far more alarming "invalid
    token" — and leaves an audit trail of what was issued when.
    """

    async def get_by_token_hash(
        self, db: AsyncSession, *, token_hash: str
    ) -> UserToken | None:
        """Find a token by the hash of the secret presented.

        Unfiltered on purpose, exactly as with refresh sessions: expired and
        already-consumed rows come back so the caller can tell a user *why*
        their link did not work. Filtering here would collapse three different
        situations into one unhelpful "invalid".
        """
        result = await db.execute(
            select(UserToken).where(col(UserToken.token_hash) == token_hash)
        )
        return result.scalar_one_or_none()

    async def consume(self, db: AsyncSession, *, db_obj: UserToken) -> UserToken:
        """Mark a token redeemed.

        Idempotent, and keeps the first timestamp: when a link was used is
        evidence, and a double submit from an impatient click must not rewrite
        it.
        """
        if db_obj.consumed_at is None:
            db_obj.consumed_at = _now()
            db.add(db_obj)
            await db.flush()
            await db.refresh(db_obj)
        return db_obj

    async def consume_outstanding(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        purpose: UserTokenPurpose,
    ) -> int:
        """Burn every token of one purpose still open for this user.

        Issuing a token does *not* invalidate the ones before it — a "resend"
        must not break the mail already sitting in someone's inbox. Succeeding
        does: once a password has actually been reset, every other reset link in
        every other inbox copy is a spare key to the account, including the one
        an attacker asked for. So this runs after the flow completes, not before
        it starts.

        Returns the number of tokens closed.
        """
        result = await db.execute(
            select(UserToken).where(
                col(UserToken.user_id) == user_id,
                col(UserToken.purpose) == purpose,
                col(UserToken.consumed_at).is_(None),
            )
        )
        outstanding = list(result.scalars().all())

        now = _now()
        for token_row in outstanding:
            token_row.consumed_at = now
            db.add(token_row)
        await db.flush()
        return len(outstanding)


user_token = CRUDUserToken(UserToken)
