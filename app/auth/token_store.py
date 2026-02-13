import json
import time
from pathlib import Path
from typing import Optional

STORE_DIR = Path.home() / ".linkedin-tool"
STORE_PATH = STORE_DIR / "tokens.json"


class TokenStore:
    def __init__(self, path: Path = STORE_PATH):
        self.path = path

    def save_token(self, token_data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Compute absolute expiry time
        if "expires_in" in token_data and "expires_at" not in token_data:
            token_data["expires_at"] = time.time() + token_data["expires_in"]
        self.path.write_text(json.dumps(token_data, indent=2))

    def load_token(self) -> Optional[dict]:
        if not self.path.exists():
            return None
        return json.loads(self.path.read_text())

    def is_token_expired(self) -> bool:
        data = self.load_token()
        if not data or "expires_at" not in data:
            return True
        return time.time() >= data["expires_at"]

    def get_valid_token(self) -> Optional[str]:
        if self.is_token_expired():
            return None
        data = self.load_token()
        return data.get("access_token") if data else None

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()


token_store = TokenStore()
