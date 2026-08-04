"""Route tests for the Telegram binding endpoints.

Covers `app/api/routes/notifications/telegram.py`, which is mounted under
`/api/v1/notifications` (see `app/api/api.py` -> `notifications.router`, which
carries `prefix="/notifications"`).
"""

import hashlib
import hmac
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud.telegram_binding import telegram_binding as crud_telegram
from app.models.notification import TelegramBinding
from app.models.user import User

BASE = "/api/v1/notifications/telegram"

BOT_TOKEN = "123456:TEST-BOT-TOKEN"


def _utcnow() -> datetime:
    """Naive UTC "now", matching what the route stores in the database."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _sign_login_payload(payload: dict[str, str | int], bot_token: str) -> str:
    """Compute the Telegram Login Widget hash exactly like the route does.

    Mirrors `_verify_telegram_login`: the payload must already exclude `hash`
    and any `None` values (`model_dump(exclude={"hash"}, exclude_none=True)`).
    """
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    return hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()


async def _make_pending_binding(
    db_session: AsyncSession,
    *,
    user_id: uuid.UUID,
    code: str,
    expires_in_minutes: int = 10,
) -> TelegramBinding:
    """Create an unverified binding with a verification code."""
    return await crud_telegram.create_binding(
        db_session,
        user_id=user_id,
        verification_code=code,
        expires_at=_utcnow() + timedelta(minutes=expires_in_minutes),
    )


@pytest.mark.asyncio
class TestTelegramConfigRoute:
    """Test suite for GET /notifications/telegram/config."""

    async def test_config_when_configured_strips_at_prefix(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a configured bot reports its username without the leading @."""
        monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", BOT_TOKEN)
        monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "@wirksam_test_bot")

        r = await async_client.get(f"{BASE}/config")

        assert r.status_code == 200
        data = r.json()
        assert data["bot_username"] == "wirksam_test_bot"
        assert data["is_configured"] is True

    async def test_config_when_not_configured(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that an unconfigured bot reports is_configured=False and no username."""
        monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", None)
        monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", None)

        r = await async_client.get(f"{BASE}/config")

        assert r.status_code == 200
        data = r.json()
        assert data["bot_username"] is None
        assert data["is_configured"] is False

    async def test_config_username_without_at_is_unchanged(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a username without a leading @ is returned verbatim."""
        monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", BOT_TOKEN)
        monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "wirksam_test_bot")

        r = await async_client.get(f"{BASE}/config")

        assert r.status_code == 200
        assert r.json()["bot_username"] == "wirksam_test_bot"


