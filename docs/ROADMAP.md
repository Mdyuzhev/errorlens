# ErrorLens Roadmap

> Актуальный статус разработки и планы на будущее.

---

## Completed Waves

### Wave 3.2: Code Refactoring ✅
- Bookmarklet modularization (esbuild, -68% size)
- Backend service layer (all routers)
- Frontend component split
- 42 unit tests

### Wave 3.3: QA Infrastructure ✅
- Auto-seed test users on startup
- Post-deploy tests webhook (GitHub Actions)
- Multi-tenancy isolation fix (articles)
- Concurrency control for workflows

---

## Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| Backend | ✅ Stable | 136/145 tests passing |
| Frontend | ✅ Stable | Vue 3 + Vite |
| Bookmarklet | ✅ Stable | ES modules + esbuild |
| Post-Deploy Tests | ✅ Working | Runs on every push to main |
| CI Lint | ❌ Failing | black/isort formatting issues |

---

## Backlog (Wave 3.4+)

### High Priority

| Task | Description | Effort |
|------|-------------|--------|
| Fix CI lint | Run black/isort to fix formatting | S |
| Session recording bug | Debug bookmarklet→backend data loss | M |
| Fix 9 failing tests | Update test assertions for new API | S |

### Medium Priority

| Task | Description | Effort |
|------|-------------|--------|
| Frontend tests | Add Vue component tests | M |
| API documentation | OpenAPI/Swagger improvements | S |
| Rate limiting | Protect public endpoints | M |

### Low Priority / Nice to Have

| Task | Description | Effort |
|------|-------------|--------|
| Dark mode | Dashboard theme toggle | S |
| Export formats | Add CSV, PDF export | M |
| Notifications | Email/Slack on new errors | L |
| Mobile responsive | Dashboard mobile layout | M |

---

## Known Issues

1. **CI Lint failing** — black/isort not run before commits
2. **9 unit tests failing** — outdated assertions (auth, model names)
3. **Session recording** — reported data loss (needs investigation)

---

## Infrastructure

| Service | Environment | URL |
|---------|-------------|-----|
| Backend | Docker | http://localhost:8000 |
| Database | Docker | PostgreSQL 16 (Docker Compose) |
| CI/CD | GitHub Actions | Tests on push |

---

## Test Users (Auto-seeded)

| User | Password | Project | Role |
|------|----------|---------|------|
| demo | ErrorLenseTest | - | system |
| owner1 | Test123! | Alpha | owner |
| owner2 | Test123! | Beta | owner |
| admin1 | Test123! | Alpha | admin |
| member1 | Test123! | Alpha | member |
| member2 | Test123! | Beta | member |
| viewer1 | Test123! | Alpha | viewer |
| viewer2 | Test123! | Beta | viewer |

---

*Last updated: 2025-12-06*
