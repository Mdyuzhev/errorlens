# Post-Deploy Verification Checklist

**Purpose:** 17-minute verification procedure for multi-tenancy deployment

---

## Prerequisites

Before running verification:

1. **Database backup** — ensure you have a backup before applying migrations
2. **Migration applied** — run `alembic upgrade head` in backend/
3. **Server running** — `uvicorn app.main:app --port 8765`
4. **Admin credentials** — have admin/admin123 ready for seeding

---

## Rollback Procedure

If verification fails critically:

```bash
# 1. Stop the server
# 2. Rollback migration
cd backend
alembic downgrade -1

# 3. Restore database backup (if needed)
# SQLite: cp backup.db errorlens.db
# PostgreSQL: pg_restore -d errorlens backup.dump

# 4. Restart with previous code version
git checkout HEAD~1
uvicorn app.main:app --reload
```

---

## Known Acceptable Failures

These test failures exist before multi-tenancy and are NOT blockers:

| Test | Reason | Status |
|------|--------|--------|
| `test_includes_recording_duration` | Cyrillic "мс" vs "ms" encoding | Pre-existing |
| `test_formats_console_logs` | Same encoding issue | Pre-existing |
| `test_formats_network_errors` | Same encoding issue | Pre-existing |
| `test_formats_js_exceptions` | Same encoding issue | Pre-existing |
| `test_fallback_on_invalid_json` | JSON parsing logic change | Pre-existing |
| `test_analyze_rejects_empty_data` | API validation behavior | Pre-existing |
| `test_analyze_validates_required_fields` | API validation behavior | Pre-existing |
| `test_analyze_accepts_valid_request` | Auth requirement added | Pre-existing |
| `test_groq_uses_correct_model` | Model llama-3.3 vs 3.1 | Pre-existing |

**Target:** 136/145 tests passing (93.8%) is acceptable for Phase 1.

---

## Verification Checks

### Check 1: Database Schema (2 min)

```bash
# Verify project_id columns exist
sqlite3 backend/errorlens.db ".schema sessions" | grep project_id
sqlite3 backend/errorlens.db ".schema test_cases" | grep project_id
sqlite3 backend/errorlens.db ".schema tasks" | grep project_id
sqlite3 backend/errorlens.db ".schema articles" | grep project_id
```

**Expected:** All 4 tables show `project_id` column.

---

### Check 2: Seed Test Users (3 min)

```bash
# Login as admin
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8765/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.access_token')

# Seed test users
curl -s -X POST http://localhost:8765/admin/seed-test-users \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Verify owner1 login
curl -s -X POST http://localhost:8765/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"owner1","password":"test123"}' | jq
```

**Expected:**
- Seed returns 6 users and 2 projects
- owner1 login returns access_token

---

### Check 3: Multi-tenancy Isolation (5 min)

```bash
# Get owner1 token and project
OWNER1_TOKEN=$(curl -s -X POST http://localhost:8765/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"owner1","password":"test123"}' | jq -r '.access_token')

PROJECT_ALPHA=$(curl -s http://localhost:8765/projects \
  -H "Authorization: Bearer $OWNER1_TOKEN" | jq -r '.items[0].id')

# Create session in Project Alpha
SESSION_ID=$(curl -s -X POST http://localhost:8765/sessions \
  -H "Authorization: Bearer $OWNER1_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"https://test.com\",
    \"user_agent\": \"Test Agent\",
    \"project_id\": \"$PROJECT_ALPHA\",
    \"console_logs\": [{\"level\": \"error\", \"message\": \"Test error\", \"timestamp\": 1234567890}]
  }" | jq -r '.session_id')

echo "Created session: $SESSION_ID"

# Get owner2 token
OWNER2_TOKEN=$(curl -s -X POST http://localhost:8765/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"owner2","password":"test123"}' | jq -r '.access_token')

# Try to access owner1's session - should get 403 or not see it
curl -s http://localhost:8765/sessions/$SESSION_ID \
  -H "Authorization: Bearer $OWNER2_TOKEN" | jq
```

**Expected:** owner2 cannot access owner1's session (403 or empty).

---

### Check 4: QA Webhook (3 min)

```bash
# Test /debug/echo endpoint
curl -s -X POST http://localhost:8765/debug/echo \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}' | jq
```

**Expected:** Returns echo of request body.

---

### Check 5: Full Test Suite (4 min)

```bash
cd backend
pytest -v --tb=short 2>&1 | tail -20
```

**Expected:** 136+ tests passing (93%+). See Known Acceptable Failures above.

---

## Results Summary

| Check | Status | Notes |
|-------|--------|-------|
| 1. DB Schema | | |
| 2. Seed Users | | |
| 3. Multi-tenancy | | |
| 4. QA Webhook | | |
| 5. Test Suite | | |

**Overall:** PASS / FAIL

---

*Last updated: 2025-12-06*
