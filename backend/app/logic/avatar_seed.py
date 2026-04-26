"""Background-task helper that seeds a local avatar from a remote URL.

Runs after the request session is closed, so it opens its own session
(same pattern as ``app.logic.notifications.triggers``).
"""

import logging
import uuid

from app.core.db import async_session
from app.crud.user import user as crud_user
from app.crud.user_avatar import user_avatar as crud_avatar
from app.logic.avatar import (
    AvatarProcessingError,
    fetch_remote_avatar,
    normalize_avatar,
)

logger = logging.getLogger(__name__)


async def seed_avatar_from_url(user_id: uuid.UUID, picture_url: str) -> None:
    """Best-effort: download an external avatar and store it locally.

    Skips if the user already has an avatar (avoids clobbering user uploads
    when this task races with one).
    """
    raw = await fetch_remote_avatar(picture_url)
    if raw is None:
        return

    try:
        data, content_type, etag = normalize_avatar(raw)
    except AvatarProcessingError:
        logger.debug("Remote avatar at %s failed validation", picture_url)
        return

    try:
        async with async_session() as db:
            user = await crud_user.get(db, id=user_id)
            if user is None:
                return
            if user.avatar_etag is not None:
                return  # user already has an avatar; don't clobber.
            await crud_avatar.upsert(
                db,
                user_id=user_id,
                data=data,
                content_type=content_type,
                etag=etag,
            )
            user.avatar_etag = etag
            db.add(user)
            await db.commit()
    except Exception:
        logger.exception("Failed to seed avatar for user %s", user_id)
