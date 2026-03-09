"""Tests for EventPublisher."""
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    r = AsyncMock()
    r.xadd.return_value = "1234567890-0"
    return r


@pytest.fixture
def patch_redis(mock_redis):
    """Patch get_redis for redis_streams."""
    get_redis_mock = AsyncMock(return_value=mock_redis)
    with patch("app.services.redis_streams.get_redis", get_redis_mock):
        yield mock_redis


class TestEventPublisher:
    """Tests for event_publisher module."""

    @pytest.mark.asyncio
    async def test_publish_returns_event_id(self, patch_redis):
        """publish() returns a non-empty UUID string."""
        from app.services.event_publisher import publish

        result = await publish("testcase.created", {"id": "tc-1", "title": "Test"})
        assert result is not None
        assert len(result) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_publish_envelope_structure(self, patch_redis):
        """Published message contains all required envelope fields."""
        from app.services.event_publisher import publish

        await publish(
            "task.created",
            {"id": "t-1", "title": "Task"},
            actor_id="user-1",
            project_id="proj-1",
        )

        patch_redis.xadd.assert_awaited_once()
        call_args = patch_redis.xadd.call_args
        stream = call_args[0][0]
        data = call_args[0][1]

        assert stream == "el:events"
        assert "event_id" in data
        assert data["type"] == "task.created"
        assert "timestamp" in data
        assert data["actor_id"] == "user-1"
        assert data["project_id"] == "proj-1"
        assert "payload" in data

    @pytest.mark.asyncio
    async def test_publish_redis_unavailable(self):
        """When Redis is unavailable, publish does not raise."""
        from app.services.event_publisher import publish

        with patch(
            "app.services.redis_streams.get_redis",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Redis down"),
        ):
            result = await publish("testcase.created", {"id": "tc-1"})
            assert result is None

    @pytest.mark.asyncio
    async def test_event_id_unique(self, patch_redis):
        """Two publish calls produce different event_ids."""
        from app.services.event_publisher import publish

        id1 = await publish("task.created", {"id": "t-1"})
        id2 = await publish("task.created", {"id": "t-2"})
        assert id1 != id2

    @pytest.mark.asyncio
    async def test_publish_empty_actor_and_project(self, patch_redis):
        """Nullable actor_id and project_id are serialized as empty string."""
        from app.services.event_publisher import publish

        await publish("testcase.deleted", {"id": "tc-1"})

        call_args = patch_redis.xadd.call_args
        data = call_args[0][1]
        assert data["actor_id"] == ""
        assert data["project_id"] == ""

    @pytest.mark.asyncio
    async def test_publish_concurrent_access(self, patch_redis):
        """Multiple concurrent publishes all succeed."""
        import asyncio

        from app.services.event_publisher import publish

        results = await asyncio.gather(
            *[publish("task.created", {"id": f"t-{i}"}) for i in range(10)]
        )
        assert all(r is not None for r in results)
        assert len(set(results)) == 10  # All unique
