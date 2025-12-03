"""Tests for LLM providers."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.providers.base import LLMProvider
from app.providers.gemini import GeminiProvider
from app.providers.groq import GroqProvider


class TestLLMProviderInterface:
    """Tests for base LLM provider interface."""

    def test_provider_is_abstract(self):
        """Cannot instantiate abstract LLMProvider."""
        with pytest.raises(TypeError):
            LLMProvider()

    def test_gemini_implements_interface(self):
        """GeminiProvider implements LLMProvider interface."""
        provider = GeminiProvider()
        assert isinstance(provider, LLMProvider)
        assert provider.name == "gemini"

    def test_groq_implements_interface(self):
        """GroqProvider implements LLMProvider interface."""
        provider = GroqProvider()
        assert isinstance(provider, LLMProvider)
        assert provider.name == "groq"


class TestGeminiProvider:
    """Tests for Gemini LLM provider."""

    @pytest.fixture
    def provider(self):
        return GeminiProvider()

    @pytest.fixture
    def mock_gemini_response(self):
        """Mock successful Gemini API response."""
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '{"summary": "Test error", "probable_cause": "Test cause", "suggested_fix": "Test fix", "severity": "medium", "details": "Test details"}'
                            }
                        ]
                    }
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_analyze_without_api_key_raises(self, provider):
        """Should raise error when API key not configured."""
        with patch("app.providers.gemini.settings") as mock_settings:
            mock_settings.gemini_api_key = ""
            with pytest.raises(ValueError, match="GEMINI_API_KEY not configured"):
                await provider.analyze("test context")

    @pytest.mark.asyncio
    async def test_analyze_success(self, provider, mock_gemini_response):
        """Should return LLM response text on success."""
        with patch("app.providers.gemini.settings") as mock_settings:
            mock_settings.gemini_api_key = "test-key"

            mock_response = MagicMock()
            mock_response.json.return_value = mock_gemini_response
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )
                result = await provider.analyze("test context")

        assert "Test error" in result
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_analyze_invalid_response_format(self, provider):
        """Should raise on unexpected response format."""
        with patch("app.providers.gemini.settings") as mock_settings:
            mock_settings.gemini_api_key = "test-key"

            mock_response = MagicMock()
            mock_response.json.return_value = {"invalid": "response"}
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )
                with pytest.raises(ValueError, match="Unexpected Gemini response"):
                    await provider.analyze("test context")


class TestGroqProvider:
    """Tests for Groq LLM provider."""

    @pytest.fixture
    def provider(self):
        return GroqProvider()

    @pytest.fixture
    def mock_groq_response(self):
        """Mock successful Groq API response (OpenAI format)."""
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"summary": "Test error", "probable_cause": "Test cause", "suggested_fix": "Test fix", "severity": "high", "details": "Test details"}'
                    }
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_analyze_without_api_key_raises(self, provider):
        """Should raise error when API key not configured."""
        with patch("app.providers.groq.settings") as mock_settings:
            mock_settings.groq_api_key = ""
            with pytest.raises(ValueError, match="GROQ_API_KEY not configured"):
                await provider.analyze("test context")

    @pytest.mark.asyncio
    async def test_analyze_success(self, provider, mock_groq_response):
        """Should return LLM response text on success."""
        with patch("app.providers.groq.settings") as mock_settings:
            mock_settings.groq_api_key = "test-key"

            mock_response = MagicMock()
            mock_response.json.return_value = mock_groq_response
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )
                result = await provider.analyze("test context")

        assert "Test error" in result
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_analyze_invalid_response_format(self, provider):
        """Should raise on unexpected response format."""
        with patch("app.providers.groq.settings") as mock_settings:
            mock_settings.groq_api_key = "test-key"

            mock_response = MagicMock()
            mock_response.json.return_value = {"invalid": "response"}
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )
                with pytest.raises(ValueError, match="Unexpected Groq response"):
                    await provider.analyze("test context")

    def test_groq_uses_correct_model(self, provider):
        """Should use llama-3.1-70b-versatile model."""
        assert provider.MODEL == "llama-3.1-70b-versatile"
