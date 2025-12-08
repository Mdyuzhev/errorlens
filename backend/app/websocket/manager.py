"""WebSocket connection manager."""
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, task_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[task_id] = websocket

    async def disconnect(self, task_id: str) -> None:
        self.active_connections.pop(task_id, None)

    async def send_json(self, task_id: str, data: dict) -> bool:
        ws = self.active_connections.get(task_id)
        if ws:
            try:
                await ws.send_json(data)
                return True
            except (RuntimeError, ConnectionError, OSError) as e:
                logger.warning(f"WebSocket send failed for {task_id}: {e}")
                await self.disconnect(task_id)
        return False

    async def send_started(self, task_id: str, total: int) -> bool:
        return await self.send_json(task_id, {"type": "started", "total": total})

    async def send_progress(self, task_id: str, current: int, total: int,
                            endpoint: str, log: str | None = None) -> bool:
        data = {"type": "progress", "current": current, "total": total, "endpoint": endpoint}
        if log:
            data["log"] = log
        return await self.send_json(task_id, data)

    async def send_completed(self, task_id: str, result_id: str) -> bool:
        return await self.send_json(task_id, {"type": "completed", "result_id": result_id})

    async def send_error(self, task_id: str, message: str) -> bool:
        return await self.send_json(task_id, {"type": "error", "message": message})

    def is_connected(self, task_id: str) -> bool:
        return task_id in self.active_connections


manager = ConnectionManager()
