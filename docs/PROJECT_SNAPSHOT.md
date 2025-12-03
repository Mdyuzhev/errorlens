# ErrorLens - Project Snapshot

> Architecture review document for Epic 8 (Web Application) planning.
> Updated: 2025-12-03 (Epic 9 complete)

---

## 1. Directory Structure

```
errorlens/
├── .claude/                    # Claude Code settings
│   └── settings.local.json
├── .github/workflows/          # CI/CD pipelines
│   ├── ci.yml                  # Linting + tests
│   ├── deploy-backend.yml      # Railway/Vercel deploy
│   └── deploy-landing.yml      # GitHub Pages deploy
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── analyzer.py         # LLM analysis orchestration
│   │   ├── config.py           # Pydantic Settings
│   │   ├── main.py             # FastAPI entrypoint
│   │   ├── models.py           # All Pydantic models
│   │   ├── postman_generator.py # Postman Collection export
│   │   ├── session_analyzer.py  # Variable detection, grouping
│   │   └── providers/
│   │       ├── __init__.py
│   │       ├── base.py         # LLMProvider ABC
│   │       ├── gemini.py       # Google Gemini
│   │       └── groq.py         # Groq (Llama)
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_analyzer.py
│   │   ├── test_api.py
│   │   ├── test_models.py
│   │   └── test_providers.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── bookmarklet/
│   ├── README.md
│   └── recorder.js             # Main bookmarklet (~1300 lines)
├── docs/
│   ├── EXAMPLES.md
│   └── PROJECT_SNAPSHOT.md     # This file
├── landing/
│   └── index.html              # GitHub Pages landing
├── nginx/
│   ├── Dockerfile              # nginx image with baked-in static files
│   └── nginx.conf              # Reverse proxy config
├── docker-compose.yml          # Full stack: backend + nginx
├── pyproject.toml
├── README.md
├── ROADMAP.md
└── CONTRIBUTING.md
```

---

## 2. API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check, returns `{status: "ok", version}` |
| `POST` | `/analyze` | AI-powered error analysis |
| `POST` | `/export/postman` | Generate Postman Collection from recorded requests |
| `POST` | `/analyze/session` | Analyze session for test generation (variables, groups, assertions) |

### POST /analyze

**Request:** `AnalyzeRequest`
```json
{
  "url": "https://example.com",
  "user_agent": "Mozilla/5.0...",
  "console_logs": [...],
  "network_errors": [...],
  "js_exceptions": [...],
  "screenshot": "base64...",
  "recording_duration_ms": 5000,
  "recorded_requests": [...],
  "record_mode": "errors"
}
```

**Response:** `AnalyzeResponse`
```json
{
  "summary": "Main issue description",
  "probable_cause": "Root cause",
  "suggested_fix": "Recommended fix",
  "severity": "low|medium|high|critical",
  "raw_events_count": 10,
  "details": "Additional analysis"
}
```

### POST /export/postman

**Request:** `ExportPostmanRequest`
```json
{
  "recorded_requests": [...],
  "collection_name": "My API Tests",
  "base_url_variable": true,
  "generate_tests": true
}
```

**Response:** `ExportPostmanResponse`
```json
{
  "collection": { /* Postman Collection v2.1 */ },
  "requests_count": 10,
  "variables_count": 3
}
```

### POST /analyze/session

**Request:** `SessionAnalysisRequest`
```json
{
  "recorded_requests": [...]
}
```

**Response:** `SessionAnalysisResponse`
```json
{
  "variables": {
    "authToken": {
      "name": "authToken",
      "source_request_id": 1,
      "source_path": "response.body.token",
      "value": "eyJ...",
      "used_in": [2, 3, 4]
    }
  },
  "groups": {
    "auth": [1],
    "user": [2, 3],
    "create": [4]
  },
  "assertions": {
    "1": [
      {"type": "status", "expected": "200", "description": "Status code is 200"}
    ]
  },
  "summary": {
    "total_requests": 4,
    "variables_found": 1,
    "scenarios_detected": ["auth", "user", "create"],
    "methods": ["GET", "POST"]
  }
}
```

