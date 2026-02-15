import asyncio
import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

CACHE_DIR = Path.home() / ".linkedin-tool" / "cache"
CACHE_TTL = 1800  # 30 minutes


@dataclass
class PostResult:
    url: str
    title: str
    snippet: str


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

POST_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/posts/"
    r"([a-zA-Z0-9_.%-]+_[a-zA-Z0-9_%-]+-activity-(\d+)-[a-zA-Z0-9]+)"
)


def _extract_posts_from_html(html: str) -> list[PostResult]:
    """Extract LinkedIn post URLs from search result HTML."""
    soup = BeautifulSoup(html, "html.parser")
    seen_ids = set()
    posts = []
    for match in POST_URL_RE.finditer(html):
        path = match.group(1)
        activity_id = match.group(2)
        if activity_id in seen_ids:
            continue
        seen_ids.add(activity_id)

        full_url = f"https://www.linkedin.com/posts/{path}"

        title = ""
        snippet = ""
        link = soup.find("a", href=re.compile(re.escape(activity_id)))
        if link:
            title = link.get_text(strip=True)
            parent = link.find_parent(["div", "li", "article"])
            if parent:
                snippet = parent.get_text(" ", strip=True)[:300]

        posts.append(PostResult(url=full_url, title=title, snippet=snippet))
    return posts


async def _search_brave(query: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        resp = await client.get(
            "https://search.brave.com/search",
            params={"q": query, "source": "web"},
            headers=HEADERS,
        )
        resp.raise_for_status()
        return resp.text


async def _search_startpage(query: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        resp = await client.post(
            "https://www.startpage.com/sp/search",
            data={"query": query, "cat": "web"},
            headers=HEADERS,
        )
        resp.raise_for_status()
        return resp.text


async def _search_yahoo(query: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        resp = await client.get(
            "https://search.yahoo.com/search",
            params={"p": query},
            headers=HEADERS,
        )
        resp.raise_for_status()
        return resp.text


async def _search_ecosia(query: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        resp = await client.get(
            "https://www.ecosia.org/search",
            params={"q": query, "method": "index"},
            headers=HEADERS,
        )
        resp.raise_for_status()
        return resp.text


def _cache_key(query: str) -> Path:
    h = hashlib.md5(query.encode()).hexdigest()[:12]
    return CACHE_DIR / f"{h}.json"


def _load_cache(query: str) -> list[PostResult] | None:
    path = _cache_key(query)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    if time.time() - data.get("ts", 0) > CACHE_TTL:
        return None
    return [PostResult(**p) for p in data.get("posts", [])]


def _save_cache(query: str, posts: list[PostResult]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = {"ts": time.time(), "posts": [{"url": p.url, "title": p.title, "snippet": p.snippet} for p in posts]}
    _cache_key(query).write_text(json.dumps(data))


async def find_linkedin_posts(
    topic: str = "crypto OR cryptocurrency OR stock market",
    max_results: int = 10,
) -> list[PostResult]:
    """Search for recent LinkedIn posts using multiple search engines with caching."""
    query = f"site:linkedin.com/posts {topic}"

    # Check cache first
    cached = _load_cache(query)
    if cached:
        return cached[:max_results]

    engines = [
        _search_brave,
        _search_yahoo,
        _search_ecosia,
        _search_startpage,
    ]

    for search_fn in engines:
        try:
            html = await search_fn(query)
            posts = _extract_posts_from_html(html)
            if posts:
                _save_cache(query, posts)
                return posts[:max_results]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                await asyncio.sleep(2)
                continue
        except Exception:
            continue

    return []
