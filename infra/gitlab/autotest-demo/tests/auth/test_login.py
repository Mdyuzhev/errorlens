import allure
import pytest


@allure.feature("Authentication")
class TestLogin:
    """Authentication tests using httpbin.org as HTTP backend."""

    @allure.story("Basic HTTP")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.smoke
    def test_successful_get_request(self, http_session, base_url):
        """GET request with query parameters returns 200."""
        response = http_session.get(
            f"{base_url}/get",
            params={"user": "testuser", "role": "admin"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["args"]["user"] == "testuser"
        assert data["args"]["role"] == "admin"

    @allure.story("POST requests")
    @allure.severity(allure.severity_level.NORMAL)
    def test_post_with_json_body(self, http_session, base_url, faker_ru):
        """POST with JSON body echoes back correctly."""
        payload = {"username": faker_ru.user_name(), "email": faker_ru.email()}

        with allure.step("Send POST request"):
            response = http_session.post(f"{base_url}/post", json=payload)

        with allure.step("Verify response body"):
            assert response.status_code == 200
            assert response.json()["json"] == payload

    @allure.story("Authorization")
    @allure.severity(allure.severity_level.NORMAL)
    def test_auth_headers(self, http_session, base_url):
        """Authorization header is forwarded correctly."""
        http_session.headers["Authorization"] = "Bearer test-token"
        response = http_session.get(f"{base_url}/headers")
        assert response.status_code == 200
        headers = response.json()["headers"]
        assert "Bearer test-token" in headers.get("Authorization", "")

    @allure.story("Authorization")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_invalid_auth_returns_401(self, http_session, base_url):
        """Request to /status/401 returns 401."""
        response = http_session.get(f"{base_url}/status/401")
        assert response.status_code == 401

    @allure.story("Negative cases")
    @allure.severity(allure.severity_level.MINOR)
    def test_login_with_wrong_password(self, http_session, base_url):
        """Intentionally failing test for defect categorization demo."""
        response = http_session.get(f"{base_url}/get")
        assert response.status_code == 999, (
            f"Expected 999, got {response.status_code}"
        )
