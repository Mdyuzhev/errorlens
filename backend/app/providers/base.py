"""Base interface for LLM providers."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

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
