from urllib.parse import quote

import httpx

from app.config import settings


class LinkedInClient:
    BASE_URL = "https://api.linkedin.com"

    def __init__(self, access_token: str):
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": settings.linkedin_api_version,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }

    async def get_profile(self) -> dict:
        """Get the authenticated member's profile (sub = member ID)."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/v2/userinfo", headers=self.headers
            )
            resp.raise_for_status()
            return resp.json()

    async def get_member_urn(self) -> str:
        profile = await self.get_profile()
        return f"urn:li:person:{profile['sub']}"

    async def get_post(self, post_urn: str) -> dict:
        """Fetch a post by its URN."""
        encoded = quote(post_urn, safe="")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/rest/posts/{encoded}", headers=self.headers
            )
            resp.raise_for_status()
            return resp.json()

    async def post_comment(
        self, post_urn: str, actor_urn: str, text: str
    ) -> dict:
        """Post a comment on a LinkedIn post."""
        encoded = quote(post_urn, safe="")
        payload = {
            "actor": actor_urn,
            "object": post_urn,
            "message": {"text": text},
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/rest/socialActions/{encoded}/comments",
                headers=self.headers,
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()
