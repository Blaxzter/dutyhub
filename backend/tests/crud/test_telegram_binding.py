"""Unit tests for TelegramBinding CRUD operations."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.telegram_binding import telegram_binding as crud_telegram
from app.models.notification import TelegramBinding
from app.models.user import User


def _future(minutes: int = 10) -> datetime:
    """Return a naive UTC timestamp in the future.

    The ``verification_expires_at`` column is timezone-naive, so the
    application stores naive UTC values (see the telegram routes).
    """
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=minutes)


@pytest.mark.asyncio
class TestCRUDTelegramBinding:
    """Test suite for TelegramBinding CRUD operations."""

    # --- get_by_user -----------------------------------------------------

    async def test_get_by_user_returns_binding(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test fetching the binding of a user that has one."""
        created = await crud_telegram.create_binding(
            db_session,
            user_id=test_user.id,
            verification_code="AABBCCDD",
            expires_at=_future(),
        )

        found = await crud_telegram.get_by_user(db_session, user_id=test_user.id)

        assert found is not None
        assert found.id == created.id
        assert found.user_id == test_user.id

    async def test_get_by_user_returns_none_without_binding(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that a user without a binding yields None."""
        found = await crud_telegram.get_by_user(db_session, user_id=test_user.id)

        assert found is None

    async def test_get_by_user_is_scoped_to_the_user(
        self, db_session: AsyncSession, test_user: User, test_admin_user: User
    ) -> None:
        """Test that one user's binding is not returned for another user."""
        await crud_telegram.create_binding(
            db_session,
            user_id=test_user.id,
            verification_code="SCOPED01",
            expires_at=_future(),
        )

        other = await crud_telegram.get_by_user(db_session, user_id=test_admin_user.id)

        assert other is None

    # --- get_by_chat_id --------------------------------------------------

    async def test_get_by_chat_id_returns_binding(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test finding a binding by its Telegram chat id."""
        created = await crud_telegram.create_verified_binding(
            db_session,
            user_id=test_user.id,
            chat_id="chat-12345",
            username="telegram_user",
        )

        found = await crud_telegram.get_by_chat_id(db_session, chat_id="chat-12345")

        assert found is not None
        assert found.id == created.id
        assert found.telegram_username == "telegram_user"

    async def test_get_by_chat_id_returns_none_for_unknown_chat(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that an unknown chat id yields None."""
        await crud_telegram.create_verified_binding(
            db_session,
            user_id=test_user.id,
            chat_id="chat-known",
        )

        found = await crud_telegram.get_by_chat_id(db_session, chat_id="chat-unknown")

        assert found is None

    # --- get_by_verification_code ----------------------------------------

    async def test_get_by_verification_code_returns_unverified_binding(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test looking up a pending binding by its verification code."""
        created = await crud_telegram.create_binding(
            db_session,
            user_id=test_user.id,
            verification_code="CODE1234",
            expires_at=_future(),
        )

        found = await crud_telegram.get_by_verification_code(
            db_session, code="CODE1234"
        )

        assert found is not None
        assert found.id == created.id
        assert found.is_verified is False

    async def test_get_by_verification_code_ignores_verified_binding(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that a verified binding is never matched by its stale code."""
        binding = TelegramBinding(
            user_id=test_user.id,
            telegram_chat_id="chat-stale",
            telegram_username="stale_user",
            is_verified=True,
            verification_code="STALE001",
            verification_expires_at=_future(),
        )
        db_session.add(binding)
        await db_session.flush()

        found = await crud_telegram.get_by_verification_code(
            db_session, code="STALE001"
        )

        assert found is None

    async def test_get_by_verification_code_matches_only_the_pending_one(
        self, db_session: AsyncSession, test_user: User, test_admin_user: User
    ) -> None:
        """Test that a shared code resolves to the unverified binding only."""
        verified = TelegramBinding(
            user_id=test_user.id,
            telegram_chat_id="chat-shared-code",
            is_verified=True,
            verification_code="SHARED01",
            verification_expires_at=_future(),
        )
        db_session.add(verified)
        await db_session.flush()

        pending = await crud_telegram.create_binding(
            db_session,
            user_id=test_admin_user.id,
            verification_code="SHARED01",
            expires_at=_future(),
        )

        found = await crud_telegram.get_by_verification_code(
            db_session, code="SHARED01"
        )

        assert found is not None
        assert found.id == pending.id
        assert found.user_id == test_admin_user.id

    async def test_get_by_verification_code_returns_none_for_unknown_code(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that an unknown verification code yields None."""
        await crud_telegram.create_binding(
            db_session,
            user_id=test_user.id,
            verification_code="KNOWN001",
            expires_at=_future(),
        )

        found = await crud_telegram.get_by_verification_code(
            db_session, code="NOSUCH01"
        )

        assert found is None

    # --- create_binding ---------------------------------------------------

    async def test_create_binding_creates_pending_binding(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test creating a fresh, unverified binding."""
        expires_at = _future()

        binding = await crud_telegram.create_binding(
            db_session,
            user_id=test_user.id,
            verification_code="NEW00001",
            expires_at=expires_at,
        )

        assert binding.user_id == test_user.id
        assert binding.verification_code == "NEW00001"
        assert binding.verification_expires_at == expires_at
        assert binding.is_verified is False
        assert binding.telegram_chat_id is None
        assert binding.telegram_username is None

    async def test_create_binding_replaces_existing_unverified_binding(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that an existing pending binding is deleted and recreated."""
        first = await crud_telegram.create_binding(
            db_session,
            user_id=test_user.id,
            verification_code="FIRST001",
            expires_at=_future(),
        )
        first_id = first.id

        second = await crud_telegram.create_binding(
            db_session,
            user_id=test_user.id,
            verification_code="SECOND01",
            expires_at=_future(20),
        )

        assert second.id != first_id
        assert second.verification_code == "SECOND01"
        assert second.is_verified is False

        # The old row is gone, so the single-row lookup still resolves.
        found = await crud_telegram.get_by_user(db_session, user_id=test_user.id)
        assert found is not None
        assert found.id == second.id
        assert (
            await crud_telegram.get_by_verification_code(db_session, code="FIRST001")
            is None
        )

    async def test_create_binding_resets_verified_binding_in_place(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that re-binding an already verified user reuses the row."""
        verified = await crud_telegram.create_verified_binding(
            db_session,
            user_id=test_user.id,
            chat_id="chat-rebind",
            username="rebind_user",
        )
        verified_id = verified.id
        expires_at = _future(15)

        rebound = await crud_telegram.create_binding(
            db_session,
            user_id=test_user.id,
            verification_code="REBIND01",
            expires_at=expires_at,
        )

        assert rebound.id == verified_id
        assert rebound.is_verified is False
        assert rebound.verification_code == "REBIND01"
        assert rebound.verification_expires_at == expires_at
        assert rebound.telegram_chat_id is None
        assert rebound.telegram_username is None

    # --- create_verified_binding -----------------------------------------

    async def test_create_verified_binding_creates_new(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test creating an already verified binding for a fresh user."""
        binding = await crud_telegram.create_verified_binding(
            db_session,
            user_id=test_user.id,
            chat_id="chat-widget",
            username="widget_user",
        )

        assert binding.user_id == test_user.id
        assert binding.telegram_chat_id == "chat-widget"
        assert binding.telegram_username == "widget_user"
        assert binding.is_verified is True
        assert binding.verification_code is None
        assert binding.verification_expires_at is None

    async def test_create_verified_binding_without_username(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that the username is optional."""
        binding = await crud_telegram.create_verified_binding(
            db_session,
            user_id=test_user.id,
            chat_id="chat-no-username",
        )

        assert binding.telegram_username is None
        assert binding.is_verified is True

    async def test_create_verified_binding_updates_existing(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test that an existing pending binding is upgraded in place."""
        pending = await crud_telegram.create_binding(
            db_session,
            user_id=test_user.id,
            verification_code="PENDING1",
            expires_at=_future(),
        )
        pending_id = pending.id

        binding = await crud_telegram.create_verified_binding(
            db_session,
            user_id=test_user.id,
            chat_id="chat-upgraded",
            username="upgraded_user",
        )

        assert binding.id == pending_id
        assert binding.telegram_chat_id == "chat-upgraded"
        assert binding.telegram_username == "upgraded_user"
        assert binding.is_verified is True
        assert binding.verification_code is None
        assert binding.verification_expires_at is None

    # --- verify_binding ---------------------------------------------------

    async def test_verify_binding_marks_verified_and_clears_code(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test verifying a pending binding stores the chat and drops the code."""
        pending = await crud_telegram.create_binding(
            db_session,
            user_id=test_user.id,
            verification_code="VERIFY01",
            expires_at=_future(),
        )

        verified = await crud_telegram.verify_binding(
            db_session,
            binding=pending,
            chat_id="chat-verified",
            username="verified_user",
        )

        assert verified.id == pending.id
        assert verified.is_verified is True
        assert verified.telegram_chat_id == "chat-verified"
        assert verified.telegram_username == "verified_user"
        assert verified.verification_code is None
        assert verified.verification_expires_at is None

        # The code no longer resolves once the binding is verified.
        found = await crud_telegram.get_by_verification_code(
            db_session, code="VERIFY01"
        )
        assert found is None

    async def test_verify_binding_without_username(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test verifying a binding when Telegram sends no username."""
        pending = await crud_telegram.create_binding(
            db_session,
            user_id=test_user.id,
            verification_code="NOUSER01",
            expires_at=_future(),
        )

        verified = await crud_telegram.verify_binding(
            db_session,
            binding=pending,
            chat_id="chat-anonymous",
        )

        assert verified.is_verified is True
        assert verified.telegram_chat_id == "chat-anonymous"
        assert verified.telegram_username is None

    # --- remove_binding ---------------------------------------------------

    async def test_remove_binding_returns_true_when_removed(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test removing an existing binding."""
        await crud_telegram.create_verified_binding(
            db_session,
            user_id=test_user.id,
            chat_id="chat-remove",
        )

        removed = await crud_telegram.remove_binding(db_session, user_id=test_user.id)

        assert removed is True
        assert await crud_telegram.get_by_user(db_session, user_id=test_user.id) is None

    async def test_remove_binding_returns_false_when_nothing_to_remove(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Test removing a binding for a user that has none."""
        removed = await crud_telegram.remove_binding(db_session, user_id=test_user.id)

        assert removed is False

    async def test_remove_binding_leaves_other_users_untouched(
        self, db_session: AsyncSession, test_user: User, test_admin_user: User
    ) -> None:
        """Test that removing one user's binding keeps the other user's binding."""
        await crud_telegram.create_verified_binding(
            db_session,
            user_id=test_user.id,
            chat_id="chat-keep-user",
        )
        await crud_telegram.create_verified_binding(
            db_session,
            user_id=test_admin_user.id,
            chat_id="chat-keep-admin",
        )

        removed = await crud_telegram.remove_binding(db_session, user_id=test_user.id)

        assert removed is True
        assert await crud_telegram.get_by_user(db_session, user_id=test_user.id) is None
        remaining = await crud_telegram.get_by_user(
            db_session, user_id=test_admin_user.id
        )
        assert remaining is not None
        assert remaining.telegram_chat_id == "chat-keep-admin"
