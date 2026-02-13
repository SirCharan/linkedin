from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ai.reply_generator import ReplyGenerator
from app.auth.token_store import token_store
from app.linkedin.client import LinkedInClient
from app.linkedin.url_parser import extract_activity_urn

router = APIRouter(prefix="/api", tags=["comments"])
reply_gen = ReplyGenerator()


def _get_client() -> LinkedInClient:
    token = token_store.get_valid_token()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return LinkedInClient(token)


class AnalyzeRequest(BaseModel):
    url: str


class GenerateRequest(BaseModel):
    post_text: str
    post_urn: str
    tone: str = "professional"
    user_context: Optional[str] = None
    num_suggestions: int = 3


class PostCommentRequest(BaseModel):
    post_urn: str
    comment_text: str


@router.post("/analyze-post")
async def analyze_post(body: AnalyzeRequest):
    try:
        urn = extract_activity_urn(body.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    client = _get_client()
    try:
        post = await client.get_post(urn)
        text = post.get("commentary", post.get("specificContent", {}).get("com.linkedin.ugc.ShareContent", {}).get("shareCommentary", {}).get("text", ""))
        author = post.get("author", "")
        return {"urn": urn, "text": text, "author": author}
    except Exception:
        # If API can't fetch the post, return URN so user can paste text manually
        return {"urn": urn, "text": "", "author": "", "manual": True}


@router.post("/generate-replies")
async def generate_replies(body: GenerateRequest):
    if not body.post_text.strip():
        raise HTTPException(status_code=400, detail="Post text is required")
    suggestions = await reply_gen.generate_replies(
        post_text=body.post_text,
        num_suggestions=body.num_suggestions,
        tone=body.tone,
        user_context=body.user_context,
    )
    return {"suggestions": suggestions}


@router.post("/post-comment")
async def post_comment(body: PostCommentRequest):
    client = _get_client()
    data = token_store.load_token()
    if not data or not data.get("member_urn"):
        raise HTTPException(status_code=401, detail="No member URN found")

    result = await client.post_comment(
        post_urn=body.post_urn,
        actor_urn=data["member_urn"],
        text=body.comment_text,
    )
    return {"success": True, "result": result}
