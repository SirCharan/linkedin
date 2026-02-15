import asyncio
from dataclasses import dataclass
from typing import Optional

import httpx
from bs4 import BeautifulSoup


@dataclass
class PostContent:
    url: str
    text: str
    author: str


async def scrape_post_text(url: str) -> Optional[PostContent]:
    """Extract post text from a public LinkedIn post page using meta tags."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Try og:description first (contains post text)
        text = ""
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            text = og_desc["content"]

        # Try article body as fallback
        if not text:
            article = soup.find("meta", {"name": "description"})
            if article and article.get("content"):
                text = article["content"]

        # Author from og:title or page title
        author = ""
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            author = og_title["content"].split(" on LinkedIn")[0].strip()

        # Skip generic LinkedIn pages that require login
        generic = ["manage your professional identity", "500 million", "sign up"]
        if text and not any(g in text.lower() for g in generic):
            return PostContent(url=url, text=text, author=author)
    except Exception:
        pass
    return None


async def scrape_multiple(urls: list[str]) -> list[PostContent]:
    """Scrape text from multiple LinkedIn post URLs concurrently."""
    tasks = [scrape_post_text(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]
