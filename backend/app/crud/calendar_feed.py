import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.models.calendar_feed import CalendarFeedToken


class CRUDCalendarFeed:
    async def get_by_user(
        self, db: AsyncSession, *, user_id: uuid.UUID
    ) -> CalendarFeedToken | None:
        query = select(CalendarFeedToken).where(
            col(CalendarFeedToken.user_id) == user_id
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_token(
        self, db: AsyncSession, *, token: str
    ) -> CalendarFeedToken | None:
        query = select(CalendarFeedToken).where(
            col(CalendarFeedToken.token) == token,
            col(CalendarFeedToken.is_enabled).is_(True),
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create_for_user(
        self, db: AsyncSession, *, user_id: uuid.UUID
    ) -> CalendarFeedToken:
        feed_token = CalendarFeedToken(user_id=user_id)
        db.add(feed_token)
        await db.flush()
        await db.refresh(feed_token)
        return feed_token

    async def regenerate_token(
        self, db: AsyncSession, *, db_obj: CalendarFeedToken
    ) -> CalendarFeedToken:
        db_obj.token = secrets.token_urlsafe(32)
        db_obj.is_enabled = True
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def set_enabled(
        self, db: AsyncSession, *, db_obj: CalendarFeedToken, enabled: bool
    ) -> CalendarFeedToken:
        db_obj.is_enabled = enabled
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update_last_accessed(
        self, db: AsyncSession, *, db_obj: CalendarFeedToken
    ) -> None:
        db_obj.last_accessed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.add(db_obj)
        await db.flush()


crud_calendar_feed = CRUDCalendarFeed()
