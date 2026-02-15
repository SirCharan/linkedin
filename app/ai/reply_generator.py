import ast
import json
import re
from typing import Optional

import httpx

from app.ai.prompts import PERSONA
from app.config import settings

SYSTEM = """{persona}

Write LinkedIn comments as Charandeep. Be direct, data-driven, concise (1-3 sentences).
Never be generic or sycophantic. Add real value — a sharp insight, contrarian take, or smart question."""

USER = """LinkedIn post: "{post_text}"

Write {num_suggestions} distinct comment(s). Tone: {tone}.
{context_section}
Reply with JSON: {{"comments": ["comment1", "comment2"]}}"""


class ReplyGenerator:
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    async def generate_replies(
        self,
        post_text: str,
        num_suggestions: int = 3,
        tone: str = "professional",
        user_context: Optional[str] = None,
    ) -> list[str]:
        context_section = ""
        if user_context:
            context_section = f"Context about me: {user_context}"

        system = SYSTEM.format(persona=PERSONA)
        user_msg = USER.format(
            post_text=post_text[:500],
            num_suggestions=num_suggestions,
            tone=tone,
            context_section=context_section,
        )

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_msg},
                    ],
                    "stream": False,
                    "format": "json",
                },
            )
            resp.raise_for_status()
            raw = resp.json()["message"]["content"]

        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> list[str]:
        cleaned = raw.strip()
        # Strip code fences
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0].strip()

        # Try JSON first, then Python ast.literal_eval for single-quoted dicts
        parsed = None
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(cleaned)
            except Exception:
                pass

        if parsed is None:
            # Last resort: extract any quoted string that looks like a comment
            strings = re.findall(r'"([^"]{20,})"', cleaned)
            if not strings:
                strings = re.findall(r"'([^']{20,})'", cleaned)
            return strings if strings else [cleaned]

        return self._extract_strings(parsed)

    def _extract_strings(self, parsed) -> list[str]:
        if isinstance(parsed, str):
            return [parsed] if len(parsed) > 20 else []

        if isinstance(parsed, list):
            out = []
            for x in parsed:
                if isinstance(x, str) and len(x) > 20:
                    out.append(x)
                elif isinstance(x, dict):
                    out.extend(self._extract_strings(x))
            return out if out else [str(parsed)]

        if isinstance(parsed, dict):
            # Check known keys first
            for key in ("comments", "suggestions", "replies", "comment", "text", "response", "reply"):
                val = parsed.get(key)
                if isinstance(val, list):
                    return self._extract_strings(val)
                if isinstance(val, str) and len(val) > 20:
                    return [val]
            # Fall back to all string values
            values = [v for v in parsed.values() if isinstance(v, str) and len(v) > 20]
            if values:
                return values

        return [str(parsed)]
