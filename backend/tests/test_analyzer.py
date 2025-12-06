"""Tests for error analyzer service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.analyzer import (
    SYSTEM_PROMPT,
    _format_context,
    _get_provider,
    _parse_llm_response,
    analyze_errors,
)
from app.models_pydantic import AnalyzeRequest, ConsoleLogEntry, JSException, NetworkError


class TestFormatContext:
    """Tests for context formatting."""

    @pytest.fixture
    def basic_request(self):
        return AnalyzeRequest(
            url="https://example.com/app",
            user_agent="Mozilla/5.0 (Test)",
            console_logs=[],
            network_errors=[],
            js_exceptions=[],
            recording_duration_ms=5000,
        )

    def test_includes_system_prompt(self, basic_request):
        """Context should include system prompt."""
        context = _format_context(basic_request)
        assert SYSTEM_PROMPT in context

    def test_includes_page_url(self, basic_request):
        """Context should include page URL."""
        context = _format_context(basic_request)
        assert "https://example.com/app" in context

    def test_includes_user_agent(self, basic_request):
        """Context should include user agent."""
        context = _format_context(basic_request)
        assert "Mozilla/5.0 (Test)" in context

    def test_includes_recording_duration(self, basic_request):
        """Context should include recording duration."""
        context = _format_context(basic_request)
        assert "5000" in context  # Duration in ms (Russian: мс)

    def test_formats_console_logs(self):
        """Should format console logs with timestamp and level."""
        request = AnalyzeRequest(
            url="https://example.com",
            user_agent="Test",
            console_logs=[
                ConsoleLogEntry(
                    timestamp="2025-01-15T10:30:00Z",
                    level="error",
                    message="Test error message",
                    stack="at foo (app.js:42)",
                )
            ],
            recording_duration_ms=1000,
        )
        context = _format_context(request)
        assert "Логи консоли" in context  # Russian header
        assert "[ERROR]" in context
        assert "Test error message" in context
        assert "at foo (app.js:42)" in context

    def test_formats_network_errors(self):
        """Should format network errors with method and status."""
        request = AnalyzeRequest(
            url="https://example.com",
            user_agent="Test",
            network_errors=[
                NetworkError(
                    timestamp="2025-01-15T10:30:00Z",
                    method="POST",
                    url="https://api.example.com/data",
                    status=500,
                    status_text="Internal Server Error",
                )
            ],
            recording_duration_ms=1000,
        )
        context = _format_context(request)
        assert "Сетевые ошибки" in context  # Russian header
        assert "POST" in context
        assert "https://api.example.com/data" in context
        assert "500" in context

    def test_formats_js_exceptions(self):
        """Should format JS exceptions with source location."""
        request = AnalyzeRequest(
            url="https://example.com",
            user_agent="Test",
            js_exceptions=[
                JSException(
                    timestamp="2025-01-15T10:30:00Z",
                    message="Uncaught TypeError",
                    source="app.js",
                    lineno=42,
                    colno=10,
                    stack="at foo (app.js:42:10)",
                )
            ],
            recording_duration_ms=1000,
        )
        context = _format_context(request)
        assert "JavaScript исключения" in context  # Russian header
        assert "Uncaught TypeError" in context
        assert "app.js:42:10" in context

    def test_limits_console_logs(self):
        """Should limit console logs to prevent token overflow."""
        request = AnalyzeRequest(
            url="https://example.com",
            user_agent="Test",
            console_logs=[
                ConsoleLogEntry(
                    timestamp=f"2025-01-15T10:30:{i:02d}Z",
                    level="log",
                    message=f"Log message {i}",
                )
                for i in range(100)
            ],
            recording_duration_ms=1000,
        )
        context = _format_context(request)
        # Should only include first 50
        assert "Log message 49" in context
        assert "Log message 50" not in context


class TestParseLLMResponse:
    """Tests for LLM response parsing."""

    def test_parses_valid_json(self):
        """Should parse valid JSON response."""
        response = '{"summary": "Test", "probable_cause": "Cause", "suggested_fix": "Fix", "severity": "high", "details": "Details"}'
        result = _parse_llm_response(response)
        assert result["summary"] == "Test"
        assert result["severity"] == "high"

    def test_extracts_json_from_markdown(self):
        """Should extract JSON from markdown code block."""
        response = """Here is the analysis:
