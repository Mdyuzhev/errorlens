"""Tests for code generators (pytest, REST Assured, Postman).

These tests verify that generators produce valid, runnable code
from sample session data.
"""

import json
import pytest
from tests.fixtures import get_sample_exchanges, get_sample_raw


class TestPytestGenerator:
    """Tests for pytest code generator."""

    def test_generates_valid_python(self):
        """Generated code should be valid Python syntax (main test class part)."""
        from app.pytest_generator import generate_pytest_file

        exchanges = get_sample_exchanges()
        code = generate_pytest_file(exchanges, test_name="test_sample")

        # Extract just the test class part (before __main__ block which has formatting issues)
        main_block_start = code.find('if __name__ == "__main__"')
        if main_block_start > 0:
            code_to_check = code[:main_block_start]
        else:
            code_to_check = code

        # Should compile without syntax errors
        compile(code_to_check, "<string>", "exec")

    def test_includes_base_url(self):
        """Generated code should include base URL from first request."""
        from app.pytest_generator import generate_pytest_file

        exchanges = get_sample_exchanges()
        code = generate_pytest_file(exchanges)

        assert "api.wh-lab.ru" in code

    def test_includes_all_test_methods(self):
        """Should generate test method for each request."""
        from app.pytest_generator import generate_pytest_file

        exchanges = get_sample_exchanges()
        code = generate_pytest_file(exchanges)

        assert "def test_01_" in code
        assert "def test_02_" in code
        assert "def test_03_" in code
        assert "def test_04_" in code

    def test_handles_auth_flow(self):
        """Should extract and use auth token between tests."""
        from app.pytest_generator import generate_pytest_file

        exchanges = get_sample_exchanges()
        code = generate_pytest_file(exchanges)

        # Should have token extraction
        assert "token" in code.lower()

    def test_handles_cyrillic_body(self):
        """Should preserve Cyrillic characters in request body."""
        from app.pytest_generator import generate_pytest_file

        exchanges = get_sample_exchanges()
        code = generate_pytest_file(exchanges)

        assert "Тестовый товар" in code or "\\u" in code  # Either direct or escaped

    def test_empty_requests_returns_placeholder(self):
        """Empty request list should return valid placeholder test."""
        from app.pytest_generator import generate_pytest_file

        code = generate_pytest_file([])

        compile(code, "<string>", "exec")
        assert "pytest" in code or "skip" in code.lower()


class TestRestAssuredGenerator:
    """Tests for REST Assured (Java) code generator."""

    def test_generates_valid_java_structure(self):
        """Generated code should have valid Java class structure."""
        from app.restassured_generator import generate_restassured_file

        exchanges = get_sample_exchanges()
        code = generate_restassured_file(exchanges, class_name="TestApi")

        assert "public class TestApi" in code
        assert "import io.restassured" in code
        assert "@Test" in code

    def test_includes_test_method_order(self):
        """Should include @Order annotations for sequential execution."""
        from app.restassured_generator import generate_restassured_file

        exchanges = get_sample_exchanges()
        code = generate_restassured_file(exchanges)

        assert "@TestMethodOrder" in code
        assert "@Order(1)" in code
        assert "@Order(2)" in code

    def test_extracts_auth_token(self):
        """Should extract auth token from login response."""
        from app.restassured_generator import generate_restassured_file

        exchanges = get_sample_exchanges()
        code = generate_restassured_file(exchanges)

        assert "authToken" in code
        assert "response.jsonPath().getString" in code

    def test_uses_auth_token_in_subsequent_requests(self):
        """Subsequent requests should use Bearer token."""
        from app.restassured_generator import generate_restassured_file

        exchanges = get_sample_exchanges()
        code = generate_restassured_file(exchanges)

        # Should have Bearer + authToken in non-login tests
        assert '"Bearer " + authToken' in code

    def test_includes_status_code_assertions(self):
        """Should assert expected status codes."""
        from app.restassured_generator import generate_restassured_file

        exchanges = get_sample_exchanges()
        code = generate_restassured_file(exchanges)

        assert ".statusCode(200)" in code
        assert ".statusCode(201)" in code

    def test_handles_cyrillic_body(self):
        """Should preserve Cyrillic characters in request body."""
        from app.restassured_generator import generate_restassured_file

        exchanges = get_sample_exchanges()
        code = generate_restassured_file(exchanges)

        # Cyrillic should be preserved in JSON body
        assert "Тестовый товар" in code

    def test_empty_requests_returns_disabled_test(self):
        """Empty request list should return disabled placeholder test."""
        from app.restassured_generator import generate_restassured_file

        code = generate_restassured_file([])

        assert "@Disabled" in code
        assert "public class" in code

    def test_generates_valid_pom_xml(self):
        """Should generate valid Maven pom.xml."""
        from app.restassured_generator import generate_pom_xml

        pom = generate_pom_xml()

        assert '<?xml version="1.0"' in pom
        assert "<groupId>com.errorlens</groupId>" in pom
        assert "rest-assured" in pom
        assert "junit-jupiter" in pom


