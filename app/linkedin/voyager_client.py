"""LinkedIn comment poster using Playwright browser automation.

Uses a persistent browser context so you only need to log in once.
The session persists across restarts via a local browser profile.
"""

import logging
import os
import time

from playwright.sync_api import sync_playwright, BrowserContext, Playwright

logger = logging.getLogger(__name__)

_pw: Playwright | None = None
_context: BrowserContext | None = None
_profile_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".linkedin-browser")


def _get_browser_context() -> BrowserContext:
    """Return a persistent Chrome context (launches once, reuses after)."""
    global _pw, _context
    if _context:
        return _context

    profile = os.path.abspath(_profile_dir)
    logger.info(f"Launching Chrome with profile at {profile}")
    _pw = sync_playwright().start()
    _context = _pw.chromium.launch_persistent_context(
        user_data_dir=profile,
        headless=False,
        channel="chrome",
        args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1280, "height": 900},
    )
    logger.info("Browser context ready")
    return _context


def _ensure_logged_in(page) -> bool:
    """Navigate to LinkedIn feed and check if we're logged in."""
    page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
    # If redirected to login, we're not authenticated
    if "/login" in page.url or "/uas/" in page.url or "/checkpoint" in page.url:
        logger.warning(
            "Not logged in to LinkedIn. Please log in via the browser window "
            "that just opened, then try again."
        )
        # Wait up to 120s for user to log in manually
        for _ in range(60):
            time.sleep(2)
            if "/feed" in page.url and "/login" not in page.url:
                logger.info("Login detected!")
                return True
        return False
    return True


def post_comment(activity_id: str, comment_text: str) -> dict:
    """Post a comment on a LinkedIn post via browser automation.

    :param activity_id: The numeric activity ID (e.g. '7130492810985676800')
    :param comment_text: The comment text to post
    :return: dict with success status
    """
    ctx = _get_browser_context()
    page = ctx.new_page()

    try:
        # Check login
        if not _ensure_logged_in(page):
            raise RuntimeError(
                "Not logged in to LinkedIn. Please log in via the browser "
                "window and retry."
            )

        # Navigate to the post
        post_url = f"https://www.linkedin.com/feed/update/urn:li:activity:{activity_id}/"
        logger.info(f"Navigating to {post_url}")
        page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        # Click the comment button to open the comment box
        comment_btn = page.locator(
            "button.comment-button, "
            "button[aria-label*='Comment'], "
            "button[aria-label*='comment'], "
            "span.comment-button"
        ).first
        if comment_btn.is_visible():
            comment_btn.click()
            page.wait_for_timeout(1000)

        # Find and fill the comment text box
        comment_box = page.locator(
            "div.ql-editor[data-placeholder*='Add a comment'], "
            "div.ql-editor[contenteditable='true'], "
            "div[role='textbox'][aria-label*='comment' i], "
            "div[role='textbox'][aria-label*='Add a comment' i], "
            "div.comments-comment-box__form div[contenteditable='true']"
        ).first

        comment_box.wait_for(state="visible", timeout=10000)
        comment_box.click()
        page.wait_for_timeout(500)

        # Type the comment
        comment_box.fill(comment_text)
        page.wait_for_timeout(500)

        # Click the submit/post button
        submit_btn = page.locator(
            "button.comments-comment-box__submit-button, "
            "button[aria-label*='Post comment'], "
            "button[type='submit'][class*='comment']"
        ).first

        if not submit_btn.is_visible():
            # Fallback: look for any enabled submit-like button near the comment box
            submit_btn = page.locator(
                "form.comments-comment-box__form button[type='submit'], "
                "button.artdeco-button--primary"
            ).last

        submit_btn.wait_for(state="visible", timeout=5000)
        submit_btn.click()

        # Wait for the comment to be posted
        page.wait_for_timeout(3000)

        logger.info(f"Comment posted on activity {activity_id}")
        return {"success": True, "data": "Comment posted via browser"}

    except Exception as e:
        logger.error(f"Failed to post comment: {e}")
        # Take a screenshot for debugging
        try:
            page.screenshot(path=f".linkedin-browser/error-{activity_id}.png")
            logger.info(f"Error screenshot saved to .linkedin-browser/error-{activity_id}.png")
        except Exception:
            pass
        raise RuntimeError(f"Browser comment posting failed: {e}")
    finally:
        page.close()


def extract_activity_id(urn: str) -> str:
    """Extract numeric activity ID from a URN like 'urn:li:activity:123'."""
    if ":" in urn:
        return urn.split(":")[-1]
    return urn
