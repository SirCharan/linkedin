"""LinkedIn Voyager API client for posting comments.

Uses the linkedin_api package (unofficial) which authenticates via
LinkedIn's internal Voyager API — the same API the website uses.
"""

import json
import logging
import time
from functools import lru_cache

from linkedin_api import Linkedin

from app.config import settings

logger = logging.getLogger(__name__)

_client: Linkedin | None = None
_client_ts: float = 0


def _no_evade():
    """Skip the default 2-5s delay for faster operation."""
    pass


def get_voyager_client() -> Linkedin:
    """Return a cached Voyager client, re-authenticating every 6 hours."""
    global _client, _client_ts
    if _client and (time.time() - _client_ts < 21600):
        return _client

    if not settings.linkedin_email or not settings.linkedin_password:
        raise RuntimeError(
            "LINKEDIN_EMAIL and LINKEDIN_PASSWORD must be set in .env"
        )

    logger.info("Authenticating with LinkedIn Voyager API...")
    _client = Linkedin(settings.linkedin_email, settings.linkedin_password)
    _client_ts = time.time()
    logger.info("Voyager authentication successful")
    return _client


def post_comment(activity_id: str, comment_text: str) -> dict:
    """Post a comment on a LinkedIn post via the Voyager API.

    :param activity_id: The numeric activity ID (e.g. '7130492810985676800')
    :param comment_text: The comment text to post
    :return: dict with success status and response details
    """
    api = get_voyager_client()

    # The Voyager API endpoint for creating comments
    payload = json.dumps({
        "commentary": {
            "text": comment_text,
            "attributesV2": [],
        },
        "parentUrn": f"urn:li:activity:{activity_id}",
        "$type": "com.linkedin.voyager.feed.shared.SocialComment",
    })

    res = api._post(
        "/feed/comments",
        evade=_no_evade,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    if res.status_code in (200, 201):
        try:
            return {"success": True, "data": res.json()}
        except Exception:
            return {"success": True, "data": res.text}

    # If that format didn't work, try alternative payload format
    payload2 = json.dumps({
        "threadUrn": f"urn:li:fsd_update:(urn:li:activity:{activity_id},FEED_DETAIL,EMPTY,DEFAULT,false)",
        "commentary": {
            "text": comment_text,
            "attributesV2": [],
        },
    })

    res2 = api._post(
        "/feed/comments",
        evade=_no_evade,
        data=payload2,
        headers={"Content-Type": "application/json"},
    )

    if res2.status_code in (200, 201):
        try:
            return {"success": True, "data": res2.json()}
        except Exception:
            return {"success": True, "data": res2.text}

    # Try the dash-style endpoint as last resort
    params = {"action": "create"}
    payload3 = json.dumps({
        "threadUrn": f"urn:li:activity:{activity_id}",
        "text": comment_text,
    })

    res3 = api._post(
        "/voyagerSocialDashComments",
        evade=_no_evade,
        params=params,
        data=payload3,
        headers={"Content-Type": "application/json"},
    )

    if res3.status_code in (200, 201):
        try:
            return {"success": True, "data": res3.json()}
        except Exception:
            return {"success": True, "data": res3.text}

    # All attempts failed — return the first error for debugging
    error_detail = f"Status {res.status_code}"
    try:
        error_detail = res.json()
    except Exception:
        error_detail = res.text[:500]
    raise RuntimeError(
        f"Comment posting failed. Status: {res.status_code}, "
        f"Response: {error_detail}"
    )


def extract_activity_id(urn: str) -> str:
    """Extract numeric activity ID from a URN like 'urn:li:activity:123'."""
    if ":" in urn:
        return urn.split(":")[-1]
    return urn
