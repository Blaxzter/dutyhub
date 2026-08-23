import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.crud.base import CRUDBase
from app.logic.notifications.registry import NotificationTypeDict
from app.models.notification import NotificationType


class _Empty(BaseModel):
    pass


class CRUDNotificationType(CRUDBase[NotificationType, _Empty, _Empty]):
    async def get_by_code(self, db: AsyncSession, code: str) -> NotificationType | None:
        query = select(NotificationType).where(col(NotificationType.code) == code)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_all_active(
        self,
        db: AsyncSession,
        *,
        include_admin_only: bool = False,
    ) -> Sequence[NotificationType]:
        query = select(NotificationType).where(col(NotificationType.is_active) == True)  # noqa: E712
        if not include_admin_only:
            query = query.where(col(NotificationType.is_admin_only) == False)  # noqa: E712
        query = query.order_by(
            col(NotificationType.category), col(NotificationType.code)
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def upsert_from_registry(
        self,
        db: AsyncSession,
        *,
        types: list[NotificationTypeDict],
    ) -> int:
        """Upsert notification types from the code-level registry.

        One statement, and it has to be one statement. The app runs as
        ``fastapi run --workers 4`` (``backend/Dockerfile``), so on a database
        that does not yet hold these rows all four processes reach this during
        lifespan startup at the same moment. Reading first and inserting second
        let every one of them decide a row was missing and insert it; three
        then died on ``ix_notification_types_code``, and because this runs in
        the lifespan that is not a logged warning but *the container failing to
        start*. ``ON CONFLICT DO UPDATE`` makes the losers of that race update
        the winner's row instead of raising.

        ``id``/``created_at``/``updated_at`` are supplied explicitly: those
        come from the ``Base`` mixin as Python-side defaults, which a Core
        insert does not run.

        Returns the number of types upserted.
        """
        if not types:
            return 0

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        rows: list[dict[str, Any]] = [
            {"id": uuid.uuid4(), "created_at": now, "updated_at": now, **type_data}
            for type_data in types
        ]

        insert_stmt = pg_insert(NotificationType).values(rows)
        excluded = insert_stmt.excluded
        # Everything the registry owns, plus the timestamp. `code` is the
        # conflict target and `created_at`/`id` belong to whoever inserted
        # first — re-stamping them would rewrite history on every boot.
        updatable = [key for key in types[0] if key != "code"]
        statement = insert_stmt.on_conflict_do_update(
            index_elements=["code"],
            set_={key: excluded[key] for key in updatable}
            | {"updated_at": excluded["updated_at"]},
        )
        _ = await db.execute(statement)
        return len(rows)


notification_type = CRUDNotificationType(NotificationType)
