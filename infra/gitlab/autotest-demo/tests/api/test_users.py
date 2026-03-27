import random

import errorlens as el
import pytest


@el.feature("User Management")
class TestUsers:
    """User management API tests."""

    @el.story("User info")
    @el.severity("normal")
    def test_get_user_info(self, http_session, base_url):
        """GET user info with custom User-Agent."""
        http_session.headers["User-Agent"] = "ErrorLens-Autotest/1.0"
        response = http_session.get(f"{base_url}/get")
        assert response.status_code == 200

        with el.step("Attach response"):
            el.attach("API Response", response.text)

    @el.story("User creation")
    @el.severity("critical")
    @pytest.mark.parametrize("role", ["admin", "manager", "viewer"])
    def test_create_user_parametrized(self, http_session, base_url, faker_ru, role):
        """POST create user with different roles."""
        payload = {
            "name": faker_ru.name(),
            "email": faker_ru.email(),
            "role": role,
        }
        response = http_session.post(f"{base_url}/post", json=payload)
        assert response.status_code == 200
        assert response.json()["json"]["role"] == role

    @el.story("User update")
    @el.severity("normal")
    def test_update_user_email(self, http_session, base_url, faker_ru):
        """PUT update user email."""
        payload = {"email": faker_ru.email()}

        with el.step("Prepare payload"):
            el.attach("Payload", str(payload))

        with el.step("Send request"):
            response = http_session.put(f"{base_url}/put", json=payload)

        with el.step("Verify response"):
            assert response.status_code == 200
            assert response.json()["json"]["email"] == payload["email"]

    @el.story("User deletion")
    @el.severity("normal")
    def test_delete_nonexistent_user(self, http_session, base_url):
        """DELETE nonexistent user returns 404."""
        response = http_session.get(f"{base_url}/status/404")
        assert response.status_code == 404

    @el.story("User list")
    @el.severity("minor")
    @pytest.mark.flaky
    def test_user_list_pagination(self, http_session, base_url):
        """Intentionally flaky test (~40% failure rate)."""
        response = http_session.get(f"{base_url}/get", params={"page": 1, "limit": 20})
        assert response.status_code == 200
        if random.random() < 0.4:
            raise AssertionError("Pagination timeout")
