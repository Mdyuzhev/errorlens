"""OpenAI provider."""

from .base import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI API provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        super().__init__(
            api_key=api_key,
            model=model,
            base_url="https://api.openai.com/v1",
        )