---

## 3. Pydantic Models (Full Code)

```python
"""Pydantic models for API request/response schemas."""

from pydantic import BaseModel, Field


class ConsoleLogEntry(BaseModel):
    """Single console log entry captured by bookmarklet."""
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    level: str = Field(..., description="Log level: log, warn, error, info, debug")
    message: str = Field(..., description="Log message content")
    stack: str | None = Field(None, description="Stack trace if available")


class NetworkError(BaseModel):
    """Network request failure captured by bookmarklet."""
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    method: str = Field(..., description="HTTP method: GET, POST, etc.")
    url: str = Field(..., description="Request URL")
    status: int | None = Field(None, description="HTTP status code")
    status_text: str | None = Field(None, description="HTTP status text")


class JSException(BaseModel):
    """JavaScript exception captured by window.onerror."""
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    message: str = Field(..., description="Error message")
    source: str | None = Field(None, description="Script URL where error occurred")
    lineno: int | None = Field(None, description="Line number")
    colno: int | None = Field(None, description="Column number")
    stack: str | None = Field(None, description="Stack trace")


class RecordedRequest(BaseModel):
    """Full HTTP request captured for test generation."""
    timestamp: str
    method: str
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None
    content_type: str | None = None


class RecordedResponse(BaseModel):
    """Full HTTP response captured for test generation."""
    status: int
    status_text: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    body: str | None = None
    duration_ms: int


class RecordedHttpExchange(BaseModel):
    """Complete HTTP request/response pair for test generation."""
    id: int
    timestamp: str
    request: RecordedRequest
    response: RecordedResponse


class AnalyzeRequest(BaseModel):
    """Request body for /analyze endpoint."""
    url: str
    user_agent: str
    console_logs: list[ConsoleLogEntry] = Field(default_factory=list)
    network_errors: list[NetworkError] = Field(default_factory=list)
    js_exceptions: list[JSException] = Field(default_factory=list)
    screenshot: str | None = None
    recording_duration_ms: int
    recorded_requests: list[RecordedHttpExchange] = Field(default_factory=list)
    record_mode: str = "errors"


class AnalyzeResponse(BaseModel):
    """Response body from /analyze endpoint."""
    summary: str
    probable_cause: str
    suggested_fix: str
    severity: str
    raw_events_count: int
    details: str


# Postman Collection v2.1 models
class PostmanHeader(BaseModel):
    key: str
    value: str
    type: str = "text"


class PostmanBody(BaseModel):
    mode: str = "raw"
    raw: str | None = None
    options: dict | None = None


class PostmanUrl(BaseModel):
    raw: str
    protocol: str | None = None
    host: list[str] | None = None
    path: list[str] | None = None
    query: list[dict] | None = None


class PostmanRequest(BaseModel):
    method: str
    header: list[PostmanHeader] = Field(default_factory=list)
    body: PostmanBody | None = None
    url: PostmanUrl


class PostmanEvent(BaseModel):
    listen: str = "test"
    script: dict


class PostmanItem(BaseModel):
    name: str
    event: list[PostmanEvent] = Field(default_factory=list)
    request: PostmanRequest
    response: list = Field(default_factory=list)


class PostmanVariable(BaseModel):
    key: str
    value: str
    type: str = "string"


class PostmanInfo(BaseModel):
    name: str
    description: str = ""
    schema_url: str = Field(
        default="https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        alias="schema"
    )


class PostmanCollection(BaseModel):
    info: PostmanInfo
    item: list[PostmanItem] = Field(default_factory=list)
    variable: list[PostmanVariable] = Field(default_factory=list)


class ExportPostmanRequest(BaseModel):
    recorded_requests: list[RecordedHttpExchange]
    collection_name: str = "ErrorLens Session"
    base_url_variable: bool = True
    generate_tests: bool = True


class ExportPostmanResponse(BaseModel):
    collection: PostmanCollection
    requests_count: int
    variables_count: int


# Session analysis models
class DetectedVariable(BaseModel):
    name: str
    source_request_id: int
    source_path: str
    value: str
    used_in: list[int] = Field(default_factory=list)


class RequestAssertion(BaseModel):
    type: str
    path: str | None = None
    expected: str
    description: str


class SessionAnalysisRequest(BaseModel):
    recorded_requests: list[RecordedHttpExchange]


class SessionAnalysisResponse(BaseModel):
    variables: dict[str, DetectedVariable] = Field(default_factory=dict)
    groups: dict[str, list[int]] = Field(default_factory=dict)
    assertions: dict[int, list[RequestAssertion]] = Field(default_factory=dict)
    summary: dict = Field(default_factory=dict)
```

