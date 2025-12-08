"""WebSocket endpoint for generation progress."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket.manager import manager

router = APIRouter()


@router.websocket("/ws/generation/{task_id}")
async def generation_websocket(websocket: WebSocket, task_id: str):
    await manager.connect(task_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "cancel":
                break
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(task_id)
