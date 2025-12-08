# Wave 7.0: Bug Fixes + Test Coverage

## Failed Tests Analysis

| Test | File | Root Cause | Fix |
|------|------|------------|-----|
| test_formats_console_logs | test_analyzer.py | Headers: "Логи консоли" → "=== CONSOLE LOGS ===" | Update assertion |
| test_formats_network_errors | test_analyzer.py | Headers: "Сетевые ошибки" → "=== NETWORK ERRORS ===" | Update assertion |
| test_formats_js_exceptions | test_analyzer.py | Headers: "JavaScript исключения" → "=== JS EXCEPTIONS ===" | Update assertion |
| test_raises_when_no_keys | test_analyzer.py | Ollama fallback added | Mock ollama_host="" |
| test_export_postman_requires_auth | test_integration.py | URL: `/exports/` vs `/export/` | Fix URL |
| test_export_pytest_requires_auth | test_integration.py | URL: `/exports/` vs `/export/` | Fix URL |
| loads sessions with recorded_requests | generator.spec.js | setTimeout unreliable | Use flushPromises |
| filters empty sessions | generator.spec.js | setTimeout unreliable | Use flushPromises |

---

## P1: Backend Test Fixes

### File: `tests/test_analyzer.py`

| Line | Current | Expected |
|------|---------|----------|
| 66 | `assert "Логи консоли" in context` | `assert "=== CONSOLE LOGS ===" in context` |
| 88 | `assert "Сетевые ошибки" in context` | `assert "=== NETWORK ERRORS ===" in context` |
| 111 | `assert "JavaScript исключения" in context` | `assert "=== JS EXCEPTIONS ===" in context` |

### Fix: test_raises_when_no_keys (line ~222)

**Problem:** `_get_provider()` now has Ollama fallback
**Solution:** Add `mock_settings.ollama_host = ""` to mock

### File: `tests/test_integration.py`

| Line | Current | Expected |
|------|---------|----------|
| 388 | `/exports/postman` | `/export/postman` |
| 393 | `/exports/pytest` | `/export/pytest` |

---

## P2: Frontend Test Fixes

### File: `tests/generator.spec.js`

**Problem:** `setTimeout(resolve, 100)` unreliable for async operations

**Solution:** Import and use `flushPromises` from `@vue/test-utils`

| Test | Change |
|------|--------|
| loads sessions with recorded_requests | Replace setTimeout with flushPromises |
| filters empty sessions | Replace setTimeout with flushPromises |

**Pattern:**
- Import: `import { flushPromises } from '@vue/test-utils'`
- Replace: `await new Promise(resolve => setTimeout(resolve, 100))` → `await flushPromises()`

---

## P3: Extended Test Coverage

### File: `tests/test_analyzer_extended.py` (create)

**Test cases to implement:**

| Class | Test | Assertion |
|-------|------|-----------|
| TestAnalyzerEdgeCases | test_empty_console_logs | Header not in context when empty |
| | test_empty_network_errors | Header not in context when empty |
| | test_empty_js_exceptions | Header not in context when empty |
| | test_max_console_logs_limit | msg49 in, msg50 not in (limit 50) |
| | test_max_network_errors_limit | a29 in, a30 not in (limit 30) |
| | test_max_js_exceptions_limit | error19 in, error20 not in (limit 20) |
| | test_stack_truncation | Long stack (1000 chars) truncated to 500 |
| | test_none_values_handling | None stack doesn't crash |
| | test_special_characters | Quotes and < > handled |
| TestProviderSelection | test_ollama_fallback | Returns OllamaProvider when only ollama configured |
| | test_explicit_ollama_selection | Returns OllamaProvider when llm_provider=ollama |
| | test_gemini_priority | GeminiProvider when explicitly selected |
| TestLLMResponseParsing | test_nested_json | Handles details as dict |
| | test_unicode_characters | Russian text parsed |
| | test_escaped_quotes | Escaped quotes handled |
| | test_multiline_json | Multiline JSON parsed |

### File: `tests/e2e.spec.js` (create)

**Test cases to implement:**

| Describe | Test | Mock |
|----------|------|------|
| E2E: Generation Flow | full swagger upload flow | post → get mocks |
| | handles API errors | Rejected promise |
| E2E: Session Recording | session list loads | get with items |
| E2E: Auth Flow | login stores token | post with tokens |
| | handles 401 redirect | 401 response |

---

## P4: Integration Tests

### File: `tests/test_integration_extended.py` (create)

**Test cases to implement:**

| Class | Test | Expected |
|-------|------|----------|
| TestExportEndpoints | test_export_postman_no_requests | 400, "No recorded requests" |
| | test_export_pytest_no_requests | 400 |
| | test_export_restassured_no_requests | 400 |
| | test_export_k6_no_requests | 400 |
| | test_export_testit_no_requests | 400 |
| TestGenerationEndpoints | test_from_swagger_empty_paths | 400, "paths" in detail |
| | test_from_session_no_requests | 400 |
| | test_from_session_not_found | 404 |
| TestSessionEndpoints | test_create_session_empty_events | 400 |
| | test_create_session_valid | 200, session_id in response |
| | test_list_sessions_requires_auth | 401 |
| | test_delete_session_requires_auth | 401 |

---

## Prohibited

- Copy-paste test implementations
- Skip fixing existing tests before adding new
- Commit partial fixes

## Quality Gates

- [ ] 6 backend failed → 0
- [ ] 2 frontend failed → 0
- [ ] Extended tests pass
- [ ] Integration tests pass
- [ ] `pytest -v` shows 280+ passed

## Commits

```
[Wave 7.0] P1: Fix backend test assertions
[Wave 7.0] P2: Fix frontend async tests
[Wave 7.0] P3: Add extended test coverage
[Wave 7.0] P4: Add integration tests
```
