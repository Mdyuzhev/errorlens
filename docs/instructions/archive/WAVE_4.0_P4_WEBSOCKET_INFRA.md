# Wave 4.0 P4: WebSocket Infrastructure

## Scope

Create files in `backend/app/websocket/`:
- `__init__.py`
- `manager.py`
- `generation_ws.py`

## Interfaces

### manager.py

```python
@dataclass
class Connection:
    websocket: WebSocket
    task_id: str
    created_at: float = field(default_factory=time.time)

class ConnectionManager:
    def __init__(self, max_age: int = 3600, max_connections: int = 1000): ...
    
    async def connect(self, task_id: str, websocket: WebSocket) -> None: ...
    async def disconnect(self, task_id: str) -> None: ...
    async def send_json(self, task_id: str, data: dict) -> bool: ...
    async def send_started(self, task_id: str, total: int) -> bool: ...
    async def send_progress(self, task_id: str, current: int, total: int, endpoint: str, log: str | None = None) -> bool: ...
    async def send_completed(self, task_id: str, result_id: str) -> bool: ...
    async def send_error(self, task_id: str, message: str) -> bool: ...
    def is_connected(self, task_id: str) -> bool: ...
    def cleanup_stale(self) -> int: ...

manager = ConnectionManager()
```

### generation_ws.py

```python
router = APIRouter()

@router.websocket("/ws/generation/{task_id}")
async def generation_websocket(websocket: WebSocket, task_id: str): ...
```

## Requirements

### Connection Management
- Max connections: 1000
- Max age: 3600 seconds
- Cleanup stale connections on each connect
- Log connection/disconnection events

### Memory Management
- Call `cleanup_stale()` on every `connect()`
- Remove connections older than `max_age`
- Remove disconnected sockets

### Production Note
Current implementation uses in-memory dict with TTL cleanup.
For horizontal scaling, replace with Redis pub/sub:
```python
# Future: redis_manager.py
# await redis.publish(f"ws:{task_id}", json.dumps(event))
```
MVP: in-memory acceptable with proper cleanup.

### Event Types

| Type | Fields |
|------|--------|
| started | total |
| progress | current, total, endpoint, log? |
| log | message |
| completed | result_id |
| error | message |

### WebSocket Protocol
- Accept: "ping" -> respond "pong"
- Accept: "cancel" -> close connection
- Handle `WebSocketDisconnect` gracefully

## Prohibited

- Bare `except:`
- Unlimited connections
- Connections without TTL
- Blocking operations in WS handler

## Tests Required

```python
# tests/test_websocket.py

def test_connect_disconnect(): ...
def test_send_progress_no_connection(): ...
def test_cleanup_stale_connections(): ...
def test_max_connections_limit(): ...
def test_ping_pong(): ...
def test_cancel_closes_connection(): ...
def test_concurrent_connections(): ...
def test_disconnect_mid_send(): ...
```

## Integration

Add to `backend/app/main.py`:
```python
from app.websocket import ws_router
app.include_router(ws_router)
```

## Commit

```
[Wave 4.0] P4: Add WebSocket infrastructure with connection management
```
