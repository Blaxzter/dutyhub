from collections.abc import Sequence
from typing import Literal

from sqlalchemy import ColumnElement, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

UserStatus = Literal["all", "active", "pending", "rejected"]


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_auth0_sub(
        self, db: AsyncSession, *, auth0_sub: str
    ) -> User | None:
        result = await db.execute(select(User).where(col(User.auth0_sub) == auth0_sub))
        return result.scalars().first()

    async def get_by_email(self, db: AsyncSession, *, email: str) -> User | None:
        result = await db.execute(select(User).where(col(User.email) == email))
        return result.scalars().first()

    @staticmethod
    def _q_clauses(q: str | None) -> list[ColumnElement[bool]]:
        if not q:
            return []
        pattern = f"%{q.strip().lower()}%"
        return [
            or_(
                func.lower(col(User.name)).like(pattern),
                func.lower(col(User.email)).like(pattern),
            )
        ]

    @staticmethod
    def _status_clauses(status: UserStatus) -> list[ColumnElement[bool]]:
        if status == "active":
            return [col(User.is_active).is_(True)]
        if status == "pending":
            return [
                col(User.is_active).is_(False),
                col(User.rejection_reason).is_(None),
            ]
        if status == "rejected":
            return [
                col(User.is_active).is_(False),
                col(User.rejection_reason).is_not(None),
            ]
        return []

    async def search(
        self,
        db: AsyncSession,
        *,
        q: str | None = None,
        status: UserStatus = "all",
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[User], dict[str, int]]:
        q_clauses = self._q_clauses(q)
        status_clauses = self._status_clauses(status)

        items_query = (
            select(User)
            .where(*q_clauses, *status_clauses)
            .order_by(col(User.created_at).desc())
            .offset(skip)
            .limit(limit)
        )

        pending_case = case(
            (
                col(User.is_active).is_(False) & col(User.rejection_reason).is_(None),
                1,
            )
        )
        rejected_case = case(
            (
                col(User.is_active).is_(False)
                & col(User.rejection_reason).is_not(None),
                1,
            )
        )
        active_case = case((col(User.is_active).is_(True), 1))

        counts_query = (
            select(
                func.count().label("all"),
                func.count(active_case).label("active"),
                func.count(pending_case).label("pending"),
                func.count(rejected_case).label("rejected"),
            )
            .select_from(User)
            .where(*q_clauses)
        )

        items_result = await db.execute(items_query)
        counts_result = await db.execute(counts_query)
        counts_row = counts_result.one()

        counts = {
            "all": int(counts_row.all or 0),
            "active": int(counts_row.active or 0),
            "pending": int(counts_row.pending or 0),
            "rejected": int(counts_row.rejected or 0),
        }
        return items_result.scalars().all(), counts


user = CRUDUser(User)
