"""Ollama LLM provider for local models."""

import httpx
import logging

from app.config import settings
from app.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama API provider for local LLM models (qwen2.5-coder)."""

    def __init__(self, model: str = None):
        """
        Initialize Ollama provider.

        Args:
            model: Model name override (default from settings)
        """
        self._model = model or settings.ollama_model

    @property
    def name(self) -> str:
        return f"ollama/{self._model}"

    async def analyze(self, context: str) -> str:
        """Send context to Ollama and get analysis."""
        if not settings.ollama_host:
            raise ValueError("OLLAMA_HOST not configured")

        payload = {
            "model": self._model,
            "prompt": context,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 2048,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{settings.ollama_host}/api/generate",
                    json=payload,
                )

                if response.status_code != 200:
                    logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                    raise ValueError(f"Ollama error: {response.status_code}")

                data = response.json()
                result = data.get("response", "")

                if not result or len(result.strip()) < 10:
                    logger.warning("Ollama returned empty response")
                    raise ValueError("Ollama returned empty response")

                return result

        except httpx.TimeoutException:
            logger.error(f"Ollama timeout after 120s")
            raise ValueError("Ollama timeout")
        except httpx.ConnectError:
            logger.error(f"Cannot connect to Ollama at {settings.ollama_host}")
            raise ValueError(f"Cannot connect to Ollama at {settings.ollama_host}")
