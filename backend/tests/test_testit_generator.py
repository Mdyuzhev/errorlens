"""Tests for TestIt generator."""

import json

import pytest
from app.generators.testit import TestItGenerator, generate_testit_testcase


@pytest.fixture
def sample_session():
    """Sample session data with recorded requests."""
    return {
        "id": "test-session-123",
        "url": "https://example.com",
        "recorded_requests": [
            {
                "request": {
                    "method": "POST",
                    "url": "https://example.com/api/login",
                    "headers": {"Content-Type": "application/json"},
                    "body": '{"username": "test", "password": "secret"}',
                },
                "response": {
                    "status": 200,
                    "headers": {},
                    "body": '{"token": "abc123"}',
                },
            },
            {
                "request": {
                    "method": "GET",
                    "url": "https://example.com/api/orders",
                    "headers": {"Authorization": "Bearer abc123"},
                    "body": "",
                },
                "response": {
                    "status": 200,
                    "headers": {},
                    "body": "[]",
                },
            },
        ],
        "has_errors": False,
    }


@pytest.fixture
def sample_session_with_errors():
    """Sample session with error responses."""
    return {
        "id": "test-session-456",
        "url": "https://example.com",
        "recorded_requests": [
            {
                "request": {
                    "method": "POST",
                    "url": "https://example.com/api/orders",
                    "headers": {"Content-Type": "application/json"},
                    "body": '{"product_id": 999}',
                },
                "response": {
                    "status": 404,
                    "headers": {},
                    "body": '{"error": "Product not found"}',
                },
            },
        ],
        "has_errors": True,
    }


@pytest.fixture
def sample_analysis():
    """Sample AI analysis result."""
    return {
        "summary": "Проверка авторизации и получения заказов",
        "probable_cause": "Тест бизнес-сценария авторизации",
        "severity": "medium",
    }


class TestTestItGenerator:
    """Test suite for TestItGenerator class."""

    def test_generate_basic_structure(self, sample_session):
        """Test that generator produces correct basic structure."""
        generator = TestItGenerator(sample_session)
        result = generator.generate()

        assert "name" in result
        assert "description" in result
        assert "state" in result
        assert "priority" in result
        assert "preconditions" in result
        assert "postconditions" in result
        assert "steps" in result
        assert "tags" in result
        assert "automationStatus" in result

    def test_generate_steps_from_requests(self, sample_session):
        """Test that each request generates a test step."""
        generator = TestItGenerator(sample_session)
        result = generator.generate()

        # Should have 2 steps for 2 requests
        assert len(result["steps"]) == 2

        # First step should be for login
        first_step = result["steps"][0]
        assert "action" in first_step
        assert "expected" in first_step
        assert "testData" in first_step
        assert "POST" in first_step["action"]
        assert "/api/login" in first_step["action"]

    def test_password_masking(self, sample_session):
        """Test that passwords are masked in test data."""
        generator = TestItGenerator(sample_session)
        result = generator.generate()

        first_step = result["steps"][0]
        # Password should be masked
        assert "secret" not in first_step["testData"]
        assert "***" in first_step["testData"]

    def test_auto_detect_auth_precondition(self, sample_session):
        """Test that auth is detected from Authorization header."""
        generator = TestItGenerator(sample_session)
        result = generator.generate()

        # Should detect auth from Authorization header
        assert (
            "авторизован" in result["preconditions"].lower()
            or "Базовый URL" in result["preconditions"]
        )

    def test_tags_include_auth(self, sample_session):
        """Test that auth tag is added for login endpoints."""
        generator = TestItGenerator(sample_session)
        result = generator.generate()

        assert "api" in result["tags"]
        assert "auth" in result["tags"]

    def test_postconditions_with_errors(self, sample_session_with_errors):
        """Test that postconditions reflect errors."""
        generator = TestItGenerator(sample_session_with_errors)
        result = generator.generate()

        assert "ошибка" in result["postconditions"].lower()

    def test_postconditions_success(self, sample_session):
        """Test that postconditions reflect success."""
        generator = TestItGenerator(sample_session)
        result = generator.generate()

        assert "успешно" in result["postconditions"].lower()


class TestPriorityMapping:
    """Test priority mapping from severity."""

    @pytest.mark.parametrize(
        "severity,expected_priority",
        [
            ("critical", "Highest"),
            ("high", "High"),
            ("medium", "Medium"),
            ("low", "Low"),
        ],
    )
    def test_priority_mapping(self, sample_session, severity, expected_priority):
        """Test that severity maps to correct priority."""
        analysis = {"severity": severity}
        generator = TestItGenerator(sample_session, analysis)
        result = generator.generate()
        assert result["priority"] == expected_priority


