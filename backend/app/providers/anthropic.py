"""Anthropic Claude provider."""

from typing import Any

from .base import BaseHTTPProvider


class AnthropicProvider(BaseHTTPProvider):
    """Anthropic Claude API provider."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        super().__init__(
            api_key=api_key,
            model=model,
            base_url="https://api.anthropic.com/v1",
        )

    def _build_headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def _build_request_body(self, prompt: str, max_tokens: int) -> dict[str, Any]:
        return {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

    def _extract_response(self, data: dict[str, Any]) -> str:
        return data["content"][0]["text"]

    def _get_endpoint(self) -> str:
        return f"{self.base_url}/messages"
