"""Tests for cache_service module."""

import json
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    r = AsyncMock()
    r.get.return_value = None
    r.setex.return_value = True
    r.delete.return_value = 1
    r.scan.return_value = (0, [])
    return r


@pytest.fixture
def patch_cache_redis(mock_redis):
    """Patch get_redis in cache_service."""
    with patch("app.services.cache_service.get_redis", AsyncMock(return_value=mock_redis)):
        yield mock_redis


class TestGetOrSet:
    """Tests for cache get_or_set."""

    @pytest.mark.asyncio
    async def test_cache_miss_calls_fetcher(self, patch_cache_redis):
        from app.services.cache_service import get_or_set

        mock_redis = patch_cache_redis
        mock_redis.get.return_value = None

        fetcher = AsyncMock(return_value={"id": "1", "name": "Bug"})
        result = await get_or_set("test:key", fetcher, ttl=60)

        assert result == {"id": "1", "name": "Bug"}
        fetcher.assert_awaited_once()
        mock_redis.setex.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cache_hit_skips_fetcher(self, patch_cache_redis):
        from app.services.cache_service import get_or_set

        mock_redis = patch_cache_redis
        mock_redis.get.return_value = json.dumps({"id": "1", "name": "Bug"})

        fetcher = AsyncMock(return_value={"id": "2", "name": "Task"})
        result = await get_or_set("test:key", fetcher, ttl=60)

        assert result == {"id": "1", "name": "Bug"}
        fetcher.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_redis_read_error_falls_back(self, patch_cache_redis):
        from app.services.cache_service import get_or_set

        mock_redis = patch_cache_redis
        mock_redis.get.side_effect = ConnectionError("Redis down")

        fetcher = AsyncMock(return_value=[1, 2, 3])
        result = await get_or_set("test:key", fetcher)

        assert result == [1, 2, 3]
        fetcher.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_redis_write_error_returns_result(self, patch_cache_redis):
        from app.services.cache_service import get_or_set

        mock_redis = patch_cache_redis
        mock_redis.get.return_value = None
        mock_redis.setex.side_effect = ConnectionError("Redis down")

        fetcher = AsyncMock(return_value={"ok": True})
        result = await get_or_set("test:key", fetcher)

        assert result == {"ok": True}


class TestInvalidate:
    """Tests for cache invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_deletes_key(self, patch_cache_redis):
        from app.services.cache_service import invalidate

        mock_redis = patch_cache_redis
        await invalidate("test:key")
        mock_redis.delete.assert_awaited_once_with("test:key")

    @pytest.mark.asyncio
    async def test_invalidate_prefix_scans_and_deletes(self, patch_cache_redis):
        from app.services.cache_service import invalidate_prefix

        mock_redis = patch_cache_redis
        mock_redis.scan.return_value = (0, ["task_types:p1", "task_types:p1:sub"])

        await invalidate_prefix("task_types:p1")
        mock_redis.delete.assert_awaited_once_with("task_types:p1", "task_types:p1:sub")

    @pytest.mark.asyncio
    async def test_invalidate_prefix_no_keys(self, patch_cache_redis):
        from app.services.cache_service import invalidate_prefix

        mock_redis = patch_cache_redis
        mock_redis.scan.return_value = (0, [])

        await invalidate_prefix("nonexistent:")
        mock_redis.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_invalidate_redis_error_no_exception(self, patch_cache_redis):
        from app.services.cache_service import invalidate

        mock_redis = patch_cache_redis
        mock_redis.delete.side_effect = ConnectionError("Redis down")

        await invalidate("test:key")  # Should not raise
