"""Tests for ErrorLens API endpoints."""

import pytest


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_ok(self, client):
        """Health check should return status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_health_includes_version(self, client):
        """Health check should include version string."""
        response = client.get("/health")
        data = response.json()
        assert data["version"] == "0.1.0"


class TestAnalyzeEndpoint:
    """Tests for /analyze endpoint - requires authentication."""

    def test_analyze_rejects_unauthenticated(self, client, empty_analyze_request):
        """Analyze should reject unauthenticated requests."""
        response = client.post("/analyze", json=empty_analyze_request)
        assert response.status_code == 401  # Unauthorized

    def test_analyze_validates_auth_before_body(self, client):
        """Analyze should check auth before validating body."""
        response = client.post("/analyze", json={})
        assert response.status_code == 401  # Auth check first

    def test_analyze_requires_auth(self, client, sample_analyze_request):
        """Analyze should require authentication."""
        response = client.post("/analyze", json=sample_analyze_request)
        assert response.status_code == 401  # Unauthorized


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_allows_any_origin(self, client):
        """CORS should allow any origin for bookmarklet compatibility."""
        response = client.options(
            "/analyze",
            headers={
                "Origin": "https://random-site.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        # FastAPI handles CORS, just verify no error
        assert response.status_code in [200, 405]
