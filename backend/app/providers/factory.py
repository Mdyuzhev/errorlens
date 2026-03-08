"""LLM Provider factory."""

from typing import Literal

from app.config import settings

from .anthropic import AnthropicProvider
from .base import BaseLLMProvider
from .gemini import GeminiGeneratorProvider
from .gigachat import GigaChatProvider
from .groq import GroqGeneratorProvider
from .ollama import OllamaGeneratorProvider
from .openai import OpenAIProvider

ProviderType = Literal["anthropic", "openai", "gigachat", "groq", "gemini", "ollama"]


class ProviderFactory:
    """Factory for creating LLM providers."""

    _providers = {
        "anthropic": AnthropicProvider,
        "openai": OpenAIProvider,
        "gigachat": GigaChatProvider,
        "groq": GroqGeneratorProvider,
        "gemini": GeminiGeneratorProvider,
        "ollama": OllamaGeneratorProvider,
    }

    @classmethod
    def create(
        cls,
        provider_type: ProviderType,
        api_key: str | None = None,
        model: str | None = None,
    ) -> BaseLLMProvider:
        """Create LLM provider instance."""
        if provider_type not in cls._providers:
            raise ValueError(f"Unknown provider: {provider_type}")

        provider_class = cls._providers[provider_type]
        key = api_key or cls._get_api_key(provider_type)

        if model:
            return provider_class(api_key=key, model=model)
        return provider_class(api_key=key)

    @classmethod
    def _get_api_key(cls, provider_type: str) -> str:
        """Get API key from settings."""
        key_map = {
            "anthropic": settings.ANTHROPIC_API_KEY,
            "openai": settings.OPENAI_API_KEY,
            "gigachat": settings.GIGACHAT_CREDENTIALS,
            "groq": settings.GROQ_API_KEY,
            "gemini": settings.GEMINI_API_KEY,
            "ollama": "",
        }
        key = key_map.get(provider_type, "")
        if not key and provider_type != "ollama":
            raise ValueError(f"API key not configured for {provider_type}")
        return key

    @classmethod
    def list_providers(cls) -> list[str]:
        """Return list of available provider names."""
        return list(cls._providers.keys())
