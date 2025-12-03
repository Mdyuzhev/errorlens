"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from app.models import (
    ConsoleLogEntry,
    NetworkError,
    JSException,
    AnalyzeRequest,
    AnalyzeResponse,
)


class TestConsoleLogEntry:
    """Tests for ConsoleLogEntry model."""

    def test_valid_entry(self):
        """Should accept valid console log entry."""
        entry = ConsoleLogEntry(
            timestamp="2025-01-15T10:30:00Z",
            level="error",
            message="Test error message",
        )
        assert entry.timestamp == "2025-01-15T10:30:00Z"
        assert entry.level == "error"
        assert entry.message == "Test error message"
        assert entry.stack is None

    def test_with_stack_trace(self):
        """Should accept entry with stack trace."""
        entry = ConsoleLogEntry(
            timestamp="2025-01-15T10:30:00Z",
            level="error",
            message="Error",
            stack="at foo (app.js:42)\nat bar (app.js:15)",
        )
        assert entry.stack == "at foo (app.js:42)\nat bar (app.js:15)"

    def test_requires_timestamp(self):
        """Should require timestamp field."""
        with pytest.raises(ValidationError):
            ConsoleLogEntry(level="error", message="Error")

    def test_requires_level(self):
        """Should require level field."""
        with pytest.raises(ValidationError):
            ConsoleLogEntry(timestamp="2025-01-15T10:30:00Z", message="Error")

    def test_requires_message(self):
        """Should require message field."""
        with pytest.raises(ValidationError):
            ConsoleLogEntry(timestamp="2025-01-15T10:30:00Z", level="error")


class TestNetworkError:
    """Tests for NetworkError model."""

    def test_valid_error(self):
        """Should accept valid network error."""
        error = NetworkError(
            timestamp="2025-01-15T10:30:00Z",
            method="POST",
            url="https://api.example.com/data",
            status=500,
            status_text="Internal Server Error",
        )
        assert error.method == "POST"
        assert error.status == 500

    def test_optional_status(self):
        """Status should be optional (for network failures)."""
        error = NetworkError(
            timestamp="2025-01-15T10:30:00Z",
            method="GET",
            url="https://api.example.com/data",
        )
        assert error.status is None
        assert error.status_text is None

    def test_requires_method(self):
        """Should require HTTP method."""
        with pytest.raises(ValidationError):
            NetworkError(
                timestamp="2025-01-15T10:30:00Z",
                url="https://api.example.com/data",
            )


class TestJSException:
    """Tests for JSException model."""

    def test_valid_exception(self):
        """Should accept valid JS exception."""
        exc = JSException(
            timestamp="2025-01-15T10:30:00Z",
            message="Uncaught TypeError: Cannot read property 'x' of undefined",
            source="https://example.com/app.js",
            lineno=42,
            colno=10,
            stack="at foo (app.js:42:10)",
        )
        assert exc.message == "Uncaught TypeError: Cannot read property 'x' of undefined"
        assert exc.lineno == 42

    def test_minimal_exception(self):
        """Should accept exception with only required fields."""
        exc = JSException(
            timestamp="2025-01-15T10:30:00Z",
            message="Error",
        )
        assert exc.source is None
        assert exc.lineno is None
        assert exc.colno is None
        assert exc.stack is None


class TestAnalyzeRequest:
    """Tests for AnalyzeRequest model."""

    def test_valid_request(self):
        """Should accept valid request."""
        request = AnalyzeRequest(
            url="https://example.com/app",
            user_agent="Mozilla/5.0",
            recording_duration_ms=5000,
        )
        assert request.url == "https://example.com/app"
        assert request.console_logs == []
        assert request.network_errors == []
        assert request.js_exceptions == []

    def test_with_all_error_types(self):
        """Should accept request with all error types."""
        request = AnalyzeRequest(
            url="https://example.com/app",
            user_agent="Mozilla/5.0",
            console_logs=[
                ConsoleLogEntry(
                    timestamp="t1", level="error", message="Console error"
                )
            ],
            network_errors=[
                NetworkError(
                    timestamp="t2", method="GET", url="http://api.com", status=404
                )
            ],
            js_exceptions=[JSException(timestamp="t3", message="JS error")],
            recording_duration_ms=5000,
        )
        assert len(request.console_logs) == 1
        assert len(request.network_errors) == 1
        assert len(request.js_exceptions) == 1

    def test_requires_url(self):
        """Should require URL field."""
        with pytest.raises(ValidationError):
            AnalyzeRequest(
                user_agent="Mozilla/5.0",
                recording_duration_ms=5000,
            )

    def test_requires_user_agent(self):
        """Should require user agent field."""
        with pytest.raises(ValidationError):
            AnalyzeRequest(
                url="https://example.com",
                recording_duration_ms=5000,
            )

    def test_requires_recording_duration(self):
        """Should require recording duration."""
        with pytest.raises(ValidationError):
            AnalyzeRequest(
                url="https://example.com",
                user_agent="Mozilla/5.0",
            )

    def test_screenshot_optional(self):
        """Screenshot should be optional."""
        request = AnalyzeRequest(
            url="https://example.com",
            user_agent="Mozilla/5.0",
            recording_duration_ms=5000,
            screenshot="data:image/png;base64,ABC123",
        )
        assert request.screenshot == "data:image/png;base64,ABC123"


class TestAnalyzeResponse:
    """Tests for AnalyzeResponse model."""

    def test_valid_response(self):
        """Should accept valid response."""
        response = AnalyzeResponse(
            summary="TypeError due to null reference",
            probable_cause="Variable 'user' is undefined",
            suggested_fix="Add null check before accessing property",
            severity="high",
            raw_events_count=5,
            details="Detailed analysis...",
        )
        assert response.summary == "TypeError due to null reference"
        assert response.severity == "high"
        assert response.raw_events_count == 5

    def test_requires_all_fields(self):
        """Should require all response fields."""
        with pytest.raises(ValidationError):
            AnalyzeResponse(
                summary="Test",
                probable_cause="Cause",
                # missing other required fields
            )

    def test_severity_values(self):
        """Should accept various severity values."""
        for severity in ["low", "medium", "high", "critical"]:
            response = AnalyzeResponse(
                summary="Test",
                probable_cause="Cause",
                suggested_fix="Fix",
                severity=severity,
                raw_events_count=1,
                details="Details",
            )
            assert response.severity == severity
