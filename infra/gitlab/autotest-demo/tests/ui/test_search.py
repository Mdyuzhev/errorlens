import allure
import pytest

pytestmark = [
    allure.feature("Search"),
    allure.story("Full-text search"),
]


class TestSearch:
    """Search functionality tests."""

    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.smoke
    def test_search_returns_results(self, http_session, base_url):
        """Search with keyword returns matching results."""
        response = http_session.get(f"{base_url}/get", params={"q": "laptop"})
        assert response.status_code == 200
        assert response.json()["args"]["q"] == "laptop"

    @allure.severity(allure.severity_level.MINOR)
    def test_search_empty_query(self, http_session, base_url):
        """Search without query returns valid response."""
        response = http_session.get(f"{base_url}/get")
        assert response.status_code == 200

    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("query", [
        "hello world",
        "test@mail.com",
        "price > 100",
    ])
    def test_search_special_characters(self, http_session, base_url, query):
        """Search with special characters is handled correctly."""
        response = http_session.get(f"{base_url}/anything", params={"q": query})
        assert response.status_code == 200
        assert response.json()["args"]["q"] == query
