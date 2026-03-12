import logging
from typing import Any

import httpx

from app.core.auth import get_management_api_token
from app.core.config import settings
from app.schemas.users import UserProfileUpdate

logger = logging.getLogger(__name__)


async def delete_auth0_user(auth0_sub: str) -> bool:
    """Delete a user from Auth0 using the Management API."""
    try:
        token = await get_management_api_token()
        url = f"https://{settings.AUTH0_DOMAIN}/api/v2/users/{auth0_sub}"
        headers = {
            "Authorization": f"Bearer {token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.delete(url, headers=headers)
            if response.status_code == 204:
                return True
            logger.error(
                "Failed to delete Auth0 user %s: %s %s",
                auth0_sub,
                response.status_code,
                response.text,
            )
            return False

    except Exception:
        logger.exception("Error deleting Auth0 user %s", auth0_sub)
        return False


async def update_auth0_user(user_id: str, update_data: UserProfileUpdate) -> bool:
    """Update user profile in Auth0 using Management API."""
    try:
        token = await get_management_api_token()

        # Prepare user update payload
        user_data: dict[str, Any] = {}
        if update_data.name is not None:
            user_data["name"] = update_data.name
        if update_data.nickname is not None:
            user_data["nickname"] = update_data.nickname
        if update_data.picture is not None:
            user_data["picture"] = str(update_data.picture)

        # Add bio to user_metadata
        if update_data.bio is not None:
            user_data["user_metadata"] = {"bio": update_data.bio}

        if not user_data:
            return True

        # Update user via Management API
        url = f"https://{settings.AUTH0_DOMAIN}/api/v2/users/{user_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.patch(url, json=user_data, headers=headers)
            return response.status_code == 200

    except Exception as e:
        print(f"Error updating Auth0 user: {e}")
        return False
