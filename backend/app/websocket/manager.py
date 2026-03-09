"""WebSocket connection manager with Redis pub/sub support."""
import asyncio
import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self._pubsub_tasks: dict[str, asyncio.Task] = {}

    async def connect(self, task_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[task_id] = websocket
        await self._subscribe_task(task_id)

    async def disconnect(self, task_id: str) -> None:
        self.active_connections.pop(task_id, None)
        task = self._pubsub_tasks.pop(task_id, None)
        if task and not task.done():
            task.cancel()

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
        msg = {"type": "started", "total": total}
        await self._publish(task_id, msg)
        return await self.send_json(task_id, msg)

    async def send_progress(self, task_id: str, current: int, total: int,
                            endpoint: str, log: str | None = None) -> bool:
        data = {"type": "progress", "current": current, "total": total, "endpoint": endpoint}
        if log:
            data["log"] = log
        await self._publish(task_id, data)
        return await self.send_json(task_id, data)

    async def send_completed(self, task_id: str, result_id: str) -> bool:
        msg = {"type": "completed", "result_id": result_id}
        await self._publish(task_id, msg)
        return await self.send_json(task_id, msg)

    async def send_error(self, task_id: str, message: str) -> bool:
        msg = {"type": "error", "message": message}
        await self._publish(task_id, msg)
        return await self.send_json(task_id, msg)

    def is_connected(self, task_id: str) -> bool:
        return task_id in self.active_connections

    async def _publish(self, task_id: str, data: dict) -> None:
        """Publish message to Redis pub/sub channel."""
        try:
            from app.services.redis_client import get_redis
            r = await get_redis()
            await r.publish(f"el:ws:{task_id}", json.dumps(data))
        except Exception as e:
            logger.debug(f"Redis publish skipped for {task_id}: {e}")

    async def _subscribe_task(self, task_id: str) -> None:
        """Subscribe to Redis pub/sub for this task_id."""
        try:
            from app.services.redis_client import get_redis
            r = await get_redis()
            pubsub = r.pubsub()
            await pubsub.subscribe(f"el:ws:{task_id}")
            task = asyncio.create_task(self._pubsub_listener(task_id, pubsub))
            self._pubsub_tasks[task_id] = task
        except Exception as e:
            logger.debug(f"Redis subscribe skipped for {task_id}: {e}")

    async def _pubsub_listener(self, task_id: str, pubsub) -> None:
        """Listen to Redis pub/sub and forward messages to WebSocket."""
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                ws = self.active_connections.get(task_id)
                if not ws:
                    break
                try:
                    data = json.loads(message["data"])
                    await ws.send_json(data)
                except (RuntimeError, ConnectionError, OSError):
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Pubsub listener error for {task_id}: {e}")
        finally:
            try:
                await pubsub.unsubscribe(f"el:ws:{task_id}")
                await pubsub.aclose()
            except Exception:
                pass


manager = ConnectionManager()
