import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ai.reply_generator import ReplyGenerator
from app.auth.token_store import token_store
from app.linkedin.client import LinkedInClient
from app.linkedin.url_parser import extract_activity_urn
from app.linkedin.voyager_client import extract_activity_id, post_comment as voyager_post_comment

router = APIRouter(prefix="/api", tags=["comments"])
reply_gen = ReplyGenerator()
_executor = ThreadPoolExecutor(max_workers=2)


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
    try:
        suggestions = await reply_gen.generate_replies(
            post_text=body.post_text,
            num_suggestions=body.num_suggestions,
            tone=body.tone,
            user_context=body.user_context,
        )
        return {"suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reply generation failed: {e}")


@router.post("/post-comment")
async def post_comment(body: PostCommentRequest):
    activity_id = extract_activity_id(body.post_urn)
    try:
        # Run synchronous linkedin_api in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor, voyager_post_comment, activity_id, body.comment_text
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"success": True, "result": result}