```json
{"summary": "Test", "probable_cause": "Cause", "suggested_fix": "Fix", "severity": "medium", "details": "Details"}
```
"""
        result = _parse_llm_response(response)
        assert result["summary"] == "Test"

    def test_extracts_json_from_generic_code_block(self):
        """Should extract JSON from generic code block."""
        response = """```
{"summary": "Test", "probable_cause": "Cause", "suggested_fix": "Fix", "severity": "low", "details": "Details"}
```"""
        result = _parse_llm_response(response)
        assert result["summary"] == "Test"

    def test_fallback_on_invalid_json(self):
        """Should return fallback structure on invalid JSON."""
        response = "This is not JSON, just plain text analysis"
        result = _parse_llm_response(response)
        assert result["summary"] == "Анализ завершён"  # Russian fallback
        assert result["severity"] == "medium"
        assert "This is not JSON" in result["details"]

    def test_handles_whitespace(self):
        """Should handle leading/trailing whitespace."""
        response = """

        {"summary": "Test", "probable_cause": "Cause", "suggested_fix": "Fix", "severity": "critical", "details": "Details"}

        """
        result = _parse_llm_response(response)
        assert result["summary"] == "Test"


class TestGetProvider:
    """Tests for provider selection logic."""

    def test_returns_groq_when_configured(self):
        """Should return Groq when llm_provider is groq and key exists."""
        with patch("app.analyzer.settings") as mock_settings:
            mock_settings.llm_provider = "groq"
            mock_settings.groq_api_key = "test-key"
            mock_settings.gemini_api_key = ""

            from app.providers.groq import GroqProvider

            provider = _get_provider()
            assert isinstance(provider, GroqProvider)

    def test_returns_gemini_when_configured(self):
        """Should return Gemini when key exists."""
        with patch("app.analyzer.settings") as mock_settings:
            mock_settings.llm_provider = "gemini"
            mock_settings.gemini_api_key = "test-key"
            mock_settings.groq_api_key = ""

            from app.providers.gemini import GeminiProvider

            provider = _get_provider()
            assert isinstance(provider, GeminiProvider)

    def test_fallback_to_groq(self):
        """Should fallback to Groq if Gemini not available."""
        with patch("app.analyzer.settings") as mock_settings:
            mock_settings.llm_provider = "gemini"
            mock_settings.gemini_api_key = ""
            mock_settings.groq_api_key = "test-key"

            from app.providers.groq import GroqProvider

            provider = _get_provider()
            assert isinstance(provider, GroqProvider)

    def test_raises_when_no_keys(self):
        """Should raise when no API keys configured."""
        with patch("app.analyzer.settings") as mock_settings:
            mock_settings.llm_provider = "gemini"
            mock_settings.gemini_api_key = ""
            mock_settings.groq_api_key = ""

            with pytest.raises(ValueError, match="No LLM API key configured"):
                _get_provider()


class TestAnalyzeErrors:
    """Integration tests for analyze_errors function."""

    @pytest.fixture
    def sample_request(self):
        return AnalyzeRequest(
            url="https://example.com/app",
            user_agent="Mozilla/5.0",
            console_logs=[
                ConsoleLogEntry(
                    timestamp="2025-01-15T10:30:00Z",
                    level="error",
                    message="Test error",
                )
            ],
            recording_duration_ms=5000,
        )

    @pytest.mark.asyncio
    async def test_returns_analyze_response(self, sample_request):
        """Should return properly structured AnalyzeResponse."""
        mock_provider = MagicMock()
        mock_provider.name = "mock"
        mock_provider.analyze = AsyncMock(
            return_value='{"summary": "Test", "probable_cause": "Cause", "suggested_fix": "Fix", "severity": "high", "details": "Details"}'
        )

        with patch("app.analyzer._get_provider", return_value=mock_provider):
            result = await analyze_errors(sample_request)

        assert result.summary == "Test"
        assert result.probable_cause == "Cause"
        assert result.suggested_fix == "Fix"
        assert result.severity == "high"
        assert result.raw_events_count == 1

    @pytest.mark.asyncio
    async def test_counts_all_events(self):
        """Should count all event types."""
        request = AnalyzeRequest(
            url="https://example.com",
            user_agent="Test",
            console_logs=[
                ConsoleLogEntry(timestamp="t1", level="error", message="e1"),
                ConsoleLogEntry(timestamp="t2", level="warn", message="e2"),
            ],
            network_errors=[
                NetworkError(timestamp="t3", method="GET", url="http://a.com", status=500),
            ],
            js_exceptions=[
                JSException(timestamp="t4", message="ex1"),
            ],
            recording_duration_ms=1000,
        )

        mock_provider = MagicMock()
        mock_provider.name = "mock"
        mock_provider.analyze = AsyncMock(return_value='{"summary": "Test"}')

        with patch("app.analyzer._get_provider", return_value=mock_provider):
            result = await analyze_errors(request)

        assert result.raw_events_count == 4
