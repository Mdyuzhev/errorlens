"""Tests for Wave 4.0 WebSocket infrastructure."""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.websocket.manager import ConnectionManager, manager


def test_websocket_ping():
    """Test WebSocket ping/pong."""
    client = TestClient(app)
    with client.websocket_connect("/ws/generation/test-123") as ws:
        ws.send_text("ping")
        assert ws.receive_text() == "pong"


def test_websocket_cancel():
    """Test WebSocket cancel message."""
    client = TestClient(app)
    with client.websocket_connect("/ws/generation/test-456") as ws:
        ws.send_text("cancel")
        # Connection should close gracefully


def test_websocket_connection():
    """Test WebSocket connection and disconnection."""
    client = TestClient(app)
    with client.websocket_connect("/ws/generation/test-789") as ws:
        # Just verify connection works
        ws.send_text("ping")
        response = ws.receive_text()
        assert response == "pong"


class TestConnectionManager:
    """Tests for ConnectionManager class."""

    @pytest.fixture
    def mgr(self):
        """Create fresh manager for each test."""
        return ConnectionManager()

    @pytest.mark.asyncio
    async def test_connect_adds_to_active(self, mgr):
        """Connect adds websocket to active connections."""
        ws = AsyncMock()
        await mgr.connect("task-1", ws)
        assert "task-1" in mgr.active_connections
        ws.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_removes_from_active(self, mgr):
        """Disconnect removes websocket from active connections."""
        ws = AsyncMock()
        await mgr.connect("task-1", ws)
        await mgr.disconnect("task-1")
        assert "task-1" not in mgr.active_connections

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent(self, mgr):
        """Disconnect nonexistent task doesn't raise."""
        await mgr.disconnect("nonexistent")  # Should not raise

    def test_is_connected(self, mgr):
        """is_connected returns correct status."""
        assert not mgr.is_connected("task-1")
        mgr.active_connections["task-1"] = AsyncMock()
        assert mgr.is_connected("task-1")

    @pytest.mark.asyncio
    async def test_send_json_success(self, mgr):
        """send_json sends data to connected websocket."""
        ws = AsyncMock()
        mgr.active_connections["task-1"] = ws

        result = await mgr.send_json("task-1", {"type": "test"})

        assert result is True
        ws.send_json.assert_called_once_with({"type": "test"})

    @pytest.mark.asyncio
    async def test_send_json_no_connection(self, mgr):
        """send_json returns False when no connection."""
        result = await mgr.send_json("nonexistent", {"type": "test"})
        assert result is False

    @pytest.mark.asyncio
    async def test_send_json_connection_error(self, mgr):
        """send_json handles connection errors gracefully."""
        ws = AsyncMock()
        ws.send_json.side_effect = RuntimeError("Connection closed")
        mgr.active_connections["task-1"] = ws

        result = await mgr.send_json("task-1", {"type": "test"})

        assert result is False
        assert "task-1" not in mgr.active_connections

    @pytest.mark.asyncio
    async def test_send_started(self, mgr):
        """send_started sends correct message format."""
        ws = AsyncMock()
        mgr.active_connections["task-1"] = ws

        await mgr.send_started("task-1", 5)

        ws.send_json.assert_called_with({"type": "started", "total": 5})

    @pytest.mark.asyncio
    async def test_send_progress(self, mgr):
        """send_progress sends correct message format."""
        ws = AsyncMock()
        mgr.active_connections["task-1"] = ws

        await mgr.send_progress("task-1", 2, 5, "GET /users", "Processing...")

        ws.send_json.assert_called_with({
            "type": "progress",
            "current": 2,
            "total": 5,
            "endpoint": "GET /users",
            "log": "Processing...",
        })

    @pytest.mark.asyncio
    async def test_send_progress_no_log(self, mgr):
        """send_progress without log omits log field."""
        ws = AsyncMock()
        mgr.active_connections["task-1"] = ws

        await mgr.send_progress("task-1", 2, 5, "GET /users")

        ws.send_json.assert_called_with({
            "type": "progress",
            "current": 2,
            "total": 5,
            "endpoint": "GET /users",
        })

    @pytest.mark.asyncio
    async def test_send_completed(self, mgr):
        """send_completed sends correct message format."""
        ws = AsyncMock()
        mgr.active_connections["task-1"] = ws

        await mgr.send_completed("task-1", "result-123")

        ws.send_json.assert_called_with({"type": "completed", "result_id": "result-123"})

    @pytest.mark.asyncio
    async def test_send_error(self, mgr):
        """send_error sends correct message format."""
        ws = AsyncMock()
        mgr.active_connections["task-1"] = ws

        await mgr.send_error("task-1", "Something went wrong")

        ws.send_json.assert_called_with({"type": "error", "message": "Something went wrong"})


class TestWebSocketDisconnectMidGeneration:
    """Tests for WebSocket disconnect during generation."""

    @pytest.mark.asyncio
    async def test_disconnect_mid_generation_cleanup(self):
        """Manager handles disconnect during active generation."""
        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect("task-mid", ws)

        # Simulate disconnect mid-generation
        ws.send_json.side_effect = ConnectionError("Client disconnected")

        result = await mgr.send_progress("task-mid", 3, 10, "GET /endpoint")

        assert result is False
        assert "task-mid" not in mgr.active_connections

    @pytest.mark.asyncio
    async def test_concurrent_disconnect_handling(self):
        """Multiple disconnects don't cause issues."""
        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect("task-concurrent", ws)

        # Simulate multiple concurrent disconnects
        await asyncio.gather(
            mgr.disconnect("task-concurrent"),
            mgr.disconnect("task-concurrent"),
            mgr.disconnect("task-concurrent"),
        )

        assert "task-concurrent" not in mgr.active_connections


class TestEdgeCases:
    """Edge case tests for WebSocket manager."""

    @pytest.mark.asyncio
    async def test_empty_task_id(self):
        """Empty task ID is handled."""
        mgr = ConnectionManager()
        ws = AsyncMock()
        await mgr.connect("", ws)
        assert "" in mgr.active_connections

    @pytest.mark.asyncio
    async def test_special_characters_in_task_id(self):
        """Special characters in task ID work."""
        mgr = ConnectionManager()
        ws = AsyncMock()
        task_id = "task-with-special-chars-!@#$%"
        await mgr.connect(task_id, ws)
        assert task_id in mgr.active_connections

    @pytest.mark.asyncio
    async def test_os_error_handling(self):
        """OSError during send is handled."""
        mgr = ConnectionManager()
        ws = AsyncMock()
        ws.send_json.side_effect = OSError("Network error")
        mgr.active_connections["task-os"] = ws

        result = await mgr.send_json("task-os", {"type": "test"})

        assert result is False
        assert "task-os" not in mgr.active_connections