@pytest.mark.asyncio
class TestGetTelegramBindingRoute:
    """Test suite for GET /notifications/telegram."""

    async def test_get_binding_returns_null_when_unbound(
        self, async_client: AsyncClient
    ) -> None:
        """Test that a user without a binding gets a null body."""
        r = await async_client.get(BASE)

        assert r.status_code == 200
        assert r.json() is None

    async def test_get_binding_returns_existing_binding(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that an existing binding is returned for the current user."""
        await crud_telegram.create_verified_binding(
            db_session,
            user_id=test_user.id,
            chat_id="99001",
            username="bound_user",
        )

        r = await async_client.get(BASE)

        assert r.status_code == 200
        data = r.json()
        assert data is not None
        assert data["telegram_chat_id"] == "99001"
        assert data["telegram_username"] == "bound_user"
        assert data["is_verified"] is True


@pytest.mark.asyncio
class TestStartTelegramBindingRoute:
    """Test suite for POST /notifications/telegram/bind."""

    async def test_bind_returns_code_and_creates_pending_binding(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that binding returns an 8-char hex code and persists a pending row."""
        before = _utcnow()

        r = await async_client.post(f"{BASE}/bind")

        assert r.status_code == 200
        data = r.json()

        code = data["verification_code"]
        assert len(code) == 8
        assert code == code.upper()
        assert set(code) <= set("0123456789ABCDEF")

        expires_at = datetime.fromisoformat(data["expires_at"])
        delta = (expires_at - before).total_seconds()
        assert 9 * 60 <= delta <= 11 * 60

        binding = await crud_telegram.get_by_user(db_session, user_id=test_user.id)
        assert binding is not None
        assert binding.is_verified is False
        assert binding.verification_code == code
        assert binding.telegram_chat_id is None

    async def test_bind_includes_cleaned_bot_username(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that the bind response strips the @ from the bot username."""
        monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "@wirksam_test_bot")

        r = await async_client.post(f"{BASE}/bind")

        assert r.status_code == 200
        assert r.json()["bot_username"] == "wirksam_test_bot"


@pytest.mark.asyncio
class TestVerifyTelegramBindingRoute:
    """Test suite for POST /notifications/telegram/verify."""

    async def test_verify_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that a valid, unexpired code verifies the binding."""
        binding = await _make_pending_binding(
            db_session, user_id=test_user.id, code="AABBCCDD"
        )

        r = await async_client.post(
            f"{BASE}/verify",
            json={
                "verification_code": "AABBCCDD",
                "telegram_chat_id": "12345",
                "telegram_username": "tg_user",
            },
        )

        assert r.status_code == 200
        data = r.json()
        assert data["is_verified"] is True
        assert data["telegram_chat_id"] == "12345"
        assert data["telegram_username"] == "tg_user"

        await db_session.refresh(binding)
        assert binding.is_verified is True
        assert binding.verification_code is None

    async def test_verify_success_without_expiry(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that a binding with no expiry timestamp verifies successfully."""
        binding = await _make_pending_binding(
            db_session, user_id=test_user.id, code="NOEXPIRY"
        )
        binding.verification_expires_at = None
        db_session.add(binding)
        await db_session.flush()

        r = await async_client.post(
            f"{BASE}/verify",
            json={
                "verification_code": "NOEXPIRY",
                "telegram_chat_id": "12346",
            },
        )

        assert r.status_code == 200
        data = r.json()
        assert data["is_verified"] is True
        assert data["telegram_username"] is None

    async def test_verify_unknown_code_returns_400(
        self, async_client: AsyncClient
    ) -> None:
        """Test that an unknown verification code is rejected."""
        r = await async_client.post(
            f"{BASE}/verify",
            json={
                "verification_code": "DEADBEEF",
                "telegram_chat_id": "12347",
            },
        )

        assert r.status_code == 400
        assert r.json()["code"] == "telegram.invalid_code"

    async def test_verify_code_of_another_user_returns_400(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_admin_user: User,
    ) -> None:
        """Test that a code belonging to a different user cannot be redeemed."""
        binding = await _make_pending_binding(
            db_session, user_id=test_admin_user.id, code="OTHERUSR"
        )

        r = await async_client.post(
            f"{BASE}/verify",
            json={
                "verification_code": "OTHERUSR",
                "telegram_chat_id": "12348",
            },
        )

        assert r.status_code == 400
        assert r.json()["code"] == "telegram.invalid_code"

        await db_session.refresh(binding)
        assert binding.is_verified is False
        assert binding.telegram_chat_id is None

    async def test_verify_expired_code_returns_400(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that an expired verification code is rejected."""
        binding = await _make_pending_binding(
            db_session, user_id=test_user.id, code="EXPIRED1"
        )
        binding.verification_expires_at = _utcnow() - timedelta(minutes=1)
        db_session.add(binding)
        await db_session.flush()

        r = await async_client.post(
            f"{BASE}/verify",
            json={
                "verification_code": "EXPIRED1",
                "telegram_chat_id": "12349",
            },
        )

        assert r.status_code == 400
        assert r.json()["code"] == "telegram.code_expired"

        await db_session.refresh(binding)
        assert binding.is_verified is False


@pytest.mark.asyncio
class TestUnbindTelegramRoute:
    """Test suite for DELETE /notifications/telegram."""

    async def test_unbind_removes_existing_binding(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that deleting an existing binding returns 204 and removes the row."""
        await crud_telegram.create_verified_binding(
            db_session,
            user_id=test_user.id,
            chat_id="55501",
            username="to_remove",
        )

        r = await async_client.delete(BASE)

        assert r.status_code == 204
        assert await crud_telegram.get_by_user(db_session, user_id=test_user.id) is None

    async def test_unbind_without_binding_returns_404(
        self, async_client: AsyncClient
    ) -> None:
        """Test that deleting a nonexistent binding returns 404."""
        r = await async_client.delete(BASE)

        assert r.status_code == 404
        assert r.json()["code"] == "telegram.not_bound"


@pytest.mark.asyncio
class TestTelegramLoginRoute:
    """Test suite for POST /notifications/telegram/login."""

    async def test_login_without_bot_token_returns_400(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that login fails when the bot token is not configured."""
        monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", None)

        r = await async_client.post(
            f"{BASE}/login",
            json={
                "id": 4242,
                "auth_date": int(time.time()),
                "hash": "deadbeef",
            },
        )

        assert r.status_code == 400
        assert r.json()["code"] == "telegram.not_configured"

    async def test_login_with_invalid_hash_returns_400(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a forged/incorrect hash is rejected."""
        monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", BOT_TOKEN)

        r = await async_client.post(
            f"{BASE}/login",
            json={
                "id": 4243,
                "first_name": "Ada",
                "auth_date": int(time.time()),
                "hash": "00" * 32,
            },
        )

        assert r.status_code == 400
        assert r.json()["code"] == "telegram.invalid_auth"

    async def test_login_with_stale_auth_date_returns_400(
        self, async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a correctly signed but stale auth_date is rejected."""
        monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", BOT_TOKEN)

        payload: dict[str, str | int] = {
            "id": 4244,
            "first_name": "Grace",
            "auth_date": int(time.time()) - 7200,
        }
        body = dict(payload)
        body["hash"] = _sign_login_payload(payload, BOT_TOKEN)

        r = await async_client.post(f"{BASE}/login", json=body)

        assert r.status_code == 400
        assert r.json()["code"] == "telegram.auth_expired"

    async def test_login_success_creates_verified_binding(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that a correctly signed, fresh payload creates a verified binding."""
        monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", BOT_TOKEN)

        payload: dict[str, str | int] = {
            "id": 4245,
            "first_name": "Alan",
            "last_name": "Turing",
            "username": "alan_t",
            "photo_url": "https://t.me/i/userpic/320/alan_t.jpg",
            "auth_date": int(time.time()),
        }
        body = dict(payload)
        body["hash"] = _sign_login_payload(payload, BOT_TOKEN)

        r = await async_client.post(f"{BASE}/login", json=body)

        assert r.status_code == 200
        data = r.json()
        assert data["telegram_chat_id"] == "4245"
        assert data["telegram_username"] == "alan_t"
        assert data["is_verified"] is True

        binding = await crud_telegram.get_by_user(db_session, user_id=test_user.id)
        assert binding is not None
        assert binding.telegram_chat_id == "4245"
        assert binding.is_verified is True


@pytest.mark.asyncio
class TestTelegramWebhookRoute:
    """Test suite for POST /notifications/telegram/webhook."""

    async def test_webhook_without_message_is_ignored(
        self, async_client: AsyncClient
    ) -> None:
        """Test that an update without a message is acknowledged and ignored."""
        r = await async_client.post(f"{BASE}/webhook", json={})

        assert r.status_code == 200
        assert r.json() == {"ok": True}

    async def test_webhook_message_without_text_is_ignored(
        self, async_client: AsyncClient
    ) -> None:
        """Test that a message without text is acknowledged and ignored."""
        r = await async_client.post(
            f"{BASE}/webhook", json={"message": {"chat": {"id": 777}}}
        )

        assert r.status_code == 200
        assert r.json() == {"ok": True}

    async def test_webhook_message_without_chat_is_ignored(
        self, async_client: AsyncClient
    ) -> None:
        """Test that a message without a chat is acknowledged and ignored."""
        r = await async_client.post(
            f"{BASE}/webhook", json={"message": {"text": "ABCD1234"}}
        )

        assert r.status_code == 200
        assert r.json() == {"ok": True}

    async def test_webhook_blank_text_is_ignored(
        self, async_client: AsyncClient
    ) -> None:
        """Test that whitespace-only text is acknowledged and ignored."""
        r = await async_client.post(
            f"{BASE}/webhook",
            json={"message": {"text": "   ", "chat": {"id": 778}}},
        )

        assert r.status_code == 200
        assert r.json() == {"ok": True}

    async def test_webhook_unknown_code_is_ignored(
        self, async_client: AsyncClient
    ) -> None:
        """Test that a text that matches no binding is acknowledged and ignored."""
        r = await async_client.post(
            f"{BASE}/webhook",
            json={"message": {"text": "NOSUCHCD", "chat": {"id": 779}}},
        )

        assert r.status_code == 200
        assert r.json() == {"ok": True}

    async def test_webhook_verifies_matching_code(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that sending the verification code verifies the binding."""
        binding = await _make_pending_binding(
            db_session, user_id=test_user.id, code="WEBH0001"
        )

        r = await async_client.post(
            f"{BASE}/webhook",
            json={
                "message": {
                    "text": "webh0001",
                    "chat": {"id": 81001, "username": "hook_user"},
                }
            },
        )

        assert r.status_code == 200
        assert r.json() == {"ok": True}

        await db_session.refresh(binding)
        assert binding.is_verified is True
        assert binding.telegram_chat_id == "81001"
        assert binding.telegram_username == "hook_user"
        assert binding.verification_code is None

    async def test_webhook_handles_start_deep_link(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that the "/start CODE" deep-link prefix is stripped and verified."""
        binding = await _make_pending_binding(
            db_session, user_id=test_user.id, code="WEBH0002"
        )

        r = await async_client.post(
            f"{BASE}/webhook",
            json={
                "message": {
                    "text": "/start WEBH0002",
                    "chat": {"id": 81002},
                }
            },
        )

        assert r.status_code == 200
        assert r.json() == {"ok": True}

        await db_session.refresh(binding)
        assert binding.is_verified is True
        assert binding.telegram_chat_id == "81002"
        assert binding.telegram_username is None

    async def test_webhook_ignores_expired_code(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that an expired code leaves the binding unverified."""
        binding = await _make_pending_binding(
            db_session, user_id=test_user.id, code="WEBH0003"
        )
        binding.verification_expires_at = _utcnow() - timedelta(minutes=1)
        db_session.add(binding)
        await db_session.flush()

        r = await async_client.post(
            f"{BASE}/webhook",
            json={
                "message": {
                    "text": "WEBH0003",
                    "chat": {"id": 81003},
                }
            },
        )

        assert r.status_code == 200
        assert r.json() == {"ok": True}

        await db_session.refresh(binding)
        assert binding.is_verified is False
        assert binding.telegram_chat_id is None

    async def test_webhook_verifies_code_without_expiry(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Test that a binding with no expiry timestamp is verified by the webhook."""
        binding = await _make_pending_binding(
            db_session, user_id=test_user.id, code="WEBH0004"
        )
        binding.verification_expires_at = None
        db_session.add(binding)
        await db_session.flush()

        r = await async_client.post(
            f"{BASE}/webhook",
            json={
                "message": {
                    "text": "WEBH0004",
                    "chat": {"id": 81004},
                }
            },
        )

        assert r.status_code == 200
        assert r.json() == {"ok": True}

        await db_session.refresh(binding)
        assert binding.is_verified is True
        assert binding.telegram_chat_id == "81004"
