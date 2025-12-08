"""Tests for Wave 4.0 WebSocket infrastructure."""

from fastapi.testclient import TestClient
from app.main import app


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
