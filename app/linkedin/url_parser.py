import re


def extract_activity_urn(url: str) -> str:
    """Extract a LinkedIn activity URN from various post URL formats."""
    patterns = [
        r"urn:li:activity:(\d+)",
        r"urn:li:ugcPost:(\d+)",
        r"activity-(\d+)",
        r"-(\d{19,20})-",          # /posts/user_slug-7428164893930876929-XOqa
        r"/posts/[^?]*-(\d{19,20})",  # fallback without trailing dash
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return f"urn:li:activity:{match.group(1)}"
    raise ValueError(f"Could not extract activity URN from URL: {url}")
