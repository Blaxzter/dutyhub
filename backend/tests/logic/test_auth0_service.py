"""Unit tests for the Auth0 Management API service helpers.

Every test patches ``httpx.AsyncClient`` inside ``app.logic.auth0.auth0_service``
so no network call is ever made. ``get_management_api_token`` and
``get_management_api_base_url`` are patched in the service namespace because the
module imports them by name.
"""

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

from app.logic.auth0.auth0_service import delete_auth0_user, update_auth0_user
from app.schemas.users import UserProfileUpdate

MODULE = "app.logic.auth0.auth0_service"
FAKE_TOKEN = "fake-management-token"
BASE_URL = "https://tenant.auth0.com/api/v2"
AUTH0_SUB = "auth0|test123"
DELETE_HEADERS = {"Authorization": f"Bearer {FAKE_TOKEN}"}
PATCH_HEADERS = {
    "Authorization": f"Bearer {FAKE_TOKEN}",
    "Content-Type": "application/json",
}


class _StubResponse:
    """Minimal stand-in for ``httpx.Response`` with only what the service reads."""

    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


def _wire_client(mock_client_cls: MagicMock) -> MagicMock:
    """Make ``async with httpx.AsyncClient() as client`` yield a mock client.

    Returns the inner client, whose ``delete`` and ``patch`` attributes are
    ``AsyncMock``s the test can configure and assert on.
    """
    inner_client = MagicMock()
    inner_client.delete = AsyncMock()
    inner_client.patch = AsyncMock()

    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=inner_client)
    context_manager.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = context_manager

    return inner_client


def _sent_json(mock_method: AsyncMock) -> dict[str, Any]:
    """Return the ``json=`` payload of the single recorded call."""
    assert mock_method.await_args is not None
    payload = mock_method.await_args.kwargs["json"]
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


@pytest.mark.asyncio
class TestDeleteAuth0User:
    """Test suite for delete_auth0_user."""

    @patch(f"{MODULE}.httpx.AsyncClient")
    @patch(f"{MODULE}.get_management_api_base_url", return_value=BASE_URL)
    @patch(f"{MODULE}.get_management_api_token", new_callable=AsyncMock)
    async def test_returns_true_on_204(
        self,
        mock_token: AsyncMock,
        mock_base_url: MagicMock,
        mock_client_cls: MagicMock,
    ) -> None:
        """A 204 No Content response means the user was deleted."""
        mock_token.return_value = FAKE_TOKEN
        client = _wire_client(mock_client_cls)
        client.delete.return_value = _StubResponse(204)

        result = await delete_auth0_user(AUTH0_SUB)

        assert result is True
        mock_token.assert_awaited_once()
        mock_base_url.assert_called_once()
        mock_client_cls.assert_called_once_with()
        client.delete.assert_awaited_once_with(
            f"{BASE_URL}/users/{AUTH0_SUB}", headers=DELETE_HEADERS
        )

    @patch(f"{MODULE}.httpx.AsyncClient")
    @patch(f"{MODULE}.get_management_api_base_url", return_value=BASE_URL)
    @patch(f"{MODULE}.get_management_api_token", new_callable=AsyncMock)
    async def test_returns_false_on_404(
        self,
        mock_token: AsyncMock,
        mock_base_url: MagicMock,
        mock_client_cls: MagicMock,
    ) -> None:
        """An unknown Auth0 user yields False instead of raising."""
        mock_token.return_value = FAKE_TOKEN
        client = _wire_client(mock_client_cls)
        client.delete.return_value = _StubResponse(404, "Not Found")

        result = await delete_auth0_user(AUTH0_SUB)

        assert result is False
        mock_base_url.assert_called_once()
        client.delete.assert_awaited_once()

    @patch(f"{MODULE}.httpx.AsyncClient")
    @patch(f"{MODULE}.get_management_api_base_url", return_value=BASE_URL)
    @patch(f"{MODULE}.get_management_api_token", new_callable=AsyncMock)
    async def test_returns_false_on_server_error(
        self,
        mock_token: AsyncMock,
        mock_base_url: MagicMock,
        mock_client_cls: MagicMock,
    ) -> None:
        """A 500 from the Management API yields False and is logged, not raised."""
        mock_token.return_value = FAKE_TOKEN
        client = _wire_client(mock_client_cls)
        client.delete.return_value = _StubResponse(500, "Internal Server Error")

        result = await delete_auth0_user(AUTH0_SUB)

        assert result is False
        mock_base_url.assert_called_once()
        client.delete.assert_awaited_once()

    @patch(f"{MODULE}.httpx.AsyncClient")
    @patch(f"{MODULE}.get_management_api_base_url", return_value=BASE_URL)
    @patch(f"{MODULE}.get_management_api_token", new_callable=AsyncMock)
    async def test_returns_false_when_token_fetch_raises(
        self,
        mock_token: AsyncMock,
        mock_base_url: MagicMock,
        mock_client_cls: MagicMock,
    ) -> None:
        """Missing Management API credentials must not bubble up to the caller."""
        mock_token.side_effect = HTTPException(
            status_code=500, detail="Auth0 Management API credentials not configured"
        )

        result = await delete_auth0_user(AUTH0_SUB)

        assert result is False
        mock_token.assert_awaited_once()
        mock_base_url.assert_not_called()
        mock_client_cls.assert_not_called()

    @patch(f"{MODULE}.httpx.AsyncClient")
    @patch(f"{MODULE}.get_management_api_base_url", return_value=BASE_URL)
    @patch(f"{MODULE}.get_management_api_token", new_callable=AsyncMock)
    async def test_returns_false_when_request_raises(
        self,
        mock_token: AsyncMock,
        mock_base_url: MagicMock,
        mock_client_cls: MagicMock,
    ) -> None:
        """A transport error during DELETE is swallowed and reported as False."""
        mock_token.return_value = FAKE_TOKEN
        client = _wire_client(mock_client_cls)
        client.delete.side_effect = httpx.ConnectError("connection refused")

        result = await delete_auth0_user(AUTH0_SUB)

        assert result is False
        mock_base_url.assert_called_once()
        client.delete.assert_awaited_once()


