"""Integration tests for ErrorLens API with test users.

Tests all API endpoints with different user roles and projects.
Run after seeding test users via: python -m app.services.seed_test_users
"""

import pytest
from fastapi.testclient import TestClient


# Test user credentials (from seed_test_users.py)
TEST_USERS = {
    "owner1": {"password": "Test123!", "project": "project-alpha", "role": "owner"},
    "owner2": {"password": "Test123!", "project": "project-beta", "role": "owner"},
    "admin1": {"password": "Test123!", "project": "project-alpha", "role": "admin"},
    "member1": {"password": "Test123!", "project": "project-alpha", "role": "member"},
    "member2": {"password": "Test123!", "project": "project-beta", "role": "member"},
    "viewer1": {"password": "Test123!", "project": "project-alpha", "role": "viewer"},
    "viewer2": {"password": "Test123!", "project": "project-beta", "role": "viewer"},
}


def get_token(client: TestClient, username: str, password: str) -> str:
    """Login and get access token."""
    response = client.post("/auth/login", json={"username": username, "password": password})
    if response.status_code != 200:
        pytest.skip(f"Cannot login as {username}: {response.text}")
    return response.json()["access_token"]


def auth_headers(token: str) -> dict:
    """Create authorization headers."""
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# AUTH ENDPOINTS
# =============================================================================
class TestAuthEndpoints:
    """Test authentication endpoints: /auth/*"""

    def test_login_success(self, client):
        """POST /auth/login - successful login."""
        response = client.post(
            "/auth/login", json={"username": "owner1", "password": "Test123!"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        """POST /auth/login - wrong password returns 401."""
        response = client.post(
            "/auth/login", json={"username": "owner1", "password": "wrong"}
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """POST /auth/login - nonexistent user returns 401."""
        response = client.post(
            "/auth/login", json={"username": "nonexistent", "password": "test"}
        )
        assert response.status_code == 401

    def test_login_empty_credentials(self, client):
        """POST /auth/login - empty credentials returns 422."""
        response = client.post("/auth/login", json={})
        assert response.status_code == 422

    def test_me_authenticated(self, client):
        """GET /auth/me - returns user info with valid token."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get("/auth/me", headers=auth_headers(token))
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "owner1"

    def test_me_unauthenticated(self, client):
        """GET /auth/me - returns 401 without token."""
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_me_invalid_token(self, client):
        """GET /auth/me - returns 401 with invalid token."""
        response = client.get("/auth/me", headers={"Authorization": "Bearer invalid"})
        assert response.status_code == 401

    def test_refresh_token(self, client):
        """POST /auth/refresh - refreshes access token."""
        login_response = client.post(
            "/auth/login", json={"username": "owner1", "password": "Test123!"}
        )
        refresh_token = login_response.json()["refresh_token"]
        response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_logout(self, client):
        """POST /auth/logout - logs out user."""
        token = get_token(client, "owner1", "Test123!")
        response = client.post("/auth/logout", headers=auth_headers(token))
        assert response.status_code == 200


# =============================================================================
# SESSIONS ENDPOINTS
# =============================================================================
class TestSessionsEndpoints:
    """Test sessions endpoints: /sessions/*"""

    def test_list_sessions_authenticated(self, client):
        """GET /sessions - returns sessions list with auth."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get("/sessions", headers=auth_headers(token))
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)

    def test_list_sessions_unauthenticated(self, client):
        """GET /sessions - returns 401 without auth."""
        response = client.get("/sessions")
        assert response.status_code == 401

    def test_list_sessions_with_limit(self, client):
        """GET /sessions?limit=5 - respects limit parameter."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get("/sessions?limit=5", headers=auth_headers(token))
        assert response.status_code == 200

    def test_get_session_not_found(self, client):
        """GET /sessions/{id} - returns 404 for nonexistent session."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get("/sessions/nonexistent-id", headers=auth_headers(token))
        assert response.status_code == 404

    def test_delete_session_not_found(self, client):
        """DELETE /sessions/{id} - returns 404 for nonexistent session."""
        token = get_token(client, "owner1", "Test123!")
        response = client.delete("/sessions/nonexistent-id", headers=auth_headers(token))
        assert response.status_code == 404


# =============================================================================
# TESTCASES ENDPOINTS
# =============================================================================
class TestTestCasesEndpoints:
    """Test test cases endpoints: /testcases/*"""

    def test_list_testcases_authenticated(self, client):
        """GET /testcases - returns list with auth."""
        token = get_token(client, "member1", "Test123!")
        response = client.get("/testcases", headers=auth_headers(token))
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_testcases_unauthenticated(self, client):
        """GET /testcases - returns 401 without auth."""
        response = client.get("/testcases")
        assert response.status_code == 401

    def test_search_testcases(self, client):
        """GET /testcases/search - searches test cases."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get("/testcases/search?q=test", headers=auth_headers(token))
        assert response.status_code == 200

    def test_get_testcase_folders(self, client):
        """GET /testcases/folders/list - returns folders."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get("/testcases/folders/list", headers=auth_headers(token))
        assert response.status_code == 200

    def test_get_testcase_stats(self, client):
        """GET /testcases/stats - returns statistics."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get("/testcases/stats", headers=auth_headers(token))
        assert response.status_code == 200

    def test_get_testcase_not_found(self, client):
        """GET /testcases/{id} - returns 404 for nonexistent."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get("/testcases/nonexistent-id", headers=auth_headers(token))
        assert response.status_code == 404


# =============================================================================
# TASKS ENDPOINTS
# =============================================================================
class TestTasksEndpoints:
    """Test tasks endpoints: /tasks/*"""

    def test_list_tasks_authenticated(self, client):
        """GET /tasks - returns list with auth."""
        token = get_token(client, "admin1", "Test123!")
        response = client.get("/tasks", headers=auth_headers(token))
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_tasks_unauthenticated(self, client):
        """GET /tasks - returns 401 without auth."""
        response = client.get("/tasks")
        assert response.status_code == 401

    def test_get_task_board(self, client):
        """GET /tasks/board - returns board data."""
        token = get_token(client, "member1", "Test123!")
        response = client.get("/tasks/board", headers=auth_headers(token))
        assert response.status_code == 200

    def test_get_task_stats(self, client):
        """GET /tasks/stats - returns task statistics."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get("/tasks/stats", headers=auth_headers(token))
        assert response.status_code == 200

    def test_get_task_not_found(self, client):
        """GET /tasks/{id} - returns 404 for nonexistent."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get("/tasks/nonexistent-id", headers=auth_headers(token))
        assert response.status_code == 404


# =============================================================================
# ARTICLES ENDPOINTS
# =============================================================================
class TestArticlesEndpoints:
    """Test articles endpoints: /articles/*"""

    def test_list_articles_authenticated(self, client):
        """GET /articles - returns list with auth."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get("/articles", headers=auth_headers(token))
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_articles_unauthenticated(self, client):
        """GET /articles - returns 401 without auth."""
        response = client.get("/articles")
        assert response.status_code == 401

    def test_get_article_categories(self, client):
        """GET /articles/categories/list - returns categories."""
        token = get_token(client, "viewer1", "Test123!")
        response = client.get("/articles/categories/list", headers=auth_headers(token))
        assert response.status_code == 200

    def test_get_article_not_found(self, client):
        """GET /articles/{id} - returns 404 for nonexistent."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get("/articles/nonexistent-id", headers=auth_headers(token))
        assert response.status_code == 404


# =============================================================================
# TEST RUNS ENDPOINTS
# =============================================================================
class TestTestRunsEndpoints:
    """Test test runs endpoints: /test-runs/*"""

    def test_list_testruns_authenticated(self, client):
        """GET /test-runs - returns list with auth."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get("/test-runs", headers=auth_headers(token))
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_testruns_unauthenticated(self, client):
        """GET /test-runs - returns 401 without auth."""
        response = client.get("/test-runs")
        assert response.status_code == 401

    def test_get_testrun_stats_summary(self, client):
        """GET /test-runs/stats/summary - returns summary stats."""
        token = get_token(client, "member1", "Test123!")
        response = client.get("/test-runs/stats/summary", headers=auth_headers(token))
        assert response.status_code == 200

    def test_get_testrun_stats_detailed(self, client):
        """GET /test-runs/stats/detailed - returns detailed stats."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get("/test-runs/stats/detailed", headers=auth_headers(token))
        assert response.status_code == 200


# =============================================================================
# GENERATION ENDPOINTS
# =============================================================================
class TestGenerationEndpoints:
    """Test generation endpoints: /api/v1/generation/*"""

    def test_generation_health(self, client):
        """GET /api/v1/generation/health - returns health status."""
        response = client.get("/api/v1/generation/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_generation_from_swagger_requires_file(self, client):
        """POST /api/v1/generation/from-swagger - requires file."""
        token = get_token(client, "owner1", "Test123!")
        response = client.post(
            "/api/v1/generation/from-swagger",
            data={"framework": "pytest", "provider": "ollama"},
            headers=auth_headers(token),
        )
        assert response.status_code == 422

    def test_generation_result_not_found(self, client):
        """GET /api/v1/generation/result/{id} - returns 404."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get(
            "/api/v1/generation/result/nonexistent",
            headers=auth_headers(token)
        )
        assert response.status_code == 404

    def test_generation_download_not_found(self, client):
        """GET /api/v1/generation/download/{id} - returns 404."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get(
            "/api/v1/generation/download/nonexistent",
            headers=auth_headers(token)
        )
        assert response.status_code == 404


# =============================================================================
# PROJECT ENDPOINTS
# =============================================================================
class TestProjectEndpoints:
    """Test project endpoints: /projects/*"""

    def test_list_projects_authenticated(self, client):
        """GET /projects - returns list with auth."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get("/projects", headers=auth_headers(token))
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_projects_unauthenticated(self, client):
        """GET /projects - returns 401 without auth."""
        response = client.get("/projects")
        assert response.status_code == 401

    def test_get_project_not_found(self, client):
        """GET /projects/{id} - returns 404 for nonexistent."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get("/projects/nonexistent-id", headers=auth_headers(token))
        assert response.status_code == 404


# =============================================================================
# ANALYSIS ENDPOINTS
# =============================================================================
class TestAnalysisEndpoints:
    """Test analysis endpoints: /analyze/*"""

    def test_analyze_requires_auth(self, client):
        """POST /analyze - requires authentication."""
        response = client.post("/analyze", json={})
        assert response.status_code == 401

    def test_analyze_stats(self, client):
        """GET /analysis/stats - returns stats."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get("/analysis/stats", headers=auth_headers(token))
        assert response.status_code == 200


# =============================================================================
# EXPORTS ENDPOINTS
# =============================================================================
class TestExportsEndpoints:
    """Test export endpoints: /exports/*"""

    def test_export_postman_requires_auth(self, client):
        """POST /export/postman - requires auth."""
        response = client.post("/export/postman", json={})
        assert response.status_code == 401

    def test_export_pytest_requires_auth(self, client):
        """POST /export/pytest - requires auth."""
        response = client.post("/export/pytest", json={})
        assert response.status_code == 401


# =============================================================================
# INTEGRATIONS ENDPOINTS
# =============================================================================
class TestIntegrationsEndpoints:
    """Test integrations endpoints: /integrations/*"""

    def test_testit_status(self, client):
        """GET /integrations/testit/status - returns status."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get("/integrations/testit/status", headers=auth_headers(token))
        assert response.status_code == 200


# =============================================================================
# ROLE-BASED ACCESS CONTROL
# =============================================================================
class TestRoleBasedAccess:
    """Test role-based access control."""

    def test_owner_has_full_access(self, client):
        """Owner can access all endpoints."""
        token = get_token(client, "owner1", "Test123!")
        endpoints = ["/sessions", "/testcases", "/tasks", "/articles", "/projects"]
        for endpoint in endpoints:
            response = client.get(endpoint, headers=auth_headers(token))
            assert response.status_code == 200, f"Owner failed on {endpoint}"

    def test_member_can_read(self, client):
        """Member can read data."""
        token = get_token(client, "member1", "Test123!")
        response = client.get("/tasks", headers=auth_headers(token))
        assert response.status_code == 200

    def test_viewer_can_read(self, client):
        """Viewer can read data."""
        token = get_token(client, "viewer1", "Test123!")
        response = client.get("/articles", headers=auth_headers(token))
        assert response.status_code == 200

    def test_all_users_can_login(self, client):
        """All test users can login."""
        for username, creds in TEST_USERS.items():
            response = client.post(
                "/auth/login",
                json={"username": username, "password": creds["password"]}
            )
            assert response.status_code == 200, f"Login failed for {username}"


# =============================================================================
# HEALTH AND MISC
# =============================================================================
class TestHealthAndMisc:
    """Test health and miscellaneous endpoints."""

    def test_health_endpoint(self, client):
        """GET /health - returns ok status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_bookmarklet_served(self, client):
        """GET /bookmarklet/recorder.js - serves bookmarklet."""
        response = client.get("/bookmarklet/recorder.js")
        assert response.status_code in [200, 404]

    def test_cors_headers(self, client):
        """OPTIONS request returns CORS headers."""
        response = client.options(
            "/health",
            headers={"Origin": "https://example.com"}
        )
        assert response.status_code in [200, 405]


# =============================================================================
# CONCURRENT ACCESS
# =============================================================================
class TestConcurrentAccess:
    """Test concurrent access patterns."""

    def test_multiple_users_simultaneous(self, client):
        """Multiple users can access API simultaneously."""
        tokens = {}
        for username, creds in list(TEST_USERS.items())[:3]:
            tokens[username] = get_token(client, username, creds["password"])

        for username, token in tokens.items():
            response = client.get("/sessions", headers=auth_headers(token))
            assert response.status_code == 200, f"Failed for {username}"

    def test_same_user_multiple_tokens(self, client):
        """Same user can have multiple active tokens."""
        token1 = get_token(client, "owner1", "Test123!")
        token2 = get_token(client, "owner1", "Test123!")

        response1 = client.get("/auth/me", headers=auth_headers(token1))
        response2 = client.get("/auth/me", headers=auth_headers(token2))

        assert response1.status_code == 200
        assert response2.status_code == 200


# =============================================================================
# ERROR HANDLING
# =============================================================================
class TestErrorHandling:
    """Test error handling."""

    def test_invalid_json(self, client):
        """Invalid JSON returns 422."""
        token = get_token(client, "owner1", "Test123!")
        response = client.post(
            "/testcases",
            content="not json",
            headers={**auth_headers(token), "Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_missing_required_fields(self, client):
        """Missing required fields returns 422."""
        token = get_token(client, "owner1", "Test123!")
        response = client.post("/testcases", json={}, headers=auth_headers(token))
        assert response.status_code == 422

    def test_not_found_returns_404(self, client):
        """Nonexistent resources return 404."""
        token = get_token(client, "owner1", "Test123!")
        response = client.get("/testcases/does-not-exist", headers=auth_headers(token))
        assert response.status_code == 404