class TestOutputFormats:
    """Test different output formats."""

    def test_generate_json(self, sample_session, sample_analysis):
        """Test JSON output format."""
        result = generate_testit_testcase(sample_session, sample_analysis, "json")

        # Should be valid JSON
        parsed = json.loads(result)
        assert "testCases" in parsed
        assert len(parsed["testCases"]) == 1
        assert "name" in parsed["testCases"][0]
        assert "steps" in parsed["testCases"][0]
        assert "source" in parsed
        assert parsed["source"] == "ErrorLens"

    def test_generate_xml(self, sample_session, sample_analysis):
        """Test XML output format."""
        result = generate_testit_testcase(sample_session, sample_analysis, "xml")

        # Should be valid XML
        assert '<?xml version="1.0"' in result
        assert "<testCases>" in result
        assert "<testCase>" in result
        assert "<step position=" in result
        assert "<name>" in result
        assert "</testCases>" in result

    def test_generate_markdown(self, sample_session, sample_analysis):
        """Test Markdown output format."""
        result = generate_testit_testcase(sample_session, sample_analysis, "markdown")

        # Should contain markdown elements
        assert "# " in result
        assert "## Шаги" in result
        assert "| # |" in result
        assert "**Приоритет:**" in result
        assert "ErrorLens" in result


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_requests(self):
        """Test handling of empty requests."""
        session = {
            "id": "empty",
            "url": "https://example.com",
            "recorded_requests": [],
            "has_errors": False,
        }
        generator = TestItGenerator(session)
        result = generator.generate()

        assert result["steps"] == []
        assert result["automationStatus"] == "NotAutomated"

    def test_missing_response(self):
        """Test handling of missing response."""
        session = {
            "id": "no-response",
            "url": "https://example.com",
            "recorded_requests": [
                {
                    "request": {
                        "method": "GET",
                        "url": "https://example.com/api/test",
                        "headers": {},
                        "body": "",
                    },
                    "response": {},
                }
            ],
            "has_errors": False,
        }
        generator = TestItGenerator(session)
        result = generator.generate()

        assert len(result["steps"]) == 1

    def test_long_body_truncation(self):
        """Test that long request bodies are truncated."""
        long_body = '{"data": "' + "x" * 600 + '"}'
        session = {
            "id": "long-body",
            "url": "https://example.com",
            "recorded_requests": [
                {
                    "request": {
                        "method": "POST",
                        "url": "https://example.com/api/test",
                        "headers": {},
                        "body": long_body,
                    },
                    "response": {"status": 200},
                }
            ],
            "has_errors": False,
        }
        generator = TestItGenerator(session)
        result = generator.generate()

        # Body should be truncated
        assert len(result["steps"][0]["testData"]) <= 510  # 500 + "..."

    def test_title_with_analysis_summary(self, sample_session, sample_analysis):
        """Test that title uses analysis summary."""
        generator = TestItGenerator(sample_session, sample_analysis)
        result = generator.generate()

        assert "Проверка:" in result["name"]
        assert "авторизации" in result["name"]

    def test_title_without_analysis(self, sample_session):
        """Test that title is generated from requests when no analysis."""
        generator = TestItGenerator(sample_session, None)
        result = generator.generate()

        assert "Тест:" in result["name"]


class TestEntityDetection:
    """Test entity detection from URL paths."""

    @pytest.mark.parametrize(
        "url,expected_entity",
        [
            ("https://example.com/api/users", "пользователь"),
            ("https://example.com/api/orders/123", "заказ"),
            ("https://example.com/api/products", "товар"),
            ("https://example.com/api/login", "авторизация"),
            ("https://example.com/api/cart", "корзина"),
            ("https://example.com/api/pet/1", "питомец"),
        ],
    )
    def test_entity_detection(self, url, expected_entity):
        """Test that correct entity is detected from URL."""
        session = {
            "id": "entity-test",
            "url": "https://example.com",
            "recorded_requests": [
                {
                    "request": {
                        "method": "GET",
                        "url": url,
                        "headers": {},
                        "body": "",
                    },
                    "response": {"status": 200},
                }
            ],
            "has_errors": False,
        }
        generator = TestItGenerator(session)
        result = generator.generate()

        assert expected_entity in result["steps"][0]["action"]
