"""Unit tests for the notification type seeder."""

from typing import cast
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.crud.notification_type import notification_type as crud_notif_type
from app.logic.notifications.registry import (
    ALL_NOTIFICATION_TYPES,
    BOOKING_CONFIRMED,
    NotificationTypeDict,
)
from app.logic.notifications.seeder import seed_notification_types
from app.models.notification import NotificationType

# Spot-check codes that must exist after seeding. Kept explicit (not derived
# from the registry) so a silent registry rename shows up as a test failure.
KNOWN_CODES = ["booking.confirmed", "task.published", "user.registered"]


@pytest.mark.asyncio
class TestSeedNotificationTypes:
    """Test suite for seed_notification_types."""

    async def _rows_for_code(
        self, db_session: AsyncSession, code: str
    ) -> list[NotificationType]:
        """Return every persisted notification_types row with the given code."""
        query = select(NotificationType).where(col(NotificationType.code) == code)
        result = await db_session.execute(query)
        return list(result.scalars().all())

    async def _persisted_registry_codes(self, db_session: AsyncSession) -> set[str]:
        """Return the persisted codes that are part of the code registry."""
        registry_codes = [t.code for t in ALL_NOTIFICATION_TYPES]
        query = select(NotificationType).where(
            col(NotificationType.code).in_(registry_codes)
        )
        result = await db_session.execute(query)
        return {nt.code for nt in result.scalars().all()}

    async def test_seed_returns_registry_count(self, db_session: AsyncSession) -> None:
        """Test that seeding reports one upsert per registry entry."""
        count = await seed_notification_types(db_session)

        assert count == len(ALL_NOTIFICATION_TYPES)

    async def test_seed_persists_known_codes(self, db_session: AsyncSession) -> None:
        """Test that well-known notification types exist after seeding."""
        await seed_notification_types(db_session)

        for code in KNOWN_CODES:
            found = await crud_notif_type.get_by_code(db_session, code)
            assert found is not None, f"{code} was not persisted by the seeder"
            assert found.code == code
            assert found.name

    async def test_seed_persists_every_registry_code(
        self, db_session: AsyncSession
    ) -> None:
        """Test that every registry entry has a matching database row."""
        await seed_notification_types(db_session)

        persisted = await self._persisted_registry_codes(db_session)

        assert persisted == {t.code for t in ALL_NOTIFICATION_TYPES}

    async def test_seed_twice_returns_same_count(
        self, db_session: AsyncSession
    ) -> None:
        """Test that a second seeding run reports the same number of upserts."""
        first = await seed_notification_types(db_session)
        second = await seed_notification_types(db_session)

        assert first == len(ALL_NOTIFICATION_TYPES)
        assert second == first

    async def test_seed_is_idempotent(self, db_session: AsyncSession) -> None:
        """Test that seeding twice does not duplicate rows."""
        await seed_notification_types(db_session)
        await seed_notification_types(db_session)

        for code in KNOWN_CODES:
            rows = await self._rows_for_code(db_session, code)
            assert len(rows) == 1, f"{code} was duplicated by a second seeding run"

        persisted = await self._persisted_registry_codes(db_session)
        assert len(persisted) == len(ALL_NOTIFICATION_TYPES)

    async def test_persisted_row_matches_registry_definition(
        self, db_session: AsyncSession
    ) -> None:
        """Test that a seeded row mirrors its registry definition."""
        await seed_notification_types(db_session)

        found = await crud_notif_type.get_by_code(db_session, BOOKING_CONFIRMED.code)

        assert found is not None
        assert found.name == BOOKING_CONFIRMED.name
        assert found.description == BOOKING_CONFIRMED.description
        assert found.category == BOOKING_CONFIRMED.category
        assert found.classification == BOOKING_CONFIRMED.classification
        assert found.is_admin_only == BOOKING_CONFIRMED.is_admin_only
        assert found.default_channels == BOOKING_CONFIRMED.default_channels
        assert found.is_user_configurable == BOOKING_CONFIRMED.is_user_configurable

    async def test_seed_refreshes_stale_row(self, db_session: AsyncSession) -> None:
        """Test that seeding overwrites drifted values on an existing row."""
        stale: NotificationTypeDict = BOOKING_CONFIRMED.to_dict()
        stale["name"] = "Stale Name"
        stale["description"] = "Stale description"
        stale["category"] = "stale"
        stale["default_channels"] = ["telegram"]
        await crud_notif_type.upsert_from_registry(db_session, types=[stale])

        await seed_notification_types(db_session)

        found = await crud_notif_type.get_by_code(db_session, BOOKING_CONFIRMED.code)
        assert found is not None
        assert found.name == BOOKING_CONFIRMED.name
        assert found.description == BOOKING_CONFIRMED.description
        assert found.category == BOOKING_CONFIRMED.category
        assert found.default_channels == BOOKING_CONFIRMED.default_channels

        rows = await self._rows_for_code(db_session, BOOKING_CONFIRMED.code)
        assert len(rows) == 1

    async def test_seed_commits_and_returns_crud_count(self) -> None:
        """Test that the seeder forwards the registry and commits the session."""
        captured: list[list[NotificationTypeDict]] = []

        async def _fake_upsert(
            db: AsyncSession, *, types: list[NotificationTypeDict]
        ) -> int:
            _ = db
            captured.append(types)
            return 7

        mock_db = AsyncMock(spec=AsyncSession)

        with patch(
            "app.logic.notifications.seeder.crud_notification_type.upsert_from_registry",
            new=_fake_upsert,
        ):
            count = await seed_notification_types(cast(AsyncSession, mock_db))

        assert count == 7
        mock_db.commit.assert_awaited_once()
        assert len(captured) == 1
        assert {t["code"] for t in captured[0]} == {
            t.code for t in ALL_NOTIFICATION_TYPES
        }
