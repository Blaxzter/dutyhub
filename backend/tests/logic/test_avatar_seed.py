"""Unit tests for the background avatar-seeding task.

``seed_avatar_from_url`` runs after the request session is closed and opens its
own database session, so every collaborator it imports by name
(``fetch_remote_avatar``, ``normalize_avatar``, ``async_session`` and the two
CRUD singletons) is patched inside ``app.logic.avatar_seed``. No database is
touched and no network request is made.
"""

import hashlib
import io
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from app.logic.avatar import AvatarProcessingError
from app.logic.avatar_seed import seed_avatar_from_url
from app.models.user import User

MODULE = "app.logic.avatar_seed"
PICTURE_URL = "https://cdn.example.test/picture.png"
RAW_BYTES = b"raw-remote-avatar-bytes"
WEBP_BYTES = b"normalised-webp-bytes"
CONTENT_TYPE = "image/webp"
ETAG = "0" * 64


def _wire_session(mock_async_session: MagicMock) -> MagicMock:
    """Make ``async with async_session() as db`` yield an inspectable mock."""
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=db)
    context_manager.__aexit__ = AsyncMock(return_value=False)
    mock_async_session.return_value = context_manager

    return db


def _user(avatar_etag: str | None = None) -> User:
    return User(
        auth0_sub="auth0|seed-target",
        email="seed@example.test",
        name="Seed Target",
        avatar_etag=avatar_etag,
    )


