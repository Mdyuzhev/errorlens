# ErrorLens Agent Context

## Project

| Field | Value |
|-------|-------|
| Name | ErrorLens |
| Type | AI-powered QA platform |
| Production | https://errorlens-production.up.railway.app |
| Repo | github.com/Mdyuzhev/errorlens |

## Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI, SQLAlchemy async, Alembic |
| Database | PostgreSQL (prod), SQLite (dev) |
| Frontend | Vue 3, Vite, Pinia, TailwindCSS |
| LLM | Anthropic, OpenAI, Groq, Gemini, Ollama, GigaChat |
| Auth | JWT (access 30min, refresh 7days) |

## Architecture

```
Router → Service → Repository → Model
```

Violations not permitted.

## Code Requirements

### Python

| Requirement | Details |
|-------------|---------|
| Type hints | All functions, all parameters |
| Async | All I/O operations |
| Max file size | 500 LOC |
| Exceptions | Specific types only, no bare `except` |
| Memory | Explicit cleanup, TTL for caches |

### Memory Management

Required for all dict/cache storage:
```python
# TTL cleanup
MAX_AGE = 3600
def cleanup():
    cutoff = time.time() - MAX_AGE
    expired = [k for k, v in cache.items() if v.created < cutoff]
    for k in expired:
        del cache[k]
```

### Tests

| Category | Required |
|----------|----------|
| Unit | All public methods |
| Edge cases | Empty, None, duplicates |
| Errors | All exception paths |
| Concurrency | Parallel access |
| Memory | Leak detection |

Required test functions per feature:
- `test_empty_input()`
- `test_none_handling()`
- `test_duplicate_handling()`
- `test_concurrent_access()`
- `test_memory_cleanup()`
- `test_error_recovery()`

### WebSocket

| Requirement | Value |
|-------------|-------|
| State storage | Redis or DB, not in-memory |
| Reconnection | Exponential backoff client-side |
| Timeout | 120s max |
| Cleanup | Explicit on disconnect |

## Git

| Item | Value |
|------|-------|
| Main branch | main |
| Work branch | feature/* |
| Commit format | `[Wave X.Y] PX: Description` |

## Phase Execution

1. Read instruction (interfaces + requirements only)
2. Write implementation independently
3. Write all required tests
4. Verify memory management
5. Run tests, fix failures
6. Commit
7. Next phase

## Prohibited

- Skip phases
- Copy full implementations from instructions
- Bare `except:`
- In-memory state for distributed systems
- Commit without tests
- Files >500 LOC
- Ask confirmation

## Instruction Format

Instructions contain:
- Interface signatures
- Requirements list
- Prohibited patterns
- Test cases

Instructions do NOT contain:
- Full implementations
- Ready-to-copy code

Agent writes code independently.

## Current Wave

| Field | Value |
|-------|-------|
| Number | 4.0 |
| Name | Sharmanka Migration |
| Order | P1 → P2 → P3 → P4 → P5 → P6 → P7 |

## Quality Gates

Phase complete when:
- [ ] All tests pass
- [ ] No bare except
- [ ] Memory cleanup exists
- [ ] Concurrent access tested
- [ ] Edge cases covered
- [ ] <500 LOC per file
