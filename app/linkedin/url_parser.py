import re


def extract_activity_urn(url: str) -> str:
    """Extract a LinkedIn activity URN from various post URL formats."""
    patterns = [
        r"urn:li:activity:(\d+)",
        r"urn:li:ugcPost:(\d+)",
        r"activity-(\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return f"urn:li:activity:{match.group(1)}"
    raise ValueError(f"Could not extract activity URN from URL: {url}")