@pytest.mark.asyncio
class TestSeedAvatarFromUrl:
    """Test suite for seed_avatar_from_url."""

    @patch(f"{MODULE}.async_session")
    @patch(f"{MODULE}.normalize_avatar")
    @patch(f"{MODULE}.fetch_remote_avatar", new_callable=AsyncMock)
    async def test_stops_when_the_download_fails(
        self,
        mock_fetch: AsyncMock,
        mock_normalize: MagicMock,
        mock_async_session: MagicMock,
    ) -> None:
        """A failed download ends the task before any work is done."""
        mock_fetch.return_value = None

        await seed_avatar_from_url(uuid.uuid4(), PICTURE_URL)

        mock_fetch.assert_awaited_once_with(PICTURE_URL)
        mock_normalize.assert_not_called()
        mock_async_session.assert_not_called()

    @patch(f"{MODULE}.async_session")
    @patch(f"{MODULE}.normalize_avatar")
    @patch(f"{MODULE}.fetch_remote_avatar", new_callable=AsyncMock)
    async def test_stops_when_the_image_is_rejected(
        self,
        mock_fetch: AsyncMock,
        mock_normalize: MagicMock,
        mock_async_session: MagicMock,
    ) -> None:
        """An unusable remote image is logged and dropped, never stored."""
        mock_fetch.return_value = RAW_BYTES
        mock_normalize.side_effect = AvatarProcessingError("File is not a valid image")

        await seed_avatar_from_url(uuid.uuid4(), PICTURE_URL)

        mock_normalize.assert_called_once_with(RAW_BYTES)
        mock_async_session.assert_not_called()

    @patch(f"{MODULE}.crud_avatar.upsert", new_callable=AsyncMock)
    @patch(f"{MODULE}.crud_user.get", new_callable=AsyncMock)
    @patch(f"{MODULE}.async_session")
    @patch(f"{MODULE}.normalize_avatar")
    @patch(f"{MODULE}.fetch_remote_avatar", new_callable=AsyncMock)
    async def test_stops_when_the_user_no_longer_exists(
        self,
        mock_fetch: AsyncMock,
        mock_normalize: MagicMock,
        mock_async_session: MagicMock,
        mock_get_user: AsyncMock,
        mock_upsert: AsyncMock,
    ) -> None:
        """A user deleted between login and task run is not resurrected."""
        mock_fetch.return_value = RAW_BYTES
        mock_normalize.return_value = (WEBP_BYTES, CONTENT_TYPE, ETAG)
        db = _wire_session(mock_async_session)
        mock_get_user.return_value = None
        user_id = uuid.uuid4()

        await seed_avatar_from_url(user_id, PICTURE_URL)

        mock_get_user.assert_awaited_once_with(db, id=user_id)
        mock_upsert.assert_not_awaited()
        db.commit.assert_not_awaited()

    @patch(f"{MODULE}.crud_avatar.upsert", new_callable=AsyncMock)
    @patch(f"{MODULE}.crud_user.get", new_callable=AsyncMock)
    @patch(f"{MODULE}.async_session")
    @patch(f"{MODULE}.normalize_avatar")
    @patch(f"{MODULE}.fetch_remote_avatar", new_callable=AsyncMock)
    async def test_does_not_clobber_an_existing_avatar(
        self,
        mock_fetch: AsyncMock,
        mock_normalize: MagicMock,
        mock_async_session: MagicMock,
        mock_get_user: AsyncMock,
        mock_upsert: AsyncMock,
    ) -> None:
        """If the user uploaded an avatar first, that upload wins."""
        mock_fetch.return_value = RAW_BYTES
        mock_normalize.return_value = (WEBP_BYTES, CONTENT_TYPE, ETAG)
        db = _wire_session(mock_async_session)
        existing = _user(avatar_etag="an-existing-etag")
        mock_get_user.return_value = existing

        await seed_avatar_from_url(existing.id, PICTURE_URL)

        mock_upsert.assert_not_awaited()
        db.commit.assert_not_awaited()
        assert existing.avatar_etag == "an-existing-etag"

    @patch(f"{MODULE}.crud_avatar.upsert", new_callable=AsyncMock)
    @patch(f"{MODULE}.crud_user.get", new_callable=AsyncMock)
    @patch(f"{MODULE}.async_session")
    @patch(f"{MODULE}.normalize_avatar")
    @patch(f"{MODULE}.fetch_remote_avatar", new_callable=AsyncMock)
    async def test_stores_the_avatar_and_stamps_the_etag(
        self,
        mock_fetch: AsyncMock,
        mock_normalize: MagicMock,
        mock_async_session: MagicMock,
        mock_get_user: AsyncMock,
        mock_upsert: AsyncMock,
    ) -> None:
        """Happy path: download, normalise, upsert, stamp the etag, commit."""
        mock_fetch.return_value = RAW_BYTES
        mock_normalize.return_value = (WEBP_BYTES, CONTENT_TYPE, ETAG)
        db = _wire_session(mock_async_session)
        user = _user()
        mock_get_user.return_value = user

        await seed_avatar_from_url(user.id, PICTURE_URL)

        mock_fetch.assert_awaited_once_with(PICTURE_URL)
        mock_normalize.assert_called_once_with(RAW_BYTES)
        mock_upsert.assert_awaited_once_with(
            db,
            user_id=user.id,
            data=WEBP_BYTES,
            content_type=CONTENT_TYPE,
            etag=ETAG,
        )
        assert user.avatar_etag == ETAG
        db.add.assert_called_once_with(user)
        db.commit.assert_awaited_once()

    @patch(f"{MODULE}.logger")
    @patch(f"{MODULE}.crud_avatar.upsert", new_callable=AsyncMock)
    @patch(f"{MODULE}.crud_user.get", new_callable=AsyncMock)
    @patch(f"{MODULE}.async_session")
    @patch(f"{MODULE}.normalize_avatar")
    @patch(f"{MODULE}.fetch_remote_avatar", new_callable=AsyncMock)
    async def test_database_failures_are_swallowed(
        self,
        mock_fetch: AsyncMock,
        mock_normalize: MagicMock,
        mock_async_session: MagicMock,
        mock_get_user: AsyncMock,
        mock_upsert: AsyncMock,
        mock_logger: MagicMock,
    ) -> None:
        """A broken session must not bubble out of a background task."""
        mock_fetch.return_value = RAW_BYTES
        mock_normalize.return_value = (WEBP_BYTES, CONTENT_TYPE, ETAG)
        db = _wire_session(mock_async_session)
        user = _user()
        mock_get_user.return_value = user
        mock_upsert.side_effect = RuntimeError("connection reset")

        await seed_avatar_from_url(user.id, PICTURE_URL)

        db.commit.assert_not_awaited()
        mock_logger.exception.assert_called_once()

    @patch(f"{MODULE}.crud_avatar.upsert", new_callable=AsyncMock)
    @patch(f"{MODULE}.crud_user.get", new_callable=AsyncMock)
    @patch(f"{MODULE}.async_session")
    @patch(f"{MODULE}.fetch_remote_avatar", new_callable=AsyncMock)
    async def test_end_to_end_with_a_real_generated_image(
        self,
        mock_fetch: AsyncMock,
        mock_async_session: MagicMock,
        mock_get_user: AsyncMock,
        mock_upsert: AsyncMock,
    ) -> None:
        """Only the network and the database are faked; Pillow runs for real."""
        buffer = io.BytesIO()
        Image.new("RGB", (300, 150), (20, 140, 90)).save(buffer, format="PNG")
        mock_fetch.return_value = buffer.getvalue()

        db = _wire_session(mock_async_session)
        user = _user()
        mock_get_user.return_value = user

        await seed_avatar_from_url(user.id, PICTURE_URL)

        assert mock_upsert.await_args is not None
        stored: dict[str, Any] = dict(mock_upsert.await_args.kwargs)
        assert stored["content_type"] == "image/webp"
        assert stored["etag"] == hashlib.sha256(stored["data"]).hexdigest()
        assert user.avatar_etag == stored["etag"]
        with Image.open(io.BytesIO(stored["data"])) as stored_img:
            assert stored_img.format == "WEBP"
            assert stored_img.size == (256, 128)
        db.commit.assert_awaited_once()
