"""GigaChat (Sber) provider."""

import uuid
from typing import Any

import httpx

from .base import BaseHTTPProvider


class GigaChatProvider(BaseHTTPProvider):
    """GigaChat API provider (Sber)."""

    def __init__(self, credentials: str, model: str = "GigaChat"):
        super().__init__(
            api_key=credentials,
            model=model,
            base_url="https://gigachat.devices.sberbank.ru/api/v1",
            verify_ssl=False,
        )
        self.credentials = credentials
        self._token: str | None = None

    async def _get_token(self) -> str:
        """Get OAuth token from GigaChat."""
        if self._token:
            return self._token

        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            response = await client.post(
                "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                headers={
                    "Authorization": f"Basic {self.credentials}",
                    "RqUID": str(uuid.uuid4()),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"scope": "GIGACHAT_API_PERS"},
            )
            response.raise_for_status()
            self._token = response.json()["access_token"]
            return self._token

    def _build_headers(self) -> dict[str, str]:
        # Token will be set dynamically in generate()
        return {
            "Authorization": f"Bearer {self._token}",
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

    async def generate(self, prompt: str, max_tokens: int = 4096) -> str:
        """Generate completion with token refresh."""
        await self._get_token()
        return await super().generate(prompt, max_tokens)
