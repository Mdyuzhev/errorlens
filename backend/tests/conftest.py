"""Pytest fixtures for ErrorLens tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client for API tests."""
    return TestClient(app)


@pytest.fixture
def sample_analyze_request():
    """Sample request data for /analyze endpoint."""
    return {
        "url": "https://example.com/app",
        "user_agent": "Mozilla/5.0 (Test)",
        "console_logs": [
            {
                "timestamp": "2025-01-15T10:30:00Z",
                "level": "error",
                "message": "Uncaught TypeError: Cannot read property 'x' of undefined",
                "stack": "at foo (app.js:42)\nat bar (app.js:15)",
            }
        ],
        "network_errors": [
            {
                "timestamp": "2025-01-15T10:30:01Z",
                "method": "POST",
                "url": "https://api.example.com/data",
                "status": 500,
                "status_text": "Internal Server Error",
            }
        ],
        "js_exceptions": [],
        "recording_duration_ms": 5000,
    }


@pytest.fixture
def empty_analyze_request():
    """Request with no error data."""
    return {
        "url": "https://example.com/app",
        "user_agent": "Mozilla/5.0 (Test)",
        "console_logs": [],
        "network_errors": [],
        "js_exceptions": [],
        "recording_duration_ms": 1000,
    }
