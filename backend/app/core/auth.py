import httpx
from fastapi import HTTPException

from app.core.config import settings


def get_management_api_base_url() -> str:
    """Return the Auth0 Management API base URL (without trailing slash)."""
    if settings.AUTH0_MANAGEMENT_AUDIENCE:
        return settings.AUTH0_MANAGEMENT_AUDIENCE.rstrip("/")
    return f"https://{settings.AUTH0_DOMAIN}/api/v2"


async def get_management_api_token() -> str:
    """Get an Auth0 Management API token."""
    if not settings.AUTH0_CLIENT_ID or not settings.AUTH0_CLIENT_SECRET:
        raise HTTPException(
            status_code=500, detail="Auth0 Management API credentials not configured"
        )

    token_url = f"https://{settings.AUTH0_DOMAIN}/oauth/token"

    payload = {
        "client_id": settings.AUTH0_CLIENT_ID,
        "client_secret": settings.AUTH0_CLIENT_SECRET,
        "audience": f"{get_management_api_base_url()}/",
        "grant_type": "client_credentials",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, json=payload)

        if response.status_code != 200:
            raise HTTPException(
                status_code=500, detail="Failed to obtain Management API token"
            )

        token_data = response.json()
        return token_data["access_token"]
