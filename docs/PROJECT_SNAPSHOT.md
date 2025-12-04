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
│   │   ├── session_analyzer.py      # Variable detection, grouping
│   │   ├── test_runner.py           # Async pytest execution
│   │   ├── ticket_generator.py      # Smart ticket generation
│   │   ├── generators/              # Test code generators
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # BaseGenerator ABC
│   │   │   ├── pytest.py            # pytest + requests
│   │   │   ├── restassured.py       # REST Assured (Java)
│   │   │   ├── k6.py                # k6 load tests
│   │   │   ├── postman.py           # Postman Collection
│   │   │   ├── cypress.py           # Cypress API tests
│   │   │   └── llm_comments.py      # LLM-generated comments
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
| POST | `/export/restassured` | Generate REST Assured (Java ZIP) |
| POST | `/export/k6` | Generate k6 load test script |
| POST | `/analyze/session` | Analyze session for test generation |
| POST | `/tickets/generate` | Generate smart Jira/GitHub ticket |
| POST | `/tests/run` | Start pytest execution |
| POST | `/tests/run/restassured` | Start REST Assured (Maven) execution |
| GET | `/tests/{id}/status` | Get test run status |
| POST | `/sessions` | Create session with auto-analysis |
| GET | `/sessions` | List sessions (paginated, has_errors/has_requests flags) |
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
| Session filters (All/Bug/Chain) | ✅ |
| Quick 🐍 Test button on session list | ✅ |
| Test status colors (grey/blue/green/red) | ✅ |
| Session detail modal | ✅ |
| Compact button grid in modal footer | ✅ |
| Export to Markdown | ✅ |
| Export to Postman | ✅ |
| Export to pytest | ✅ |
| Export to REST Assured (Java) | ✅ |
| Export to k6 load tests | ✅ |
| Smart ticket generator (auto-steps, timeline) | ✅ |
| Integration stubs (Jira/Slack/Telegram) | ✅ |
| pytest runner with live output | ✅ |
| REST Assured runner (Java/Maven) | ✅ |
| Test type selector (pytest/Java/k6) | ✅ |
| Delete session | ✅ |

---

## 7. Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, Pydantic |
| Database | SQLite + SQLAlchemy (async) |
| LLM | Groq Llama 3.3 70B |
| Frontend | Vanilla JS |
| Container | Docker, nginx, Java 21, Maven 3.9 |
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

---

## 9. Statistics

| Metric | Value |
|--------|-------|
| Python files | ~25 |
| Total backend LOC | ~3000 |
| Tests | 54+ |
| Endpoints | 15+ |
| Generators | 5 (pytest, REST Assured, k6, Postman, Cypress) |

---

*End of Project Snapshot*
