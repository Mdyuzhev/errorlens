"""Ollama LLM provider for local models."""

import httpx
import logging

from app.config import settings
from typing import Any

from app.providers.base import LLMProvider, BaseHTTPProvider

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama API provider for local LLM models (qwen2.5-coder) - Legacy error analysis."""

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


class OllamaGeneratorProvider(BaseHTTPProvider):
    """Ollama provider for test generation (Wave 4.0)."""

    def __init__(self, api_key: str = "", model: str = "qwen2.5-coder:7b"):
        """Initialize Ollama generator provider."""
        super().__init__(
            api_key=api_key,
            model=model,
            base_url=settings.OLLAMA_HOST,
        )

    def _build_headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def _build_request_body(self, prompt: str, max_tokens: int) -> dict[str, Any]:
        return {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": max_tokens},
        }

    def _extract_response(self, data: dict[str, Any]) -> str:
        return data.get("response", "")

    def _get_endpoint(self) -> str:
        return f"{self.base_url}/api/generate"
