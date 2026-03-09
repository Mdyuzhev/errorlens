"""Tests for Redis client and streams helpers."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    r = AsyncMock()
    r.ping.return_value = True
    r.setex.return_value = True
    r.get.return_value = None
    r.delete.return_value = 1
    r.xadd.return_value = "1234567890-0"
    r.xreadgroup.return_value = []
    r.xack.return_value = 1
    r.xgroup_create.return_value = True
    return r


@pytest.fixture
def patch_all_redis(mock_redis):
    """Patch get_redis in all modules that import it."""
    get_redis_mock = AsyncMock(return_value=mock_redis)
    with patch("app.services.redis_client.get_redis", get_redis_mock):
        with patch("app.services.redis_streams.get_redis", get_redis_mock):
            with patch("app.services.generation_service.get_redis", get_redis_mock):
                yield mock_redis


class TestRedisClient:
    """Tests for redis_client module."""

    @pytest.mark.asyncio
    async def test_redis_ping(self):
        """ping() returns True when Redis is available."""
        from app.services.redis_client import ping

        with patch("app.services.redis_client.get_redis", new_callable=AsyncMock) as mock_get:
            mock_r = AsyncMock()
            mock_r.ping.return_value = True
            mock_get.return_value = mock_r

            result = await ping()
            assert result is True
            mock_r.ping.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_redis_ping_failure(self):
        """ping() returns False when Redis is unavailable."""
        from app.services.redis_client import ping

        with patch("app.services.redis_client.get_redis", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = ConnectionError("Connection refused")

            result = await ping()
            assert result is False

    @pytest.mark.asyncio
    async def test_task_store_retrieve(self, patch_all_redis):
        """Task saved in Redis and read back correctly."""
        from app.services.generation_service import GenerationService, TaskConfig

        mock_r = patch_all_redis
        config = TaskConfig(
            input_type="swagger",
            input_data={"paths": {"/api": {}}},
            framework="pytest",
            provider="anthropic",
            model=None,
        )

        # Store task
        stored_json = config.to_json()
        mock_r.get.return_value = stored_json

        task_id = await GenerationService.create_task(
            "swagger", {"paths": {"/api": {}}}, "pytest", "anthropic", None
        )
        assert task_id  # UUID string
        mock_r.setex.assert_awaited()

        # Retrieve task
        result = await GenerationService.get_task_config(task_id)
        assert result is not None
        assert result.input_type == "swagger"
        assert result.framework == "pytest"

    @pytest.mark.asyncio
    async def test_task_ttl(self, patch_all_redis):
        """After TTL, task is unavailable (Redis returns None)."""
        from app.services.generation_service import GenerationService

        mock_r = patch_all_redis
        mock_r.get.return_value = None

        result = await GenerationService.get_task_config("expired-task-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_result_store(self, patch_all_redis):
        """Result stored with correct Redis key pattern."""
        from app.services.generation_service import GenerationService

        mock_r = patch_all_redis

        mock_result = MagicMock()
        mock_result.total_endpoints = 3
        mock_result.successful = 2
        mock_result.failed = 1
        mock_result.errors = ["error1"]
        mock_result.tests = []
        mock_result.conftest = "import pytest"

        await GenerationService.store_result("test-result-id", mock_result)

        mock_r.setex.assert_awaited()
        call_args = mock_r.setex.call_args
        assert "el:result:test-result-id" == call_args[0][0]
        assert call_args[0][1] == 3600  # RESULT_TTL


class TestRedisStreams:
    """Tests for redis_streams module."""

    @pytest.mark.asyncio
    async def test_stream_publish_consume(self, patch_all_redis):
        """Message published and consumed from stream."""
        from app.services.redis_streams import publish, consume, STREAM_GENERATION

        mock_r = patch_all_redis

        # Publish
        msg_id = await publish(STREAM_GENERATION, {"task_id": "abc123"})
        assert msg_id == "1234567890-0"
        mock_r.xadd.assert_awaited_once_with(
            STREAM_GENERATION, {"task_id": "abc123"}
        )

        # Consume
        mock_r.xreadgroup.return_value = [
            (STREAM_GENERATION, [("1234567890-0", {"task_id": "abc123"})])
        ]
        messages = await consume(STREAM_GENERATION, "generators", "worker-1", count=1)
        assert len(messages) == 1
        assert messages[0].id == "1234567890-0"
        assert messages[0].data["task_id"] == "abc123"

    @pytest.mark.asyncio
    async def test_stream_ack(self, patch_all_redis):
        """After ack, message is acknowledged."""
        from app.services.redis_streams import ack, STREAM_GENERATION

        mock_r = patch_all_redis
        await ack(STREAM_GENERATION, "generators", "1234567890-0")
        mock_r.xack.assert_awaited_once_with(
            STREAM_GENERATION, "generators", "1234567890-0"
        )

    @pytest.mark.asyncio
    async def test_create_group_idempotent(self, patch_all_redis):
        """create_group succeeds even if group already exists."""
        from app.services.redis_streams import create_group, STREAM_GENERATION

        mock_r = patch_all_redis

        # First call succeeds
        await create_group(STREAM_GENERATION, "generators")
        mock_r.xgroup_create.assert_awaited()

        # Second call with BUSYGROUP error should not raise
        mock_r.xgroup_create.side_effect = Exception("BUSYGROUP Consumer Group name already exists")
        await create_group(STREAM_GENERATION, "generators")  # Should not raise
