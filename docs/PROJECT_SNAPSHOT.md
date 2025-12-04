# ErrorLens - Project Snapshot

> Architecture review document. Last updated: 2025-12-04

---

## 1. Directory Structure

```
errorlens/
├── .github/workflows/
│   ├── ci.yml
│   ├── deploy-backend.yml
│   └── deploy-landing.yml
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── analyzer.py              # LLM analysis orchestration
│   │   ├── config.py                # Pydantic Settings
│   │   ├── database.py              # SQLAlchemy async session
│   │   ├── main.py                  # FastAPI entrypoint
│   │   ├── models_pydantic.py       # Pydantic API models
│   │   ├── postman_generator.py     # Postman Collection export
│   │   ├── pytest_generator.py      # pytest test file export
│   │   ├── session_analyzer.py      # Variable detection, grouping
│   │   ├── test_runner.py           # Async pytest execution
│   │   ├── ticket_generator.py      # Jira/GitHub ticket generation
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py              # Admin key authentication
│   │   │   └── rate_limit.py        # Rate limiting (10/day for anon)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── db_models.py         # Session, SessionData, AnalysisResult
│   │   ├── routers/
│   │   │   └── sessions.py          # Session CRUD endpoints
│   │   └── providers/
│   │       ├── __init__.py
│   │       ├── base.py              # LLMProvider ABC
│   │       ├── gemini.py            # Google Gemini
│   │       └── groq.py              # Groq (Llama 3.3)
│   ├── tests/                       # 54 tests
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── bookmarklet/
│   └── recorder.js                  # ~1880 lines, IIFE pattern
├── dashboard/
│   └── index.html                   # Session list, detail, exports, runner
├── landing/
│   ├── index.html
│   ├── style.css
│   └── favicon.svg
├── nginx/
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
├── ROADMAP.md
├── CONTRIBUTING.md
└── README.md
```

---

## 2. API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/analyze` | AI-powered error analysis |
| POST | `/export/postman` | Generate Postman Collection |
| POST | `/export/pytest` | Generate pytest file |
| POST | `/analyze/session` | Analyze session for test generation |
| POST | `/tickets/generate` | Generate Jira/GitHub ticket |
| POST | `/tests/run` | Start pytest execution |
| GET | `/tests/{id}/status` | Get test run status |
| POST | `/sessions` | Create session with auto-analysis |
| GET | `/sessions` | List sessions (paginated) |
| GET | `/sessions/{id}` | Get session details |
| DELETE | `/sessions/{id}` | Delete session |
| GET | `/sessions/{id}/export/{format}` | Export (markdown/postman/pytest) |

---

## 3. Security

### Rate Limiting
- Anonymous users: 10 requests/day to `/analyze`
- Admin (X-Admin-Key header): unlimited

### Payload Limits
| Parameter | User | Admin |
|-----------|------|-------|
| Console logs | 100 | 1000 |
| Network errors | 10 | 100 |
| Recorded requests | 50 | 500 |

---

## 4. Database

SQLite with async SQLAlchemy (aiosqlite).

### Models
- **Session**: id, url, user_agent, created_at, recording_duration_ms, record_mode
- **SessionData**: console_logs (JSON), network_errors (JSON), js_exceptions (JSON), recorded_requests (JSON), screenshot
- **AnalysisResult**: summary, probable_cause, suggested_fix, severity, details

---

## 5. Bookmarklet Features

| Feature | Status |
|---------|--------|
| Console interception (log/warn/error) | ✅ |
| Network interception (fetch/XHR) | ✅ |
| JS error capture (onerror) | ✅ |
| Screenshot (html2canvas) | ✅ |
| Recording modes (errors/all) | ✅ |
| New pill widget (top-right) | ✅ |
| Classic widget (optional) | ✅ |
| Smart API URL detection | ✅ |
| Junk URL filtering | ✅ |

---

## 6. Dashboard Features

| Feature | Status |
|---------|--------|
| Session list with pagination | ✅ |
| Session detail modal | ✅ |
| Export to Markdown | ✅ |
| Export to Postman | ✅ |
| Export to pytest | ✅ |
| Ticket generator (Jira/GitHub/MD) | ✅ |
| pytest runner with live output | ✅ |
| Delete session | ✅ |

---

## 7. Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, Pydantic |
| Database | SQLite + SQLAlchemy (async) |
| LLM | Groq Llama 3.3 70B |
| Frontend | Vanilla JS |
| Container | Docker, nginx |
| CI/CD | GitHub Actions |

---

## 8. Docker Setup

```bash
# Start
docker-compose up --build

# Services
# - backend: localhost:8000
# - nginx: localhost:3000 (landing, dashboard, API proxy)
```

nginx routes:
- `/` → landing
- `/dashboard/` → dashboard
- `/bookmarklet/` → JS files
- `/api/` → backend proxy

---

*End of Project Snapshot*
