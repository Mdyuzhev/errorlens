"""WebSocket endpoint for live launch progress."""
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/launches/{launch_id}")
async def launch_websocket(websocket: WebSocket, launch_id: str):
    """Stream launch events (batch progress) to frontend."""
    await websocket.accept()
    pubsub = None
    try:
        from app.services.redis_client import get_redis
        r = await get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(f"el:ws:launch:{launch_id}")

        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                data = json.loads(message["data"])
                await websocket.send_json(data)
                if data.get("type") == "launch_completed":
                    break
            except (RuntimeError, ConnectionError, OSError):
                break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"Launch WS error for {launch_id}: {e}")
    finally:
        if pubsub:
            try:
                await pubsub.unsubscribe(f"el:ws:launch:{launch_id}")
                await pubsub.aclose()
            except Exception:
                pass
