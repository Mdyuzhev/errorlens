# ErrorLens - Project Snapshot

> Architecture review document. Last updated: 2025-12-04 (JWT Auth added)

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
│   │   │   ├── auth.py              # Admin key authentication (legacy)
│   │   │   ├── jwt_auth.py          # JWT authentication middleware
│   │   │   └── rate_limit.py        # Rate limiting (10/day for anon)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── db_models.py         # Session, SessionData, AnalysisResult
│   │   │   └── user.py              # User model (bcrypt password)
│   │   ├── routers/
│   │   │   ├── auth.py              # Authentication endpoints
│   │   │   └── sessions.py          # Session CRUD endpoints
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── auth.py              # JWT token service
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
│   ├── index.html                   # Session list, detail, exports, runner
│   └── login.html                   # Login page
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

### Public Endpoints (no auth required)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/auth/login` | Get JWT tokens (access + refresh) |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Logout (client discards tokens) |
| POST | `/sessions` | Create session with auto-analysis |

### Protected Endpoints (require Bearer token)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/auth/me` | Get current user info |
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
| GET | `/sessions` | List sessions (paginated, has_errors/has_requests flags) |
| GET | `/sessions/{id}` | Get session details |
| DELETE | `/sessions/{id}` | Delete session |
| GET | `/sessions/{id}/export/{format}` | Export (markdown/postman/pytest)

---

## 3. Security

### JWT Authentication
- Access token: 30 min expiry
- Refresh token: 7 days expiry
- Algorithm: HS256
- Auto-created admin user on startup

### Environment Variables
```bash
JWT_SECRET_KEY=your-super-secret-key-min-32-chars  # REQUIRED for production
ADMIN_PASSWORD=your-secure-password                 # Default: admin123
```

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
- **User**: id, username, hashed_password (bcrypt), is_active, is_admin, created_at, last_login
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
| JWT authentication (login page) | ✅ |
| Auto token refresh | ✅ |
| Logout button | ✅ |
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
| Python files | ~30 |
| Total backend LOC | ~3500 |
| Tests | 80+ |
| Endpoints | 20+ |
| Generators | 5 (pytest, REST Assured, k6, Postman, Cypress) |

---

## 10. Quick Start (Local)

```bash
# Clone & start
git clone https://github.com/Mdyuzhev/errorlens.git
cd errorlens
docker-compose up --build

# Open dashboard
# http://localhost:3000/dashboard/
# Login: admin / admin123
```

---

*End of Project Snapshot*
