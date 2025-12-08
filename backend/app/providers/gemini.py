"""Google Gemini LLM provider."""

import httpx

from app.config import settings
from app.providers.base import LLMProvider, BaseLLMProvider


class GeminiProvider(LLMProvider):
    """Gemini API provider using REST API."""

    API_URL = (
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    )

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


class GeminiGeneratorProvider(BaseLLMProvider):
    """Gemini provider for test generation (Wave 4.0)."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def generate(self, prompt: str, max_tokens: int = 4096) -> str:
        """Generate completion using Gemini API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/{self.model}:generateContent",
                params={"key": self.api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": max_tokens,
                    },
                },
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    def get_model_name(self) -> str:
        return self.model
