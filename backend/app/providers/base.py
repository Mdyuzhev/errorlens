"""Base interface for LLM providers."""

from abc import ABC, abstractmethod


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
