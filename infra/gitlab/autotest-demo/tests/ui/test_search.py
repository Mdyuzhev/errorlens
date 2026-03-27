import errorlens as el
import pytest


@el.feature("Search")
@el.story("Full-text search")
class TestSearch:
    """Search functionality tests."""

    @el.severity("normal")
    @pytest.mark.smoke
    def test_search_returns_results(self, http_session, base_url):
        """Search with keyword returns matching results."""
        response = http_session.get(f"{base_url}/get", params={"q": "laptop"})
        assert response.status_code == 200
        assert response.json()["args"]["q"] == "laptop"

    @el.severity("minor")
    def test_search_empty_query(self, http_session, base_url):
        """Search without query returns valid response."""
        response = http_session.get(f"{base_url}/get")
        assert response.status_code == 200

    @el.severity("normal")
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
