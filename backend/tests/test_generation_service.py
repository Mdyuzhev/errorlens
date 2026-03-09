"""Tests for GenerationService with Redis-backed storage."""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.generation_service import (
    GenerationService,
    TaskConfig,
    TASK_TTL,
    RESULT_TTL,
)


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    r = AsyncMock()
    r.ping.return_value = True
    r.setex.return_value = True
    r.get.return_value = None
    r.delete.return_value = 1
    r.publish.return_value = 1
    return r


@pytest.fixture(autouse=True)
def patch_redis(mock_redis):
    """Patch get_redis to return mock."""
    with patch(
        "app.services.generation_service.get_redis",
        new_callable=AsyncMock,
        return_value=mock_redis,
    ):
        yield mock_redis


@pytest.fixture
def mock_manager():
    """Mock WebSocket manager."""
    with patch("app.services.generation_service.manager") as m:
        m.send_started = AsyncMock(return_value=True)
        m.send_progress = AsyncMock(return_value=True)
        m.send_completed = AsyncMock(return_value=True)
        m.send_error = AsyncMock(return_value=True)
        yield m


class TestTaskCreation:
    """Tests for task creation in Redis."""

    @pytest.mark.asyncio
    async def test_create_task(self, patch_redis):
        """create_task stores config in Redis with TTL."""
        task_id = await GenerationService.create_task(
            "swagger", {"paths": {}}, "pytest", "anthropic", None
        )
        assert task_id is not None
        patch_redis.setex.assert_awaited_once()
        call_args = patch_redis.setex.call_args[0]
        assert f"el:task:{task_id}" == call_args[0]
        assert call_args[1] == TASK_TTL

    @pytest.mark.asyncio
    async def test_get_task_config(self, patch_redis):
        """get_task_config reads from Redis."""
        config = TaskConfig("swagger", {"paths": {}}, "pytest", "anthropic", None)
        patch_redis.get.return_value = config.to_json()

        result = await GenerationService.get_task_config("test-id")
        assert result is not None
        assert result.input_type == "swagger"

    @pytest.mark.asyncio
    async def test_get_task_config_not_found(self, patch_redis):
        """get_task_config returns None for missing task."""
        patch_redis.get.return_value = None
        result = await GenerationService.get_task_config("missing")
        assert result is None


class TestTaskExecution:
    """Tests for task execution."""

    @pytest.mark.asyncio
    async def test_task_removed_after_completion(self, patch_redis, mock_manager):
        """Task is deleted from Redis after run_task completes."""
        config = TaskConfig("swagger", {"paths": {"/test": {"get": {}}}}, "pytest", "anthropic", None)
        patch_redis.get.return_value = config.to_json()

        with patch("app.services.generation_service.LLMTestGenerator") as mock_gen:
            mock_gen.return_value.generate = AsyncMock(
                return_value=MagicMock(
                    total_endpoints=0, successful=0, failed=0, errors=[], tests=[], conftest=None
                )
            )
            with patch("app.services.generation_service.SwaggerInput") as mock_input:
                mock_input.return_value.to_endpoints.return_value = []
                await GenerationService.run_task("task-123")

        patch_redis.delete.assert_awaited()

    @pytest.mark.asyncio
    async def test_task_removed_on_error(self, patch_redis, mock_manager):
        """Task is deleted from Redis even on error."""
        config = TaskConfig("swagger", {"paths": {}}, "pytest", "anthropic", None)
        patch_redis.get.return_value = config.to_json()

        with patch("app.services.generation_service.LLMTestGenerator") as mock_gen:
            mock_gen.return_value.generate = AsyncMock(side_effect=Exception("LLM error"))
            with patch("app.services.generation_service.SwaggerInput") as mock_input:
                mock_input.return_value.to_endpoints.return_value = ["/test"]
                await GenerationService.run_task("task-err")

        patch_redis.delete.assert_awaited()
        mock_manager.send_error.assert_awaited()

    @pytest.mark.asyncio
    async def test_task_not_found(self, patch_redis, mock_manager):
        """Running non-existent task returns None."""
        patch_redis.get.return_value = None
        result = await GenerationService.run_task("nonexistent")
        assert result is None
        mock_manager.send_error.assert_awaited()


class TestResultStorage:
    """Tests for result storage."""

    @pytest.mark.asyncio
    async def test_store_result(self, patch_redis):
        """store_result writes serialized result to Redis."""
        mock_result = MagicMock()
        mock_result.total_endpoints = 2
        mock_result.successful = 1
        mock_result.failed = 1
        mock_result.errors = ["error"]
        mock_result.tests = []
        mock_result.conftest = "import pytest"

        await GenerationService.store_result("res-1", mock_result)

        call_args = patch_redis.setex.call_args[0]
        assert call_args[0] == "el:result:res-1"
        assert call_args[1] == RESULT_TTL
        data = json.loads(call_args[2])
        assert data["total_endpoints"] == 2
        assert data["conftest"] == "import pytest"

    @pytest.mark.asyncio
    async def test_get_result(self, patch_redis):
        """get_result deserializes correctly."""
        patch_redis.get.return_value = json.dumps({
            "total_endpoints": 1,
            "successful": 1,
            "failed": 0,
            "errors": [],
            "tests": [{"endpoint": "GET /", "code": "def test(): pass", "is_valid": True, "validation_error": None}],
            "conftest": None,
        })
        result = await GenerationService.get_result("res-1")
        assert result is not None
        assert result.total_endpoints == 1
        assert result.tests[0].endpoint == "GET /"

    @pytest.mark.asyncio
    async def test_get_result_not_found(self, patch_redis):
        """get_result returns None for missing result."""
        patch_redis.get.return_value = None
        result = await GenerationService.get_result("missing")
        assert result is None


class TestConcurrentAccess:
    """Tests for concurrent task creation."""

    @pytest.mark.asyncio
    async def test_concurrent_task_creation(self, patch_redis):
        """Multiple tasks created concurrently have unique IDs."""
        tasks = await asyncio.gather(
            *[
                GenerationService.create_task("swagger", {"paths": {}}, "pytest", "anthropic")
                for _ in range(10)
            ]
        )
        assert len(tasks) == 10
        assert len(set(tasks)) == 10


class TestEdgeCases:
    """Edge case tests."""

    @pytest.mark.asyncio
    async def test_empty_input(self, patch_redis):
        """Empty input data is handled."""
        task_id = await GenerationService.create_task("swagger", {}, "pytest", "anthropic")
        assert task_id is not None

    @pytest.mark.asyncio
    async def test_none_model(self, patch_redis):
        """None model parameter is handled."""
        config = TaskConfig("swagger", {"paths": {}}, "pytest", "anthropic", None)
        serialized = config.to_json()
        deserialized = TaskConfig.from_json(serialized)
        assert deserialized.model is None

    @pytest.mark.asyncio
    async def test_get_nonexistent_result(self, patch_redis):
        """Getting nonexistent result returns None."""
        patch_redis.get.return_value = None
        assert await GenerationService.get_result("nonexistent") is None

    def test_task_config_round_trip(self):
        """TaskConfig serialization round-trip."""
        config = TaskConfig("har", [{"req": "data"}], "pytest", "groq", "llama3")
        restored = TaskConfig.from_json(config.to_json())
        assert restored.input_type == "har"
        assert restored.provider == "groq"
        assert restored.model == "llama3"
