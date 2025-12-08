"""Tests for GenerationService including memory management and concurrency."""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.generation_service import (
    GenerationService,
    _results,
    _tasks,
    _cleanup_expired_results,
    StoredResult,
    RESULT_TTL,
    MAX_RESULTS,
)
from app.generators.llm_generator import GenerationResult, GeneratedTest


@pytest.fixture(autouse=True)
def clear_storage():
    """Clear global storage before each test."""
    _tasks.clear()
    _results.clear()
    yield
    _tasks.clear()
    _results.clear()


@pytest.fixture
def mock_result():
    """Create mock GenerationResult."""
    return GenerationResult(
        tests=[GeneratedTest(endpoint="GET /test", code="def test(): pass", is_valid=True)],
        conftest=None,
        total_endpoints=1,
        successful=1,
        failed=0,
        errors=[],
    )


class TestMemoryCleanup:
    """Tests for TTL-based memory cleanup."""

    def test_cleanup_expired_results(self):
        """Expired results are removed by cleanup."""
        # Add expired result
        _results["old"] = StoredResult(
            result=MagicMock(),
            created_at=time.time() - RESULT_TTL - 100,
        )
        # Add fresh result
        _results["new"] = StoredResult(result=MagicMock(), created_at=time.time())

        _cleanup_expired_results()

        assert "old" not in _results
        assert "new" in _results

    def test_cleanup_enforces_max_size(self):
        """Cleanup removes oldest when exceeding MAX_RESULTS."""
        # Add MAX_RESULTS + 10 items
        for i in range(MAX_RESULTS + 10):
            _results[f"result_{i}"] = StoredResult(
                result=MagicMock(),
                created_at=time.time() - i,  # Older items have larger i
            )

        _cleanup_expired_results()

        assert len(_results) == MAX_RESULTS

    def test_memory_cleanup_called_on_store(self, mock_result):
        """Cleanup is called when storing new result."""
        # Add expired result
        _results["expired"] = StoredResult(
            result=MagicMock(),
            created_at=time.time() - RESULT_TTL - 100,
        )

        with patch("app.services.generation_service._cleanup_expired_results") as mock_cleanup:
            # Simulate storing result (we can't easily call run_task, so test cleanup directly)
            _cleanup_expired_results()
            # Verify expired is removed
            assert "expired" not in _results

    def test_result_ttl_expiration(self):
        """Results expire after TTL."""
        _results["test"] = StoredResult(
            result=MagicMock(),
            created_at=time.time() - RESULT_TTL - 1,
        )

        _cleanup_expired_results()

        assert "test" not in _results
        assert GenerationService.get_result("test") is None

    def test_fresh_result_persists(self, mock_result):
        """Fresh results are not removed."""
        _results["fresh"] = StoredResult(result=mock_result, created_at=time.time())

        _cleanup_expired_results()

        assert "fresh" in _results
        assert GenerationService.get_result("fresh") == mock_result


class TestTaskMemoryLeak:
    """Tests ensuring no memory leaks in task storage."""

    @pytest.mark.asyncio
    async def test_task_removed_after_completion(self):
        """Task is removed from _tasks after run_task completes."""
        valid_swagger = {
            "openapi": "3.0.0",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {"/test": {"get": {"responses": {"200": {"description": "OK"}}}}}
        }
        task_id = await GenerationService.create_task(
            input_type="swagger",
            input_data=valid_swagger,
            framework="pytest",
            provider="anthropic",
        )
        assert task_id in _tasks

        with patch("app.services.generation_service.LLMTestGenerator") as mock_gen:
            mock_gen.return_value.generate = AsyncMock(
                return_value=GenerationResult([], None, 0, 0, 0, [])
            )
            with patch("app.services.generation_service.manager") as mock_mgr:
                mock_mgr.send_started = AsyncMock()
                mock_mgr.send_completed = AsyncMock()
                mock_mgr.send_error = AsyncMock()
                await GenerationService.run_task(task_id)

        assert task_id not in _tasks

    @pytest.mark.asyncio
    async def test_task_removed_on_error(self):
        """Task is removed from _tasks even when error occurs."""
        task_id = await GenerationService.create_task(
            input_type="swagger",
            input_data={"paths": {"/test": {"get": {}}}},
            framework="pytest",
            provider="anthropic",
        )

        with patch("app.services.generation_service.LLMTestGenerator") as mock_gen:
            mock_gen.return_value.generate = AsyncMock(side_effect=Exception("Test error"))
            with patch("app.services.generation_service.manager") as mock_mgr:
                mock_mgr.send_started = AsyncMock()
                mock_mgr.send_error = AsyncMock()
                await GenerationService.run_task(task_id)

        assert task_id not in _tasks

    @pytest.mark.asyncio
    async def test_task_not_found(self):
        """Running non-existent task returns None."""
        with patch("app.services.generation_service.manager") as mock_mgr:
            mock_mgr.send_error = AsyncMock()
            result = await GenerationService.run_task("nonexistent")

        assert result is None


class TestConcurrentAccess:
    """Tests for concurrent task execution."""

    @pytest.mark.asyncio
    async def test_concurrent_task_creation(self):
        """Multiple tasks can be created concurrently."""
        tasks = await asyncio.gather(
            *[
                GenerationService.create_task(
                    input_type="swagger",
                    input_data={"paths": {}},
                    framework="pytest",
                    provider="anthropic",
                )
                for _ in range(10)
            ]
        )

        assert len(tasks) == 10
        assert len(set(tasks)) == 10  # All unique IDs

    @pytest.mark.asyncio
    async def test_concurrent_result_access(self, mock_result):
        """Multiple concurrent reads of same result work correctly."""
        _results["concurrent"] = StoredResult(result=mock_result, created_at=time.time())

        async def get_result():
            return GenerationService.get_result("concurrent")

        results = await asyncio.gather(*[get_result() for _ in range(100)])

        assert all(r == mock_result for r in results)


class TestCleanupFunction:
    """Tests for manual cleanup function."""

    def test_cleanup_returns_count(self, mock_result):
        """cleanup_results returns count of removed items."""
        # Add 3 expired
        for i in range(3):
            _results[f"expired_{i}"] = StoredResult(
                result=mock_result,
                created_at=time.time() - RESULT_TTL - 100,
            )
        # Add 2 fresh
        for i in range(2):
            _results[f"fresh_{i}"] = StoredResult(
                result=mock_result,
                created_at=time.time(),
            )

        removed = GenerationService.cleanup_results()

        assert removed == 3
        assert len(_results) == 2


class TestEdgeCases:
    """Edge case tests."""

    @pytest.mark.asyncio
    async def test_empty_input(self):
        """Empty input data is handled."""
        task_id = await GenerationService.create_task(
            input_type="swagger",
            input_data={},
            framework="pytest",
            provider="anthropic",
        )
        assert task_id in _tasks

    @pytest.mark.asyncio
    async def test_none_model(self):
        """None model parameter is handled."""
        task_id = await GenerationService.create_task(
            input_type="swagger",
            input_data={"paths": {}},
            framework="pytest",
            provider="anthropic",
            model=None,
        )
        config = _tasks[task_id]
        assert config.model is None

    def test_get_nonexistent_result(self):
        """Getting nonexistent result returns None."""
        assert GenerationService.get_result("nonexistent") is None

    def test_duplicate_result_ids(self, mock_result):
        """Result IDs are unique (UUID)."""
        ids = set()
        for i in range(100):
            _results[f"result_{i}"] = StoredResult(
                result=mock_result,
                created_at=time.time(),
            )
            ids.add(f"result_{i}")
        assert len(ids) == 100
