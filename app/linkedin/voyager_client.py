"""LinkedIn Voyager API client for posting comments.

Uses the linkedin_api package (unofficial) with browser cookie authentication.
"""

import json
import logging
import time

from linkedin_api import Linkedin
from requests.cookies import RequestsCookieJar

from app.config import settings

logger = logging.getLogger(__name__)

_client: Linkedin | None = None
_client_ts: float = 0


def _no_evade():
    """Skip the default 2-5s delay for faster operation."""
    pass


def get_voyager_client() -> Linkedin:
    """Return a cached Voyager client using browser cookies."""
    global _client, _client_ts
    if _client and (time.time() - _client_ts < 21600):
        return _client

    li_at = settings.linkedin_li_at
    jsessionid = settings.linkedin_jsessionid
    if not li_at or not jsessionid:
        raise RuntimeError(
            "LINKEDIN_LI_AT and LINKEDIN_JSESSIONID must be set in .env. "
            "Get these from your browser's LinkedIn cookies."
        )

    logger.info("Setting up Voyager client with browser cookies...")
    cookies = RequestsCookieJar()
    cookies.set("li_at", li_at, domain=".linkedin.com", path="/")
    cookies.set("JSESSIONID", f'"{jsessionid}"', domain=".linkedin.com", path="/")

    # Create client without authenticating, then inject cookies
    api = Linkedin("", "", authenticate=False)
    api.client._set_session_cookies(cookies)

    _client = api
    _client_ts = time.time()
    logger.info("Voyager client ready")
    return _client


def post_comment(activity_id: str, comment_text: str) -> dict:
    """Post a comment on a LinkedIn post via the Voyager API.

    :param activity_id: The numeric activity ID (e.g. '7130492810985676800')
    :param comment_text: The comment text to post
    :return: dict with success status and response details
    """
    api = get_voyager_client()

    # Attempt 1: /feed/comments with parentUrn
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

    logger.info(f"Attempt 1 (/feed/comments parentUrn): {res.status_code}")
    if res.status_code in (200, 201):
        return _parse_response(res)

    # Attempt 2: /feed/comments with threadUrn (fsd_update format)
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

    logger.info(f"Attempt 2 (/feed/comments threadUrn): {res2.status_code}")
    if res2.status_code in (200, 201):
        return _parse_response(res2)

    # Attempt 3: /voyagerSocialDashComments
    payload3 = json.dumps({
        "threadUrn": f"urn:li:activity:{activity_id}",
        "text": comment_text,
    })

    res3 = api._post(
        "/voyagerSocialDashComments",
        evade=_no_evade,
        params={"action": "create"},
        data=payload3,
        headers={"Content-Type": "application/json"},
    )

    logger.info(f"Attempt 3 (/voyagerSocialDashComments): {res3.status_code}")
    if res3.status_code in (200, 201):
        return _parse_response(res3)

    # All attempts failed — collect diagnostics
    errors = []
    for i, r in enumerate([res, res2, res3], 1):
        try:
            body = r.json()
        except Exception:
            body = r.text[:300]
        errors.append(f"Attempt {i}: {r.status_code} -> {body}")

    error_msg = " | ".join(errors)
    raise RuntimeError(f"All comment posting attempts failed. {error_msg}")


def _parse_response(res) -> dict:
    try:
        return {"success": True, "data": res.json()}
    except Exception:
        return {"success": True, "data": res.text}


def extract_activity_id(urn: str) -> str:
    """Extract numeric activity ID from a URN like 'urn:li:activity:123'."""
    if ":" in urn:
        return urn.split(":")[-1]
    return urn
