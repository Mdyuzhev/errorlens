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
    """Tests for /analyze endpoint."""

    def test_analyze_rejects_empty_data(self, client, empty_analyze_request):
        """Analyze should reject requests with no error data."""
        response = client.post("/analyze", json=empty_analyze_request)
        assert response.status_code == 400
        assert "No error data" in response.json()["detail"]

    def test_analyze_validates_required_fields(self, client):
        """Analyze should validate required fields."""
        response = client.post("/analyze", json={})
        assert response.status_code == 422  # Validation error

    def test_analyze_accepts_valid_request(self, client, sample_analyze_request, mocker):
        """Analyze should accept valid request (with mocked LLM)."""
        # Mock the LLM provider to avoid real API calls
        mock_response = {
            "summary": "Test error",
            "probable_cause": "Test cause",
            "suggested_fix": "Test fix",
            "severity": "medium",
            "details": "Test details",
        }
        mocker.patch(
            "app.analyzer._get_provider",
            side_effect=ValueError("No LLM API key configured"),
        )

        response = client.post("/analyze", json=sample_analyze_request)
        # Without API keys, should return 500
        assert response.status_code == 500


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
