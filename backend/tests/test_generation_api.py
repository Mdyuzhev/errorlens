"""Tests for Generation API endpoints."""
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.generators.llm_generator import GenerationResult, GeneratedTest

client = TestClient(app)


@pytest.fixture
def mock_swagger_spec():
    """Minimal valid Swagger spec."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "responses": {"200": {"description": "OK"}}
                }
            }
        }
    }


@pytest.fixture
def mock_generation_result():
    """Mock successful generation result."""
    return GenerationResult(
        tests=[
            GeneratedTest(
                endpoint="GET /users",
                code="def test_get_users():\n    pass",
                is_valid=True
            )
        ],
        conftest="import pytest\n",
        total_endpoints=1,
        successful=1,
        failed=0,
        errors=[]
    )


class TestGenerationHealthEndpoint:
    """Tests for /v1/generation/health endpoint."""

    def test_health_check(self):
        """Health endpoint returns ok status."""
        response = client.get("/v1/generation/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestGenerateFromSwagger:
    """Tests for /v1/generation/from-swagger endpoint."""

    @patch("app.routers.generation.publish", new_callable=AsyncMock)
    @patch("app.services.generation_service.GenerationService.create_task")
    def test_upload_valid_swagger_json(self, mock_create_task, mock_publish, mock_swagger_spec):
        """Upload valid Swagger JSON creates task."""
        mock_create_task.return_value = "test-task-id"

        response = client.post(
            "/v1/generation/from-swagger",
            files={"file": ("swagger.json", json.dumps(mock_swagger_spec), "application/json")},
            data={"framework": "pytest", "provider": "anthropic"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-id"
        assert data["websocket_url"] == "/ws/generation/test-task-id"
        mock_create_task.assert_called_once()

    def test_upload_invalid_swagger(self):
        """Upload invalid Swagger returns 400."""
        invalid_spec = {"openapi": "3.0.0"}  # Missing 'paths'

        response = client.post(
            "/v1/generation/from-swagger",
            files={"file": ("swagger.json", json.dumps(invalid_spec), "application/json")},
            data={"framework": "pytest"}
        )

        assert response.status_code == 400
        assert "missing 'paths'" in response.json()["detail"]

    @patch("app.routers.generation.publish", new_callable=AsyncMock)
    @patch("app.services.generation_service.GenerationService.create_task")
    def test_upload_swagger_yaml(self, mock_create_task, mock_publish, mock_swagger_spec):
        """Upload Swagger YAML is parsed correctly."""
        mock_create_task.return_value = "yaml-task-id"

        yaml_content = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      summary: List users
      responses:
        '200':
          description: OK
"""

        response = client.post(
            "/v1/generation/from-swagger",
            files={"file": ("swagger.yaml", yaml_content, "application/yaml")},
            data={"framework": "pytest", "provider": "openai", "model": "gpt-4"}
        )

        assert response.status_code == 200
        assert response.json()["task_id"] == "yaml-task-id"


class TestGetResult:
    """Tests for /v1/generation/result/{result_id} endpoint."""

    @patch("app.services.generation_service.GenerationService.get_result")
    def test_get_existing_result(self, mock_get_result, mock_generation_result):
        """Get result returns generation data."""
        mock_get_result.return_value = mock_generation_result

        response = client.get("/v1/generation/result/test-result-id")

        assert response.status_code == 200
        data = response.json()
        assert data["total_endpoints"] == 1
        assert data["successful"] == 1
        assert data["failed"] == 0
        assert len(data["tests"]) == 1
        assert data["tests"][0]["endpoint"] == "GET /users"
        assert data["conftest"] == "import pytest\n"

    @patch("app.services.generation_service.GenerationService.get_result")
    def test_get_nonexistent_result(self, mock_get_result):
        """Get nonexistent result returns 404."""
        mock_get_result.return_value = None

        response = client.get("/v1/generation/result/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestDownloadResult:
    """Tests for /v1/generation/download/{result_id} endpoint."""

    @patch("app.services.generation_service.GenerationService.get_result")
    def test_download_valid_result(self, mock_get_result, mock_generation_result):
        """Download result returns ZIP archive."""
        mock_get_result.return_value = mock_generation_result

        response = client.get("/v1/generation/download/test-result-id")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "attachment" in response.headers["content-disposition"]
        assert "tests_test-res" in response.headers["content-disposition"]

    @patch("app.services.generation_service.GenerationService.get_result")
    def test_download_nonexistent_result(self, mock_get_result):
        """Download nonexistent result returns 404."""
        mock_get_result.return_value = None

        response = client.get("/v1/generation/download/nonexistent")

        assert response.status_code == 404
