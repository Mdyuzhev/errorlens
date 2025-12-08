"""Extended tests for error analyzer service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.analyzer import _format_context, _get_provider, _parse_llm_response
from app.models_pydantic import AnalyzeRequest, ConsoleLogEntry, JSException, NetworkError


class TestAnalyzerEdgeCases:
    """Edge case tests for analyzer."""

    def test_empty_console_logs(self):
        """Empty console logs should not include header."""
        request = AnalyzeRequest(
            url="https://example.com",
            user_agent="Test",
            console_logs=[],
            recording_duration_ms=1000,
        )
        context = _format_context(request)
        assert "=== CONSOLE LOGS ===" not in context

    def test_empty_network_errors(self):
        """Empty network errors should not include header."""
        request = AnalyzeRequest(
            url="https://example.com",
            user_agent="Test",
            network_errors=[],
            recording_duration_ms=1000,
        )
        context = _format_context(request)
        assert "=== NETWORK ERRORS ===" not in context

    def test_empty_js_exceptions(self):
        """Empty JS exceptions should not include header."""
        request = AnalyzeRequest(
            url="https://example.com",
            user_agent="Test",
            js_exceptions=[],
            recording_duration_ms=1000,
        )
        context = _format_context(request)
        assert "=== JS EXCEPTIONS ===" not in context

    def test_max_console_logs_limit(self):
        """Should limit console logs to 50 entries."""
        request = AnalyzeRequest(
            url="https://example.com",
            user_agent="Test",
            console_logs=[
                ConsoleLogEntry(
                    timestamp=f"2025-01-15T10:30:{i:02d}Z",
                    level="log",
                    message=f"msg{i}",
                )
                for i in range(100)
            ],
            recording_duration_ms=1000,
        )
        context = _format_context(request)
        assert "msg49" in context
        assert "msg50" not in context

    def test_max_network_errors_limit(self):
        """Should limit network errors to 30 entries."""
        request = AnalyzeRequest(
            url="https://example.com",
            user_agent="Test",
            network_errors=[
                NetworkError(
                    timestamp=f"2025-01-15T10:30:{i:02d}Z",
                    method="GET",
                    url=f"https://api{i}.example.com",
                    status=500,
                )
                for i in range(50)
            ],
            recording_duration_ms=1000,
        )
        context = _format_context(request)
        assert "api29" in context
        assert "api30" not in context

    def test_max_js_exceptions_limit(self):
        """Should limit JS exceptions to 20 entries."""
        request = AnalyzeRequest(
            url="https://example.com",
            user_agent="Test",
            js_exceptions=[
                JSException(
                    timestamp=f"2025-01-15T10:30:{i:02d}Z",
                    message=f"error{i}",
                )
                for i in range(40)
            ],
            recording_duration_ms=1000,
        )
        context = _format_context(request)
        assert "error19" in context
        assert "error20" not in context

    def test_stack_truncation(self):
        """Should truncate long stack traces to 500 chars."""
        long_stack = "a" * 1000
        request = AnalyzeRequest(
            url="https://example.com",
            user_agent="Test",
            console_logs=[
                ConsoleLogEntry(
                    timestamp="2025-01-15T10:30:00Z",
                    level="error",
                    message="Error",
                    stack=long_stack,
                )
            ],
            recording_duration_ms=1000,
        )
        context = _format_context(request)
        assert long_stack[:500] in context
        assert long_stack not in context

    def test_none_values_handling(self):
        """Should handle None stack values without crashing."""
        request = AnalyzeRequest(
            url="https://example.com",
            user_agent="Test",
            console_logs=[
                ConsoleLogEntry(
                    timestamp="2025-01-15T10:30:00Z",
                    level="error",
                    message="Error",
                    stack=None,
                )
            ],
            recording_duration_ms=1000,
        )
        context = _format_context(request)
        assert "Error" in context

    def test_special_characters(self):
        """Should handle special characters in messages."""
        request = AnalyzeRequest(
            url="https://example.com",
            user_agent="Test",
            console_logs=[
                ConsoleLogEntry(
                    timestamp="2025-01-15T10:30:00Z",
                    level="error",
                    message='Error with "quotes" and <tags>',
                )
            ],
            recording_duration_ms=1000,
        )
        context = _format_context(request)
        assert '"quotes"' in context
        assert "<tags>" in context


class TestProviderSelection:
    """Tests for provider selection logic."""

    def test_ollama_fallback(self):
        """Should return OllamaProvider when only ollama configured."""
        with patch("app.analyzer.settings") as mock_settings:
            mock_settings.llm_provider = "gemini"
            mock_settings.gemini_api_key = ""
            mock_settings.groq_api_key = ""
            mock_settings.ollama_host = "http://localhost:11434"

            from app.providers.ollama import OllamaProvider

            provider = _get_provider()
            assert isinstance(provider, OllamaProvider)

    def test_explicit_ollama_selection(self):
        """Should return OllamaProvider when llm_provider=ollama."""
        with patch("app.analyzer.settings") as mock_settings:
            mock_settings.llm_provider = "ollama"
            mock_settings.ollama_host = "http://localhost:11434"
            mock_settings.groq_api_key = "test-key"

            from app.providers.ollama import OllamaProvider

            provider = _get_provider()
            assert isinstance(provider, OllamaProvider)

    def test_gemini_priority(self):
        """Should return GeminiProvider when explicitly selected."""
        with patch("app.analyzer.settings") as mock_settings:
            mock_settings.llm_provider = "gemini"
            mock_settings.gemini_api_key = "test-key"
            mock_settings.groq_api_key = "groq-key"
            mock_settings.ollama_host = ""

            from app.providers.gemini import GeminiProvider

            provider = _get_provider()
            assert isinstance(provider, GeminiProvider)


class TestLLMResponseParsing:
    """Tests for LLM response parsing."""

    def test_nested_json(self):
        """Should handle details as dict."""
        response = '{"summary": "Test", "probable_cause": "Cause", "suggested_fix": "Fix", "severity": "high", "details": {"key": "value"}}'
        result = _parse_llm_response(response)
        assert result["summary"] == "Test"
        assert isinstance(result["details"], (str, dict))

    def test_unicode_characters(self):
        """Should parse Russian text."""
        response = '{"summary": "Тест", "probable_cause": "Причина", "suggested_fix": "Решение", "severity": "medium", "details": "Детали"}'
        result = _parse_llm_response(response)
        assert result["summary"] == "Тест"

    def test_escaped_quotes(self):
        """Should handle escaped quotes."""
        response = '{"summary": "Error with \\"quotes\\"", "probable_cause": "Cause", "suggested_fix": "Fix", "severity": "low", "details": "Details"}'
        result = _parse_llm_response(response)
        assert '"quotes"' in result["summary"] or "quotes" in result["summary"]

    def test_multiline_json(self):
        """Should parse multiline JSON."""
        response = """{
            "summary": "Test",
            "probable_cause": "Cause",
            "suggested_fix": "Fix",
            "severity": "critical",
            "details": "Details"
        }"""
        result = _parse_llm_response(response)
        assert result["summary"] == "Test"
