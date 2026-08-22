import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.models.event_join_request import EventJoinRequest
from app.models.user import User


class CRUDEventJoinRequest:
    async def get(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        event_id: uuid.UUID,
    ) -> EventJoinRequest | None:
        result = await session.execute(
            select(EventJoinRequest).where(
                col(EventJoinRequest.user_id) == user_id,
                col(EventJoinRequest.event_id) == event_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(
        self,
        session: AsyncSession,
        *,
        request_id: uuid.UUID,
    ) -> EventJoinRequest | None:
        result = await session.execute(
            select(EventJoinRequest).where(col(EventJoinRequest.id) == request_id)
        )
        return result.scalar_one_or_none()

    async def list_for_event(
        self,
        session: AsyncSession,
        *,
        event_id: uuid.UUID,
        status: str | None = "pending",
    ) -> list[tuple[EventJoinRequest, User]]:
        query = (
            select(EventJoinRequest, User)
            .join(User, col(User.id) == col(EventJoinRequest.user_id))
            .where(col(EventJoinRequest.event_id) == event_id)
        )
        if status:
            query = query.where(col(EventJoinRequest.status) == status)
        query = query.order_by(col(EventJoinRequest.created_at).asc())
        result = await session.execute(query)
        return [(r, u) for r, u in result.all()]

    async def statuses_for_user(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        event_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, str]:
        if not event_ids:
            return {}
        result = await session.execute(
            select(col(EventJoinRequest.event_id), col(EventJoinRequest.status)).where(
                col(EventJoinRequest.user_id) == user_id,
                col(EventJoinRequest.event_id).in_(event_ids),
            )
        )
        return {row[0]: row[1] for row in result.all()}

    async def count_pending_by_event(
        self,
        session: AsyncSession,
        *,
        event_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, int]:
        if not event_ids:
            return {}
        result = await session.execute(
            select(col(EventJoinRequest.event_id), func.count())
            .where(
                col(EventJoinRequest.event_id).in_(event_ids),
                col(EventJoinRequest.status) == "pending",
            )
            .group_by(col(EventJoinRequest.event_id))
        )
        return {row[0]: row[1] for row in result.all()}

    async def upsert_pending(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        event_id: uuid.UUID,
        message: str | None,
    ) -> EventJoinRequest:
        """Create a request, or re-open a previously declined one.

        Re-opening rather than blocking means a declined applicant can ask
        again after talking to the organiser, without an admin having to
        delete the old row.
        """
        obj = await self.get(session, user_id=user_id, event_id=event_id)
        if obj:
            obj.status = "pending"
            obj.message = message
            obj.decided_at = None
            obj.decided_by_id = None
        else:
            obj = EventJoinRequest(
                user_id=user_id,
                event_id=event_id,
                message=message,
                status="pending",
            )
        session.add(obj)
        await session.flush()
        await session.refresh(obj)
        return obj

    async def decide(
        self,
        session: AsyncSession,
        *,
        request: EventJoinRequest,
        approve: bool,
        decided_by_id: uuid.UUID,
    ) -> EventJoinRequest:
        request.status = "approved" if approve else "declined"
        request.decided_at = datetime.now(timezone.utc).replace(tzinfo=None)
        request.decided_by_id = decided_by_id
        session.add(request)
        await session.flush()
        await session.refresh(request)
        return request

    async def delete_for_user(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        event_id: uuid.UUID,
    ) -> bool:
        obj = await self.get(session, user_id=user_id, event_id=event_id)
        if not obj:
            return False
        await session.delete(obj)
        await session.flush()
        return True


event_join_request = CRUDEventJoinRequest()
