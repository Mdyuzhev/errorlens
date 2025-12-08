# Wave 5.0: Session-to-Tests Integration

## Scope

Connect recorded sessions (bookmarklet) to LLM test generator.

```
Bookmarklet → Session (recorded_requests) → HARInput → LLMGenerator → Tests
```

## Phases

| Phase | Task | Files |
|-------|------|-------|
| P1 | Backend endpoint | generation.py, generation_service.py |
| P2 | Vue integration | SessionDetailModal.vue, generation.js |
| P3 | E2E verification | Manual test + automated |

## P1: Backend Endpoint

### Add to `backend/app/routers/generation.py`

```python
@router.post("/from-session/{session_id}", response_model=TaskResponse)
async def generate_from_session(
    session_id: str,
    background_tasks: BackgroundTasks,
    framework: str = Form("pytest"),
    provider: str = Form("anthropic"),
    model: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    ...
```

### Interface

```python
# generation_service.py
@staticmethod
async def create_task_from_session(
    session_id: str,
    db: AsyncSession,
    framework: str = "pytest",
    provider: str = "anthropic",
    model: str | None = None
) -> str:
    """Load session, extract recorded_requests, create task."""
    ...
```

### Requirements

- Load session by ID from DB
- Extract `recorded_requests` field
- Convert to HARInput format:
  ```python
  har_data = [
      {
          "request": {
              "url": req["url"],
              "method": req["method"],
              "headers": req.get("headers", {}),
              "body": req.get("body")
          }
      }
      for req in session.recorded_requests
  ]
  ```
- Return 404 if session not found
- Return 400 if session has no recorded_requests
- Check project access (require_auth)

### Tests

```python
# tests/test_generation_from_session.py

def test_from_session_success(): ...
def test_from_session_not_found(): ...
def test_from_session_no_requests(): ...
def test_from_session_auth_required(): ...
def test_from_session_project_access(): ...
```

## P2: Vue Integration

### Update `SessionDetailModal.vue`

Add "Generate Tests" button:

```vue
<button 
  v-if="session.recorded_requests?.length > 0"
  @click="generateTests"
  class="generate-btn"
>
  🔧 Генерировать тесты
</button>
```

### Update `stores/generation.js`

```javascript
async function startFromSession(sessionId, options = {}) {
  const formData = new FormData()
  formData.append('framework', options.framework || 'pytest')
  formData.append('provider', options.provider || 'anthropic')
  
  const response = await api.post(
    `/api/v1/generation/from-session/${sessionId}`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  )
  taskId.value = response.data.task_id
  return response.data
}
```

### Flow

1. User opens session detail
2. Clicks "Generate Tests"
3. Modal shows framework/provider selection
4. Start generation → redirect to GeneratorView progress step
5. OR: inline progress in modal

### UI Options

Option A: Redirect to /generator with session_id param
Option B: Inline progress in SessionDetailModal

Recommended: Option A (simpler, reuse existing GeneratorView)

### Router Update

```javascript
// GeneratorView accepts sessionId param
{ 
  path: '/generator/:sessionId?',
  name: 'generator',
  component: GeneratorView,
  props: true
}
```

### GeneratorView Update

```javascript
const props = defineProps(['sessionId'])

onMounted(async () => {
  if (props.sessionId) {
    // Auto-start generation from session
    await startFromSession(props.sessionId)
  }
})
```

## P3: E2E Verification

### Manual Test Flow

1. Open any site in browser
2. Activate ErrorLens bookmarklet
3. Perform actions (clicks, form submits)
4. Stop recording
5. Verify session created in Dashboard
6. Open session detail
7. Click "Generate Tests"
8. Wait for completion
9. Download ZIP
10. Verify tests are valid

### Verification Script

```bash
#!/bin/bash
# test_session_to_tests.sh

# 1. Create session with recorded requests
SESSION_ID=$(curl -s -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://test.com",
    "user_agent": "test",
    "recorded_requests": [
      {"url": "https://api.test.com/users", "method": "GET", "status": 200},
      {"url": "https://api.test.com/users/1", "method": "GET", "status": 200}
    ]
  }' | jq -r '.session_id')

echo "Session: $SESSION_ID"

# 2. Generate tests from session
TASK_ID=$(curl -s -X POST "http://localhost:8000/api/v1/generation/from-session/$SESSION_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -F "framework=pytest" \
  -F "provider=ollama" | jq -r '.task_id')

echo "Task: $TASK_ID"

# 3. Wait and check result
sleep 10
curl -s "http://localhost:8000/api/v1/generation/result/$TASK_ID"
```

## Prohibited

- Skip auth check
- Return 500 on missing session (use 404)
- Hardcode provider
- Create new components when existing can be reused

## Quality Gates

- [ ] /from-session/{id} returns task_id
- [ ] Session with no requests returns 400
- [ ] Auth required
- [ ] UI button appears only when recorded_requests exist
- [ ] Generation produces valid tests
- [ ] ZIP downloadable

## Commit Format

```
[Wave 5.0] P1: Add /from-session endpoint
[Wave 5.0] P2: Add generate tests button to session modal
[Wave 5.0] P3: E2E test session-to-tests flow
```
