"""Pydantic models for API request/response schemas."""

from pydantic import BaseModel, Field


class ConsoleLogEntry(BaseModel):
    """Single console log entry captured by bookmarklet."""

    timestamp: str = Field(..., description="ISO 8601 timestamp")
    level: str = Field(..., description="Log level: log, warn, error, info, debug")
    message: str = Field(..., description="Log message content")
    stack: str | None = Field(None, description="Stack trace if available")


class NetworkError(BaseModel):
    """Network request failure captured by bookmarklet."""

    timestamp: str = Field(..., description="ISO 8601 timestamp")
    method: str = Field(..., description="HTTP method: GET, POST, etc.")
    url: str = Field(..., description="Request URL")
    status: int | None = Field(None, description="HTTP status code")
    status_text: str | None = Field(None, description="HTTP status text")


class JSException(BaseModel):
    """JavaScript exception captured by window.onerror."""

    timestamp: str = Field(..., description="ISO 8601 timestamp")
    message: str = Field(..., description="Error message")
    source: str | None = Field(None, description="Script URL where error occurred")
    lineno: int | None = Field(None, description="Line number")
    colno: int | None = Field(None, description="Column number")
    stack: str | None = Field(None, description="Stack trace")


class AnalyzeRequest(BaseModel):
    """Request body for /analyze endpoint."""

    url: str = Field(..., description="Page URL where errors were captured")
    user_agent: str = Field(..., description="Browser user agent string")
    console_logs: list[ConsoleLogEntry] = Field(
        default_factory=list, description="Captured console logs"
    )
    network_errors: list[NetworkError] = Field(
        default_factory=list, description="Failed network requests"
    )
    js_exceptions: list[JSException] = Field(
        default_factory=list, description="Uncaught JavaScript exceptions"
    )
    screenshot: str | None = Field(None, description="Base64-encoded screenshot")
    recording_duration_ms: int = Field(..., description="Recording duration in ms")


class AnalyzeResponse(BaseModel):
    """Response body from /analyze endpoint."""

    summary: str = Field(..., description="Brief summary of detected issues")
    probable_cause: str = Field(..., description="Most likely root cause")
    suggested_fix: str = Field(..., description="Recommended fix")
    severity: str = Field(..., description="Severity: low, medium, high, critical")
    raw_events_count: int = Field(..., description="Total events analyzed")
    details: str = Field(..., description="Detailed analysis")
