from typing import Optional

from pydantic import BaseModel


class LinkedInPost(BaseModel):
    urn: str
    author: str = ""
    text: str = ""
    visibility: str = ""


class CommentRequest(BaseModel):
    post_urn: str
    actor_urn: str
    text: str


class TokenData(BaseModel):
    access_token: str
    expires_at: float
    refresh_token: Optional[str] = None
    member_urn: Optional[str] = None
