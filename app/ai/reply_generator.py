import json
from typing import Optional

import anthropic

from app.ai.prompts import SYSTEM_PROMPT, USER_PROMPT
from app.config import settings


class ReplyGenerator:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model

    async def generate_replies(
        self,
        post_text: str,
        num_suggestions: int = 3,
        tone: str = "professional",
        user_context: Optional[str] = None,
    ) -> list[str]:
        context_section = ""
        if user_context:
            context_section = f"\nAbout me (weave in naturally): {user_context}\n"

        system = SYSTEM_PROMPT.format(num_suggestions=num_suggestions)
        user_msg = USER_PROMPT.format(
            post_text=post_text,
            context_section=context_section,
            tone=tone,
            num_suggestions=num_suggestions,
        )

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )

        raw = response.content[0].text
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]
        return json.loads(cleaned)
