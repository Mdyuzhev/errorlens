"""Pytest fixtures for ErrorLens tests."""

import os

# Set DATABASE_URL before any app imports (PostgreSQL only)
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://errorlens:errorlens_secret@localhost:5432/errorlens"

import pytest
from app.main import app
from fastapi.testclient import TestClient


# Session-scoped client triggers lifespan once (creates tables, seeds data)
@pytest.fixture(scope="session")
def _app_client():
    """Session-scoped TestClient that triggers app lifespan."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client(_app_client):
    """Create test client for API tests."""
    return _app_client


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
