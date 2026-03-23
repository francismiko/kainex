from __future__ import annotations

import json
import logging

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """Async LLM client that talks to OpenRouter (OpenAI-compatible)."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def analyze(self, prompt: str) -> dict:
        """Send prompt to LLM and parse a JSON response.

        Falls back to a safe ``hold`` decision when JSON parsing fails.
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except json.JSONDecodeError as exc:
            logger.warning("LLM returned invalid JSON, falling back to hold: %s", exc)
            return _fallback_hold()
        except Exception as exc:
            logger.error("LLM request failed: %s", exc)
            return _fallback_hold()


def _fallback_hold() -> dict:
    """Return a safe hold decision when LLM analysis fails."""
    return {
        "analysis": "Unable to obtain LLM analysis; defaulting to hold.",
        "decisions": [],
        "overall_sentiment": "neutral",
    }
