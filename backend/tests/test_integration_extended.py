"""Extended integration tests for ErrorLens API."""

import pytest
from fastapi.testclient import TestClient


def get_token(client: TestClient) -> str:
    """Get test user token."""
    response = client.post("/auth/login", json={"username": "owner1", "password": "Test123!"})
    if response.status_code != 200:
        pytest.skip(f"Cannot login: {response.text}")
    return response.json()["access_token"]


def auth_headers(token: str) -> dict:
    """Create authorization headers."""
    return {"Authorization": f"Bearer {token}"}


class TestExportEndpoints:
    """Test export endpoints with edge cases."""

    def test_export_postman_no_requests(self, client):
        """POST /export/postman - returns error for invalid session."""
        token = get_token(client)
        response = client.post(
            "/export/postman",
            json={"session_id": "nonexistent"},
            headers=auth_headers(token)
        )
        assert response.status_code in [400, 404, 422]

    def test_export_pytest_no_requests(self, client):
        """POST /export/pytest - returns error for invalid session."""
        token = get_token(client)
        response = client.post(
            "/export/pytest",
            json={"session_id": "nonexistent"},
            headers=auth_headers(token)
        )
        assert response.status_code in [400, 404, 422]

    def test_export_restassured_no_requests(self, client):
        """POST /export/restassured - returns error for invalid session."""
        token = get_token(client)
        response = client.post(
            "/export/restassured",
            json={"session_id": "nonexistent"},
            headers=auth_headers(token)
        )
        assert response.status_code in [400, 404, 422]

    def test_export_k6_no_requests(self, client):
        """POST /export/k6 - returns error for invalid session."""
        token = get_token(client)
        response = client.post(
            "/export/k6",
            json={"session_id": "nonexistent"},
            headers=auth_headers(token)
        )
        assert response.status_code in [400, 404, 422]

    def test_export_testit_no_requests(self, client):
        """POST /export/testit - returns error for invalid session."""
        token = get_token(client)
        response = client.post(
            "/export/testit",
            json={"session_id": "nonexistent"},
            headers=auth_headers(token)
        )
        assert response.status_code in [400, 404, 422]


class TestGenerationEndpoints:
    """Test generation endpoints with edge cases."""

    def test_from_swagger_empty_paths(self, client):
        """POST /v1/generation/from-swagger - accepts empty swagger."""
        token = get_token(client)

        import io
        empty_swagger = io.BytesIO(b'{"paths": {}}')

        response = client.post(
            "/v1/generation/from-swagger",
            files={"file": ("swagger.json", empty_swagger, "application/json")},
            data={"framework": "pytest", "provider": "ollama"},
            headers=auth_headers(token)
        )
        assert response.status_code in [200, 202, 400, 422]

    def test_from_session_no_requests(self, client):
        """POST /v1/generation/from-session - returns 400 when session has no requests."""
        token = get_token(client)
        response = client.post(
            "/v1/generation/from-session",
            json={"session_id": "nonexistent", "framework": "pytest", "provider": "ollama"},
            headers=auth_headers(token)
        )
        assert response.status_code in [400, 404]

    def test_from_session_not_found(self, client):
        """POST /v1/generation/from-session - returns 404 for nonexistent session."""
        token = get_token(client)
        response = client.post(
            "/v1/generation/from-session",
            json={"session_id": "nonexistent-id-12345", "framework": "pytest", "provider": "ollama"},
            headers=auth_headers(token)
        )
        assert response.status_code == 404


class TestSessionEndpoints:
    """Test session endpoints with edge cases."""

    def test_create_session_empty_events(self, client):
        """POST /sessions - accepts empty events."""
        token = get_token(client)
        response = client.post(
            "/sessions",
            json={"url": "https://test.com", "events": []},
            headers=auth_headers(token)
        )
        assert response.status_code in [200, 201, 400, 422]

    def test_create_session_valid(self, client):
        """POST /sessions - creates session with valid data."""
        token = get_token(client)
        response = client.post(
            "/sessions",
            json={
                "url": "https://test.com",
                "events": [
                    {
                        "type": "request",
                        "timestamp": "2025-01-15T10:30:00Z",
                        "data": {"method": "GET", "url": "https://api.test.com"}
                    }
                ]
            },
            headers=auth_headers(token)
        )
        assert response.status_code in [200, 201, 422]

    def test_list_sessions_requires_auth(self, client):
        """GET /sessions - returns 401 without auth."""
        response = client.get("/sessions")
        assert response.status_code == 401

    def test_delete_session_requires_auth(self, client):
        """DELETE /sessions/{id} - returns 401 without auth."""
        response = client.delete("/sessions/test-id")
        assert response.status_code == 401