---

## 4. Analyzer Logic Summary

**File:** `backend/app/analyzer.py`

### Flow:
1. `analyze_errors(request)` - Main entry point
2. `_get_provider()` - Select LLM provider (Gemini primary, Groq fallback)
3. `_format_context(request)` - Build prompt with system instructions + error data
4. `provider.analyze(context)` - Send to LLM
5. `_parse_llm_response(raw)` - Extract JSON from LLM response
6. Return `AnalyzeResponse`

### System Prompt (Russian):
- Role: QA engineer analyzing browser errors
- Input: console logs, network errors, JS exceptions
- Output: JSON with summary, probable_cause, suggested_fix, severity, details
- Examples provided for TypeError and 500 errors

### Limits:
- Max 50 console logs
- Max 20 JS exceptions
- Max 30 network errors
- Stack traces truncated to 500 chars

---

## 5. Config Structure

**File:** `backend/app/config.py`

```python
class Settings(BaseSettings):
    version: str = "0.1.0"
    llm_provider: str = "gemini"  # "gemini" or "groq"
    gemini_api_key: str = ""
    groq_api_key: str = ""

    class Config:
        env_file = ".env"
```

**Environment Variables:**
- `LLM_PROVIDER` - Primary provider selection
- `GEMINI_API_KEY` - Google Gemini API key
- `GROQ_API_KEY` - Groq API key (Llama models)

---

## 6. LLM Providers

| Provider | Model | API Endpoint |
|----------|-------|--------------|
| **Gemini** | gemini-1.5-flash | `generativelanguage.googleapis.com/v1beta` |
| **Groq** | llama-3.3-70b-versatile | `api.groq.com/openai/v1` |

### Provider Interface:
```python
class LLMProvider(ABC):
    @abstractmethod
    async def analyze(self, context: str) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...
```

### Common Settings:
- Temperature: 0.3
- Max tokens: 2048
- Timeout: 60 seconds

---

## 7. Bookmarklet Functions

**File:** `bookmarklet/recorder.js` (~1300 lines, IIFE pattern)

### What It Captures:

| Type | Method |
|------|--------|
| Console logs | Override `console.log/warn/error/info/debug` |
| JS errors | `window.onerror` handler |
| Promise rejections | `window.onunhandledrejection` handler |
| Network errors | Intercept `fetch()` and `XMLHttpRequest` |
| All HTTP requests | Record mode "all" for test generation |
| Screenshots | `html2canvas` library (loaded dynamically) |

### Recording Modes:
- **"errors"** - Only 4xx/5xx network errors (default)
- **"all"** - All HTTP exchanges for Postman export

### UI Elements:
- Floating widget (red = errors mode, blue = all mode)
- Pulse animation during recording
- Event counter
- Mode selection menu
- Results modal with copy/export buttons

### Junk URL Filtering:
```javascript
const JUNK_URL_PATTERNS = [
    /google-analytics\.com/i,
    /googletagmanager\.com/i,
    /facebook\.com\/tr/i,
    /doubleclick\.net/i,
    /\.(png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot|css)(\?|$)/i,
    // ... more patterns
];
```

---

