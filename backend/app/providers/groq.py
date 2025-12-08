"""Groq LLM provider."""

import httpx

from app.config import settings
from app.providers.base import LLMProvider, BaseLLMProvider


class GroqProvider(LLMProvider):
    """Groq API provider (Llama models)."""

    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    MODEL = "llama-3.3-70b-versatile"

    @property
    def name(self) -> str:
        return "groq"

    async def analyze(self, context: str) -> str:
        """Send context to Groq and get analysis."""
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY not configured")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.groq_api_key}",
        }

        payload = {
            "model": self.MODEL,
            "messages": [{"role": "user", "content": context}],
            "temperature": 0.3,
            "max_tokens": 2048,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.API_URL,
                headers=headers,
                json=payload,
            )
            if response.status_code != 200:
                import logging

                logging.error(f"Groq API error: {response.status_code} - {response.text}")
            response.raise_for_status()
            data = response.json()

        # Extract text from OpenAI-compatible response
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"Unexpected Groq response format: {e}")


class GroqGeneratorProvider(BaseLLMProvider):
    """Groq provider for test generation (Wave 4.0)."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1"

    async def generate(self, prompt: str, max_tokens: int = 4096) -> str:
        """Generate completion using Groq API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def get_model_name(self) -> str:
        return self.model