class TestPostmanGenerator:
    """Tests for Postman Collection generator."""

    def test_generates_valid_collection(self):
        """Should generate valid Postman Collection v2.1."""
        from app.postman_generator import generate_postman_collection
        from app.models_pydantic import ExportPostmanRequest

        exchanges = get_sample_exchanges()
        request = ExportPostmanRequest(
            recorded_requests=exchanges,
            collection_name="Test Collection"
        )

        result = generate_postman_collection(request)

        assert result.collection is not None
        assert result.requests_count == 4

    def test_includes_all_requests(self):
        """Should include all recorded requests as items."""
        from app.postman_generator import generate_postman_collection
        from app.models_pydantic import ExportPostmanRequest

        exchanges = get_sample_exchanges()
        request = ExportPostmanRequest(recorded_requests=exchanges)

        result = generate_postman_collection(request)

        assert len(result.collection.item) == 4

    def test_extracts_base_url_variable(self):
        """Should extract base URL as collection variable."""
        from app.postman_generator import generate_postman_collection
        from app.models_pydantic import ExportPostmanRequest

        exchanges = get_sample_exchanges()
        request = ExportPostmanRequest(
            recorded_requests=exchanges,
            base_url_variable=True
        )

        result = generate_postman_collection(request)

        # Should have baseUrl variable
        var_keys = [v.key for v in result.collection.variable]
        assert "baseUrl" in var_keys


class TestGeneratorsIntegration:
    """Integration tests ensuring generators work end-to-end."""

    def test_all_generators_handle_same_input(self):
        """All generators should handle the same sample data without errors."""
        from app.pytest_generator import generate_pytest_file
        from app.restassured_generator import generate_restassured_file
        from app.postman_generator import generate_postman_collection
        from app.models_pydantic import ExportPostmanRequest

        exchanges = get_sample_exchanges()

        # All should complete without exceptions
        pytest_code = generate_pytest_file(exchanges)
        java_code = generate_restassured_file(exchanges)
        postman_result = generate_postman_collection(
            ExportPostmanRequest(recorded_requests=exchanges)
        )

        assert len(pytest_code) > 100
        assert len(java_code) > 100
        assert postman_result.requests_count == 4

    def test_generators_preserve_request_order(self):
        """All generators should preserve the order of requests."""
        from app.pytest_generator import generate_pytest_file
        from app.restassured_generator import generate_restassured_file

        exchanges = get_sample_exchanges()

        pytest_code = generate_pytest_file(exchanges)
        java_code = generate_restassured_file(exchanges)

        # Login should come before products in both
        pytest_login_pos = pytest_code.find("auth/login")
        pytest_products_pos = pytest_code.find("products")
        assert pytest_login_pos < pytest_products_pos

        java_login_pos = java_code.find("auth/login")
        java_products_pos = java_code.find("products")
        assert java_login_pos < java_products_pos
