import secrets
from urllib.parse import urlencode

import httpx

from app.config import settings

AUTHORIZATION_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
SCOPES = "openid profile w_member_social"


def generate_state() -> str:
    return secrets.token_urlsafe(32)


def get_authorization_url(state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": settings.linkedin_client_id,
        "redirect_uri": settings.linkedin_redirect_uri,
        "state": state,
        "scope": SCOPES,
    }
    return f"{AUTHORIZATION_URL}?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> dict:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": settings.linkedin_client_id,
        "client_secret": settings.linkedin_client_secret,
        "redirect_uri": settings.linkedin_redirect_uri,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(TOKEN_URL, data=data)
        resp.raise_for_status()
        return resp.json()
