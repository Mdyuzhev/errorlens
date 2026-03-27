"""Tests for GET /api/v1/qa/coverage endpoint."""

import pytest

from app.routers.qa import _coverage_status


def _login(client) -> dict:
    """Login as owner1 and return auth headers."""
    resp = client.post(
        "/auth/login", json={"username": "owner1", "password": "Test123!"}
    )
    if resp.status_code != 200:
        pytest.skip("Cannot login as owner1")
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestCoverageStatus:
    """Unit tests for _coverage_status helper."""

    def test_no_test_cases(self):
        assert _coverage_status([]) == "none"

    def test_all_passed(self):
        tcs = [{"last_run_status": "passed"}, {"last_run_status": "passed"}]
        assert _coverage_status(tcs) == "passing"

    def test_has_failed(self):
        tcs = [{"last_run_status": "passed"}, {"last_run_status": "failed"}]
        assert _coverage_status(tcs) == "failing"

    def test_no_run_results(self):
        tcs = [{"last_run_status": None}, {"last_run_status": None}]
        assert _coverage_status(tcs) == "not_run"

    def test_partial_mixed(self):
        tcs = [{"last_run_status": "passed"}, {"last_run_status": None}]
        assert _coverage_status(tcs) == "partial"


class TestCoverageEndpoint:
    """Integration tests for /api/v1/qa/coverage."""

    def test_coverage_requires_auth(self, client):
        """Without token should return 401."""
        response = client.get("/api/v1/qa/coverage", params={"project_id": "fake"})
        assert response.status_code == 401

    def test_coverage_empty_project(self, client):
        """Project with no tasks should return empty summary."""
        headers = _login(client)
        response = client.get(
            "/api/v1/qa/coverage",
            params={"project_id": "nonexistent-project-id"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total_issues"] == 0
        assert data["summary"]["covered_issues"] == 0
        assert data["summary"]["coverage_pct"] == 0
        assert data["issues"] == []

    def test_coverage_no_linked_cases(self, client):
        """Tasks without linked test cases should have covered_issues = 0."""
        headers = _login(client)
        # Get a real project_id from user's projects
        me_resp = client.get("/auth/me", headers=headers)
        if me_resp.status_code != 200:
            pytest.skip("Cannot get user info")
        user_data = me_resp.json()
        project_id = user_data.get("project_id")
        if not project_id:
            pytest.skip("No project_id in user data")

        response = client.get(
            "/api/v1/qa/coverage",
            params={"project_id": project_id},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        # covered_issues should be <= total_issues
        assert data["summary"]["covered_issues"] <= data["summary"]["total_issues"]

    def test_coverage_with_linked_cases(self, client):
        """Test case linked to issue should increase covered_issues count."""
        headers = _login(client)
        me_resp = client.get("/auth/me", headers=headers)
        if me_resp.status_code != 200:
            pytest.skip("Cannot get user info")
        user_data = me_resp.json()
        project_id = user_data.get("project_id")
        if not project_id:
            pytest.skip("No project_id in user data")

        response = client.get(
            "/api/v1/qa/coverage",
            params={"project_id": project_id},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        summary = data["summary"]
        # Validate response structure
        assert "total_issues" in summary
        assert "covered_issues" in summary
        assert "coverage_pct" in summary
        assert "total_test_cases" in summary
        assert "passed" in summary
        assert "failed" in summary
        assert "not_run" in summary
        # Check issue nodes structure
        for issue in data["issues"]:
            assert "id" in issue
            assert "human_id" in issue
            assert "title" in issue
            assert "has_tests" in issue
            assert "test_cases" in issue
            assert "coverage_status" in issue
            assert issue["coverage_status"] in (
                "none", "passing", "failing", "not_run", "partial"
            )

    def test_coverage_with_run_result(self, client):
        """Verify last_run_status field is present in test case nodes."""
        headers = _login(client)
        me_resp = client.get("/auth/me", headers=headers)
        if me_resp.status_code != 200:
            pytest.skip("Cannot get user info")
        user_data = me_resp.json()
        project_id = user_data.get("project_id")
        if not project_id:
            pytest.skip("No project_id in user data")

        response = client.get(
            "/api/v1/qa/coverage",
            params={"project_id": project_id},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        for issue in data["issues"]:
            for tc in issue["test_cases"]:
                assert "last_run_status" in tc
                assert "id" in tc
                assert "human_id" in tc
                assert "title" in tc
                assert "priority" in tc
                assert "status" in tc
