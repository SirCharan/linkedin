from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ai.reply_generator import ReplyGenerator
from app.auth.token_store import token_store
from app.discovery.scraper import scrape_multiple
from app.discovery.search import find_linkedin_posts
from app.linkedin.client import LinkedInClient
from app.linkedin.url_parser import extract_activity_urn

router = APIRouter(prefix="/api/auto", tags=["auto"])
reply_gen = ReplyGenerator()


class DiscoverRequest(BaseModel):
    topic: str = "crypto OR cryptocurrency OR stock market"
    max_posts: int = 8


class AutoReplyRequest(BaseModel):
    post_url: str
    post_text: str
    tone: str = "professional"
    user_context: Optional[str] = None


class BatchReplyRequest(BaseModel):
    topic: str = "crypto OR cryptocurrency OR stock market"
    tone: str = "professional"
    user_context: Optional[str] = None
    max_posts: int = 5
    auto_post: bool = False


def _get_client() -> LinkedInClient:
    token = token_store.get_valid_token()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return LinkedInClient(token)


@router.post("/discover")
async def discover_posts(body: DiscoverRequest):
    """Find trending LinkedIn posts on a topic."""
    try:
        results = await find_linkedin_posts(
            topic=body.topic, max_results=body.max_posts
        )
    except Exception:
        return {"posts": [], "message": "Search temporarily unavailable. Try again in a minute."}

    if not results:
        return {"posts": [], "message": "No posts found"}

    urls = [r.url for r in results]
    scraped = await scrape_multiple(urls)

    posts = []
    for p in scraped:
        try:
            urn = extract_activity_urn(p.url)
        except ValueError:
            continue
        posts.append({
            "url": p.url,
            "urn": urn,
            "text": p.text,
            "author": p.author,
        })
    return {"posts": posts}


@router.post("/generate-and-post")
async def generate_and_post(body: AutoReplyRequest):
    """Generate a reply for a single post and post it."""
    try:
        urn = extract_activity_urn(body.post_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    replies = await reply_gen.generate_replies(
        post_text=body.post_text,
        num_suggestions=1,
        tone=body.tone,
        user_context=body.user_context,
    )
    comment = replies[0]

    client = _get_client()
    data = token_store.load_token()
    if not data or not data.get("member_urn"):
        raise HTTPException(status_code=401, detail="No member URN")

    try:
        result = await client.post_comment(
            post_urn=urn, actor_urn=data["member_urn"], text=comment
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LinkedIn API error: {e}")
    return {"success": True, "comment": comment, "result": result}


@router.post("/batch")
async def batch_discover_and_reply(body: BatchReplyRequest):
    """Full pipeline: discover posts, generate replies, optionally auto-post."""
    # 1. Discover posts
    results = await find_linkedin_posts(
        topic=body.topic, max_results=body.max_posts
    )
    if not results:
        return {"items": [], "message": "No posts found"}

    urls = [r.url for r in results]
    scraped = await scrape_multiple(urls)

    items = []
    for p in scraped:
        try:
            urn = extract_activity_urn(p.url)
        except ValueError:
            continue

        # 2. Generate reply
        replies = await reply_gen.generate_replies(
            post_text=p.text,
            num_suggestions=1,
            tone=body.tone,
            user_context=body.user_context,
        )
        comment = replies[0]

        item = {
            "url": p.url,
            "urn": urn,
            "author": p.author,
            "post_text": p.text[:200],
            "generated_reply": comment,
            "posted": False,
        }

        # 3. Auto-post if enabled
        if body.auto_post:
            try:
                client = _get_client()
                data = token_store.load_token()
                await client.post_comment(
                    post_urn=urn, actor_urn=data["member_urn"], text=comment
                )
                item["posted"] = True
            except Exception as e:
                item["error"] = str(e)

        items.append(item)

    return {"items": items}
