"""Google Gemini LLM provider."""

import httpx

from app.config import settings
from app.providers.base import LLMProvider


class GeminiProvider(LLMProvider):
    """Gemini API provider using REST API."""

    API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

    @property
    def name(self) -> str:
        return "gemini"

    async def analyze(self, context: str) -> str:
        """Send context to Gemini and get analysis."""
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not configured")

        headers = {"Content-Type": "application/json"}
        params = {"key": settings.gemini_api_key}

        payload = {
            "contents": [{"parts": [{"text": context}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 2048,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.API_URL,
                headers=headers,
                params=params,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        # Extract text from Gemini response
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"Unexpected Gemini response format: {e}")
