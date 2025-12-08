"""Base interface for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any

import httpx


class LLMProvider(ABC):
    """Abstract base class for LLM providers (legacy - for error analysis)."""

    @abstractmethod
    async def analyze(self, context: str) -> str:
        """
        Send context to LLM and get analysis response.

        Args:
            context: Formatted error context string

        Returns:
            Raw LLM response text
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging."""
        pass


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers (Wave 4.0 - test generation)."""

    @abstractmethod
    async def generate(self, prompt: str, max_tokens: int = 4096) -> str:
        """Generate completion from prompt."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return model identifier."""
        pass


class BaseHTTPProvider(BaseLLMProvider):
    """Base class for HTTP-based LLM providers with shared HTTP client logic."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        timeout: float = 120.0,
        verify_ssl: bool = True,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.verify_ssl = verify_ssl

    @abstractmethod
    def _build_headers(self) -> dict[str, str]:
        """Build request headers for the specific provider."""
        pass

    @abstractmethod
    def _build_request_body(self, prompt: str, max_tokens: int) -> dict[str, Any]:
        """Build request body for the specific provider."""
        pass

    @abstractmethod
    def _extract_response(self, data: dict[str, Any]) -> str:
        """Extract generated text from provider response."""
        pass

    def _get_endpoint(self) -> str:
        """Get API endpoint URL. Override if needed."""
        return self.base_url

    def _get_request_params(self) -> dict[str, str] | None:
        """Get query parameters. Override if needed."""
        return None

    async def generate(self, prompt: str, max_tokens: int = 4096) -> str:
        """Generate completion using HTTP API."""
        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=self.timeout) as client:
            response = await client.post(
                self._get_endpoint(),
                headers=self._build_headers(),
                params=self._get_request_params(),
                json=self._build_request_body(prompt, max_tokens),
            )
            response.raise_for_status()
            return self._extract_response(response.json())

    def get_model_name(self) -> str:
        return self.model


class OpenAICompatibleProvider(BaseHTTPProvider):
    """Base for OpenAI-compatible APIs (OpenAI, Groq, etc.)."""

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_request_body(self, prompt: str, max_tokens: int) -> dict[str, Any]:
        return {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

    def _extract_response(self, data: dict[str, Any]) -> str:
        return data["choices"][0]["message"]["content"]

    def _get_endpoint(self) -> str:
        return f"{self.base_url}/chat/completions"