## 8. Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                           BROWSER                                    │
│  ┌──────────────┐                                                   │
│  │  Bookmarklet │                                                   │
│  │  (recorder.js)│                                                  │
│  │              │                                                   │
│  │ - Intercepts │     Click "Stop"                                  │
│  │   console    │ ─────────────────┐                                │
│  │ - Captures   │                  │                                │
│  │   errors     │                  ▼                                │
│  │ - Records    │     ┌────────────────────┐                        │
│  │   requests   │     │  Capture Screenshot │                       │
│  └──────────────┘     │  (html2canvas)      │                       │
│                       └─────────┬──────────┘                        │
│                                 │                                   │
│                                 ▼                                   │
│                       ┌────────────────────┐                        │
│                       │  Build JSON Payload │                       │
│                       │  - console_logs     │                       │
│                       │  - network_errors   │                       │
│                       │  - js_exceptions    │                       │
│                       │  - recorded_requests│                       │
│                       │  - screenshot       │                       │
│                       └─────────┬──────────┘                        │
└─────────────────────────────────┼───────────────────────────────────┘
                                  │
                    POST /analyze │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          BACKEND (FastAPI)                          │
│                                                                     │
│  ┌──────────────┐     ┌───────────────┐     ┌──────────────────┐   │
│  │   main.py    │────▶│  analyzer.py  │────▶│  LLM Provider    │   │
│  │ /analyze     │     │ _format_ctx() │     │ (Gemini/Groq)    │   │
│  │ endpoint     │     │ _get_provider │     │                  │   │
│  └──────────────┘     └───────────────┘     └────────┬─────────┘   │
│                                                       │             │
│                                                       ▼             │
│                                              ┌────────────────┐     │
│                                              │  External LLM  │     │
│                                              │  API Call      │     │
│                                              └────────┬───────┘     │
│                                                       │             │
│                                                       ▼             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    _parse_llm_response()                      │  │
│  │  - Extract JSON from response                                 │  │
│  │  - Handle markdown code blocks                                │  │
│  │  - Fallback if parsing fails                                  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                  │                                  │
│                                  ▼                                  │
│                         AnalyzeResponse                             │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           BROWSER                                    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      Results Modal                           │   │
│  │  - Summary, Cause, Fix, Severity                            │   │
│  │  - Copy to clipboard                                        │   │
│  │  - Export to Markdown                                        │   │
│  │  - Export to Postman (if record_mode="all")                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 9. What's Missing for Web App (Epic 8)

### Database Layer
- [ ] SQLite for dev, PostgreSQL for prod
- [ ] Models: `Session`, `AnalysisResult`, `User` (optional)
- [ ] Alembic migrations
- [ ] SQLAlchemy or Tortoise ORM

### Session Management
- [ ] `POST /sessions` - Create session from bookmarklet
- [ ] `GET /sessions` - List all sessions (paginated)
- [ ] `GET /sessions/{id}` - Session details
- [ ] `DELETE /sessions/{id}` - Delete session
- [ ] `GET /sessions/{id}/export` - Export formats

### Authentication (Optional)
- [ ] Anonymous sessions with UUID
- [ ] Optional user registration
- [ ] Session ownership

### Frontend Dashboard
- [ ] Vue.js or React SPA
- [ ] Session list with filters
- [ ] Session detail view
- [ ] Bookmarklet installation page
- [ ] Settings page

### Bookmarklet v2
- [ ] Silent mode (no popup)
- [ ] Send to `/sessions` instead of `/analyze`
- [ ] Success notification with dashboard link
- [ ] Offline queue

### Infrastructure
- [x] Docker Compose with nginx for landing (port 3000)
- [x] nginx Dockerfile with baked-in static files
- [x] Backend Dockerfile with health checks
- [ ] Volume mounts for database (Epic 8)
- [ ] Production Dockerfile (multi-stage)

### Current Limitations
1. **Stateless** - No data persistence between requests
2. **No session history** - Analysis results are shown once and lost
3. **Single-user** - No concept of ownership
4. **No replay** - Can't re-run analysis on saved data
5. **No batch export** - One Postman collection at a time

---

## 10. Technology Stack Summary

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, Pydantic |
| LLM | Gemini 1.5 Flash, Groq Llama 3.3 |
| Frontend | Vanilla JS (bookmarklet) |
| Landing | Static HTML |
| CI/CD | GitHub Actions |
| Deploy | Railway (backend), GitHub Pages (landing) |
| Container | Docker, docker-compose |

---

*End of Project Snapshot*
