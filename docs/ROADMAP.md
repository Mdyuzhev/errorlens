# ErrorLens Roadmap

## Current Status

| Component | Status |
|-----------|--------|
| Backend | 145/145 tests, CI green |
| Frontend | Vue 3 + Vite |
| Bookmarklet | ES modules + esbuild |
| Post-Deploy Tests | auto on push to main |

## Completed Waves

### Wave 3.2: Code Refactoring
- Bookmarklet modularization (esbuild, -68% size)
- Backend service layer (all routers)
- Frontend component split

### Wave 3.3: QA Infrastructure
- Auto-seed test users on startup
- Post-deploy tests webhook
- Multi-tenancy isolation fix (articles)

### Wave 3.4: CI/CD Fix
- black/isort/ruff formatting
- 145/145 tests passing
- Logging improvements

## Backlog

| Priority | Task |
|----------|------|
| High | Debug session recording data loss |
| Medium | Frontend tests |
| Medium | Rate limiting |
| Low | Dark mode |

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

*Last updated: 2025-12-06*