@pytest.mark.asyncio
class TestUpdateAuth0User:
    """Test suite for update_auth0_user."""

    @patch(f"{MODULE}.httpx.AsyncClient")
    @patch(f"{MODULE}.get_management_api_base_url", return_value=BASE_URL)
    @patch(f"{MODULE}.get_management_api_token", new_callable=AsyncMock)
    async def test_sends_name_and_nickname(
        self,
        mock_token: AsyncMock,
        mock_base_url: MagicMock,
        mock_client_cls: MagicMock,
    ) -> None:
        """name and nickname are sent as top-level Auth0 user fields."""
        mock_token.return_value = FAKE_TOKEN
        client = _wire_client(mock_client_cls)
        client_patch: AsyncMock = client.patch
        client_patch.return_value = _StubResponse(200)

        result = await update_auth0_user(
            AUTH0_SUB,
            UserProfileUpdate(name="New Name", nickname="newnick"),  # type: ignore[reportCallIssue]
        )

        assert result is True
        mock_token.assert_awaited_once()
        mock_base_url.assert_called_once()
        client_patch.assert_awaited_once_with(
            f"{BASE_URL}/users/{AUTH0_SUB}",
            json={"name": "New Name", "nickname": "newnick"},
            headers=PATCH_HEADERS,
        )
        payload = _sent_json(client_patch)
        assert set(payload.keys()) == {"name", "nickname"}

    @patch(f"{MODULE}.httpx.AsyncClient")
    @patch(f"{MODULE}.get_management_api_base_url", return_value=BASE_URL)
    @patch(f"{MODULE}.get_management_api_token", new_callable=AsyncMock)
    async def test_nests_bio_in_user_metadata(
        self,
        mock_token: AsyncMock,
        mock_base_url: MagicMock,
        mock_client_cls: MagicMock,
    ) -> None:
        """bio is not a native Auth0 field, so it goes into user_metadata."""
        mock_token.return_value = FAKE_TOKEN
        client = _wire_client(mock_client_cls)
        client_patch: AsyncMock = client.patch
        client_patch.return_value = _StubResponse(200)

        result = await update_auth0_user(
            AUTH0_SUB,
            UserProfileUpdate(bio="I organise shifts."),  # type: ignore[reportCallIssue]
        )

        assert result is True
        mock_base_url.assert_called_once()
        payload = _sent_json(client_patch)
        assert set(payload.keys()) == {"user_metadata"}
        assert payload["user_metadata"] == {"bio": "I organise shifts."}

    @patch(f"{MODULE}.httpx.AsyncClient")
    @patch(f"{MODULE}.get_management_api_base_url", return_value=BASE_URL)
    @patch(f"{MODULE}.get_management_api_token", new_callable=AsyncMock)
    async def test_sends_all_supported_fields_together(
        self,
        mock_token: AsyncMock,
        mock_base_url: MagicMock,
        mock_client_cls: MagicMock,
    ) -> None:
        """name, nickname and bio can all be part of a single PATCH payload."""
        mock_token.return_value = FAKE_TOKEN
        client = _wire_client(mock_client_cls)
        client_patch: AsyncMock = client.patch
        client_patch.return_value = _StubResponse(200)

        result = await update_auth0_user(
            AUTH0_SUB,
            UserProfileUpdate(name="New Name", nickname="newnick", bio="Hello"),  # type: ignore[reportCallIssue]
        )

        assert result is True
        mock_base_url.assert_called_once()
        payload = _sent_json(client_patch)
        assert payload == {
            "name": "New Name",
            "nickname": "newnick",
            "user_metadata": {"bio": "Hello"},
        }

    @patch(f"{MODULE}.httpx.AsyncClient")
    @patch(f"{MODULE}.get_management_api_base_url", return_value=BASE_URL)
    @patch(f"{MODULE}.get_management_api_token", new_callable=AsyncMock)
    async def test_empty_update_skips_http_call(
        self,
        mock_token: AsyncMock,
        mock_base_url: MagicMock,
        mock_client_cls: MagicMock,
    ) -> None:
        """An update with no Auth0-relevant field returns True without a request."""
        mock_token.return_value = FAKE_TOKEN

        result = await update_auth0_user(AUTH0_SUB, UserProfileUpdate())  # type: ignore[reportCallIssue]

        assert result is True
        mock_token.assert_awaited_once()
        mock_base_url.assert_not_called()
        mock_client_cls.assert_not_called()

    @patch(f"{MODULE}.httpx.AsyncClient")
    @patch(f"{MODULE}.get_management_api_base_url", return_value=BASE_URL)
    @patch(f"{MODULE}.get_management_api_token", new_callable=AsyncMock)
    async def test_local_only_fields_skip_http_call(
        self,
        mock_token: AsyncMock,
        mock_base_url: MagicMock,
        mock_client_cls: MagicMock,
    ) -> None:
        """Fields stored only in our own DB never reach Auth0."""
        mock_token.return_value = FAKE_TOKEN

        result = await update_auth0_user(
            AUTH0_SUB,
            UserProfileUpdate(  # type: ignore[reportCallIssue]
                phone_number="+49 123 456789",
                preferred_language="de",
                time_format="h24",
                theme="classic",
                show_event_switcher_in_nav=True,
            ),
        )

        assert result is True
        mock_base_url.assert_not_called()
        mock_client_cls.assert_not_called()

    @patch(f"{MODULE}.httpx.AsyncClient")
    @patch(f"{MODULE}.get_management_api_base_url", return_value=BASE_URL)
    @patch(f"{MODULE}.get_management_api_token", new_callable=AsyncMock)
    async def test_returns_false_on_non_200(
        self,
        mock_token: AsyncMock,
        mock_base_url: MagicMock,
        mock_client_cls: MagicMock,
    ) -> None:
        """A rejected PATCH yields False."""
        mock_token.return_value = FAKE_TOKEN
        client = _wire_client(mock_client_cls)
        client_patch: AsyncMock = client.patch
        client_patch.return_value = _StubResponse(400, "Bad Request")

        result = await update_auth0_user(
            AUTH0_SUB,
            UserProfileUpdate(name="New Name"),  # type: ignore[reportCallIssue]
        )

        assert result is False
        mock_base_url.assert_called_once()
        client_patch.assert_awaited_once()

    @patch(f"{MODULE}.httpx.AsyncClient")
    @patch(f"{MODULE}.get_management_api_base_url", return_value=BASE_URL)
    @patch(f"{MODULE}.get_management_api_token", new_callable=AsyncMock)
    async def test_returns_false_when_token_fetch_raises(
        self,
        mock_token: AsyncMock,
        mock_base_url: MagicMock,
        mock_client_cls: MagicMock,
    ) -> None:
        """Missing Management API credentials must not bubble up to the caller."""
        mock_token.side_effect = HTTPException(
            status_code=500, detail="Auth0 Management API credentials not configured"
        )

        result = await update_auth0_user(
            AUTH0_SUB,
            UserProfileUpdate(name="New Name"),  # type: ignore[reportCallIssue]
        )

        assert result is False
        mock_token.assert_awaited_once()
        mock_base_url.assert_not_called()
        mock_client_cls.assert_not_called()

    @patch(f"{MODULE}.httpx.AsyncClient")
    @patch(f"{MODULE}.get_management_api_base_url", return_value=BASE_URL)
    @patch(f"{MODULE}.get_management_api_token", new_callable=AsyncMock)
    async def test_returns_false_when_request_raises(
        self,
        mock_token: AsyncMock,
        mock_base_url: MagicMock,
        mock_client_cls: MagicMock,
    ) -> None:
        """A transport error during PATCH is swallowed and reported as False."""
        mock_token.return_value = FAKE_TOKEN
        client = _wire_client(mock_client_cls)
        client_patch: AsyncMock = client.patch
        client_patch.side_effect = httpx.ConnectTimeout("timed out")

        result = await update_auth0_user(
            AUTH0_SUB,
            UserProfileUpdate(nickname="nick"),  # type: ignore[reportCallIssue]
        )

        assert result is False
        mock_base_url.assert_called_once()
        client_patch.assert_awaited_once()
