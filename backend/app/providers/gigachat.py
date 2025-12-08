"""GigaChat (Sber) provider."""

import httpx
import uuid
from .base import BaseLLMProvider


class GigaChatProvider(BaseLLMProvider):
    """GigaChat API provider (Sber)."""

    def __init__(self, credentials: str, model: str = "GigaChat"):
        self.credentials = credentials
        self.model = model
        self.base_url = "https://gigachat.devices.sberbank.ru/api/v1"
        self.token = None

    async def _get_token(self) -> str:
        """Get OAuth token from GigaChat."""
        if self.token:
            return self.token

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                headers={
                    "Authorization": f"Basic {self.credentials}",
                    "RqUID": str(uuid.uuid4()),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"scope": "GIGACHAT_API_PERS"},
                timeout=30.0,
            )
            response.raise_for_status()
            self.token = response.json()["access_token"]
            return self.token

    async def generate(self, prompt: str, max_tokens: int = 4096) -> str:
        """Generate completion using GigaChat API."""
        token = await self._get_token()

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {token}",
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
