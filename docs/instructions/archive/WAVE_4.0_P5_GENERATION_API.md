# Wave 4.0 P5: Generation API

## Scope

Create files:
- `backend/app/services/generation_service.py`
- `backend/app/routers/generation.py`

## Interfaces

### services/generation_service.py

```python
@dataclass
class TaskConfig:
    input_type: str
    input_data: Any
    framework: str
    provider: str
    model: str | None
    created_at: float = field(default_factory=time.time)

@dataclass
class StoredResult:
    result: GenerationResult
    created_at: float = field(default_factory=time.time)

class GenerationService:
    MAX_TASKS: int = 10000
    MAX_RESULTS: int = 10000
    TTL_SECONDS: int = 3600
    
    @staticmethod
    async def create_task(...) -> str: ...
    @staticmethod
    async def run_task(task_id: str) -> GenerationResult | None: ...
    @staticmethod
    def get_result(result_id: str) -> GenerationResult | None: ...
    @staticmethod
    def cleanup_expired() -> tuple[int, int]: ...
```

### routers/generation.py

```python
router = APIRouter(prefix="/api/v1/generation", tags=["generation"])

class TaskResponse(BaseModel):
    task_id: str
    websocket_url: str

class ResultResponse(BaseModel):
    total_endpoints: int
    successful: int
    failed: int
    errors: list[str]
    tests: list[dict]
    conftest: str | None

@router.post("/from-swagger", response_model=TaskResponse)
async def generate_from_swagger(...): ...

@router.post("/from-session/{session_id}", response_model=TaskResponse)
async def generate_from_session(...): ...

@router.get("/result/{result_id}", response_model=ResultResponse)
async def get_result(...): ...

@router.get("/download/{result_id}")
async def download_result(...): ...

@router.get("/health")
async def health(): ...
```

## Requirements

### Memory Management
- Max 10000 tasks in memory
- Max 10000 results in memory
- TTL: 3600 seconds
- Cleanup on each `create_task()` call
- Log cleanup counts

### Task Lifecycle

```
create_task() → task_id
    ↓
client connects WS
    ↓
run_task() (background)
    ↓
result stored → result_id
    ↓
cleanup after TTL
```

### File Upload
- Accept JSON and YAML
- Validate: must have `paths` field
- Max size: 10MB

### Download
- ZIP format
- Include conftest.py if pytest
- Filename: `tests_{result_id[:8]}.zip`

## Prohibited

- Unlimited storage
- No TTL cleanup
- Bare `except:`
- Sync file operations

## Tests Required

```python
# tests/test_generation_api.py

def test_health(): ...
def test_from_swagger_valid(): ...
def test_from_swagger_invalid_json(): ...
def test_from_swagger_missing_paths(): ...
def test_from_swagger_yaml(): ...
def test_result_found(): ...
def test_result_not_found(): ...
def test_download_zip(): ...
def test_task_cleanup_expired(): ...
def test_result_cleanup_expired(): ...
def test_max_tasks_limit(): ...
def test_concurrent_task_creation(): ...
def test_task_memory_leak(): ...       # Create 100 tasks, wait TTL, verify cleanup
def test_concurrent_generations(): ... # 10 parallel generations, no race conditions
def test_result_memory_leak(): ...     # Create 100 results, wait TTL, verify cleanup
```

## E2E Test (manual)

```bash
# 1. Upload swagger
curl -X POST -F "file=@petstore.yaml" localhost:8000/api/v1/generation/from-swagger

# 2. Connect WebSocket (use wscat)
wscat -c ws://localhost:8000/ws/generation/{task_id}

# 3. Wait for completed event, get result_id

# 4. Download
curl -O localhost:8000/api/v1/generation/download/{result_id}

# 5. Verify ZIP contains conftest.py + test files
unzip -l tests_*.zip
```

## Integration

Add to `backend/app/main.py`:
```python
from app.routers import generation
app.include_router(generation.router)
```

## Commit

```
[Wave 4.0] P5: Add generation REST API with memory management
```
