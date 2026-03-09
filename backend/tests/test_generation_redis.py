"""Tests for GenerationService Redis-backed storage."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    r = AsyncMock()
    r.ping.return_value = True
    r.setex.return_value = True
    r.get.return_value = None
    r.delete.return_value = 1
    return r


@pytest.fixture
def patch_redis(mock_redis):
    """Patch get_redis globally."""
    with patch("app.services.redis_client.get_redis", new_callable=AsyncMock, return_value=mock_redis):
        with patch("app.services.generation_service.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            yield mock_redis


class TestGenerationRedis:
    """Tests verifying GenerationService uses Redis, not in-memory dicts."""

    @pytest.mark.asyncio
    async def test_create_task_in_redis(self, patch_redis):
        """create_task() writes to Redis, not in-memory dict."""
        from app.services.generation_service import GenerationService

        mock_r = patch_redis

        task_id = await GenerationService.create_task(
            input_type="swagger",
            input_data={"paths": {}},
            framework="pytest",
            provider="anthropic",
            model=None,
        )

        assert task_id is not None
        # Verify Redis setex was called with correct key pattern
        mock_r.setex.assert_awaited_once()
        call_args = mock_r.setex.call_args[0]
        assert call_args[0] == f"el:task:{task_id}"
        assert call_args[1] == 3600  # TASK_TTL

        # Verify the serialized data
        stored_data = json.loads(call_args[2])
        assert stored_data["input_type"] == "swagger"
        assert stored_data["framework"] == "pytest"
        assert stored_data["provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_get_result_from_redis(self, patch_redis):
        """get_result() reads from Redis."""
        from app.services.generation_service import GenerationService

        mock_r = patch_redis

        # Simulate stored result in Redis
        result_data = json.dumps({
            "total_endpoints": 5,
            "successful": 4,
            "failed": 1,
            "errors": ["timeout on /api/slow"],
            "tests": [
                {
                    "endpoint": "GET /api/users",
                    "code": "def test_get_users(): pass",
                    "is_valid": True,
                    "validation_error": None,
                }
            ],
            "conftest": "import pytest",
        })
        mock_r.get.return_value = result_data

        result = await GenerationService.get_result("test-result-123")

        assert result is not None
        assert result.total_endpoints == 5
        assert result.successful == 4
        assert result.failed == 1
        assert len(result.tests) == 1
        assert result.tests[0].endpoint == "GET /api/users"
        assert result.conftest == "import pytest"

    @pytest.mark.asyncio
    async def test_get_result_not_found(self, patch_redis):
        """get_result() returns None when result doesn't exist."""
        from app.services.generation_service import GenerationService

        mock_r = patch_redis
        mock_r.get.return_value = None

        result = await GenerationService.get_result("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_no_in_memory_state(self):
        """_tasks and _results dicts no longer exist in module."""
        import app.services.generation_service as mod

        assert not hasattr(mod, "_tasks"), "_tasks dict should not exist"
        assert not hasattr(mod, "_results"), "_results dict should not exist"

    @pytest.mark.asyncio
    async def test_task_config_serialization(self):
        """TaskConfig serializes and deserializes correctly."""
        from app.services.generation_service import TaskConfig

        config = TaskConfig(
            input_type="har",
            input_data=[{"request": {"url": "http://api.test", "method": "POST"}}],
            framework="pytest",
            provider="groq",
            model="llama3-8b",
        )

        serialized = config.to_json()
        deserialized = TaskConfig.from_json(serialized)

        assert deserialized.input_type == "har"
        assert deserialized.framework == "pytest"
        assert deserialized.provider == "groq"
        assert deserialized.model == "llama3-8b"
        assert len(deserialized.input_data) == 1

    @pytest.mark.asyncio
    async def test_store_result_with_tests(self, patch_redis):
        """store_result serializes tests correctly."""
        from app.services.generation_service import GenerationService

        mock_r = patch_redis

        mock_test = MagicMock()
        mock_test.endpoint = "POST /api/login"
        mock_test.code = "def test_login(): assert True"
        mock_test.is_valid = True
        mock_test.validation_error = None

        mock_result = MagicMock()
        mock_result.total_endpoints = 1
        mock_result.successful = 1
        mock_result.failed = 0
        mock_result.errors = []
        mock_result.tests = [mock_test]
        mock_result.conftest = None

        await GenerationService.store_result("result-456", mock_result)

        call_args = mock_r.setex.call_args[0]
        stored = json.loads(call_args[2])
        assert stored["total_endpoints"] == 1
        assert stored["tests"][0]["endpoint"] == "POST /api/login"
        assert stored["tests"][0]["is_valid"] is True
