# Wave 7.0 P5: E2E UI Tests (Cypress)

## Scope

Full UI coverage through Cypress. All routes, all CRUD operations, all user flows.

## Setup

### Install

```bash
cd dashboard-vue
npm install -D cypress @testing-library/cypress
```

### Config: `cypress.config.js`

| Setting | Value |
|---------|-------|
| baseUrl | http://localhost:5173 |
| viewportWidth | 1280 |
| viewportHeight | 720 |
| video | true |
| screenshotOnRunFailure | true |
| defaultCommandTimeout | 10000 |

### Run Commands

| Command | Description |
|---------|-------------|
| `npx cypress open` | Interactive UI runner |
| `npx cypress run` | Headless CI mode |
| `npx cypress run --spec "cypress/e2e/articles.cy.js"` | Single spec |

## Routes to Cover

| Route | View | Store | Priority |
|-------|------|-------|----------|
| /login | LoginView | auth | P0 |
| / | DashboardView | sessions | P0 |
| /sessions/:id | DashboardView | sessions | P1 |
| /articles | ArticlesView | articles | P0 |
| /articles/:slug | ArticlesView | articles | P1 |
| /testcases | TestCasesView | testcases | P0 |
| /testcases/:id | TestCasesView | testcases | P1 |
| /tasks | TasksView | tasks | P0 |
| /tasks/:id | TasksView | tasks | P1 |
| /generator | GeneratorView | generation | P0 |
| /generator/:sessionId | GeneratorView | generation | P1 |
| /results | ResultsView | - | P1 |
| /settings | SettingsView | - | P1 |

---

## Test Structure

```
dashboard-vue/
├── cypress/
│   ├── e2e/
│   │   ├── auth.cy.js
│   │   ├── articles.cy.js
│   │   ├── testcases.cy.js
│   │   ├── tasks.cy.js
│   │   ├── sessions.cy.js
│   │   ├── generator.cy.js
│   │   ├── settings.cy.js
│   │   └── navigation.cy.js
│   ├── fixtures/
│   │   └── test-data.json
│   └── support/
│       ├── commands.js
│       └── e2e.js
├── cypress.config.js
```

### Custom Commands: `cypress/support/commands.js`

| Command | Signature | Purpose |
|---------|-----------|---------|
| cy.login | (email, password) | Login and store token |
| cy.logout | () | Clear token, redirect |
| cy.createArticle | (data) | API create + return id |
| cy.createTestCase | (data) | API create + return id |
| cy.createTask | (data) | API create + return id |
| cy.resetDb | () | Clear test data |
| cy.seedData | (fixture) | Load fixture data |

---

## P5.1: Auth Tests

### File: `tests/e2e/auth.spec.js`

| Test | Steps | Assertion |
|------|-------|-----------|
| login_success | Navigate /login → fill email/password → click Login | Redirect to /, token in localStorage |
| login_invalid_credentials | Fill wrong password → submit | Error message visible, stay on /login |
| login_empty_fields | Click Login without filling | Validation error shown |
| logout | Login → click Logout in navbar | Redirect to /login, token removed |
| auth_guard_redirect | Navigate / without token | Redirect to /login |
| auth_guard_allows | Set valid token → navigate / | Page loads, no redirect |
| token_refresh | Wait for token expiry → make request | Auto-refresh, request succeeds |
| remember_me | Login with remember → close/reopen | Still authenticated |

---

## P5.2: Articles Tests

### File: `tests/e2e/articles.spec.js`

| Test | Steps | Assertion |
|------|-------|-----------|
| list_articles | Login → navigate /articles | Articles list visible, count > 0 |
| create_article | Click "New" → fill title/content/category → Save | Article in list, toast "Created" |
| create_article_validation | Click Save with empty title | Validation error shown |
| view_article | Click article in list | Modal/detail opens with content |
| edit_article | Open article → change title → Save | Updated title in list |
| edit_preserves_data | Edit → change one field → Save | Other fields unchanged |
| delete_article | Open article → click Delete → confirm | Article removed from list |
| delete_cancel | Click Delete → cancel | Article still in list |
| filter_by_category | Select category filter | Only matching articles shown |
| filter_by_status | Select status filter | Only matching articles shown |
| search_articles | Type in search box | Filtered results |
| empty_state | Delete all articles | "No articles" message |
| pagination | Create 20+ articles | Pagination controls work |

---

## P5.3: TestCases Tests

### File: `tests/e2e/testcases.spec.js`

| Test | Steps | Assertion |
|------|-------|-----------|
| list_testcases | Navigate /testcases | List visible |
| create_testcase | Click New → fill title/steps/expected → Save | TestCase in list |
| create_with_priority | Set priority High → Save | Priority badge visible |
| view_testcase | Click testcase | Detail view with steps |
| edit_testcase | Edit title → Save | Updated in list |
| delete_testcase | Delete → confirm | Removed from list |
| filter_by_folder | Select folder | Filtered results |
| filter_by_status | Select status | Filtered results |
| filter_by_priority | Select priority | Filtered results |
| drag_to_folder | Drag testcase to folder | Folder updated |
| bulk_delete | Select multiple → Delete | All removed |
| export_testcase | Click Export | File downloaded |

---

## P5.4: Tasks Tests

### File: `tests/e2e/tasks.spec.js`

| Test | Steps | Assertion |
|------|-------|-----------|
| view_board | Navigate /tasks | Kanban board with columns |
| create_task | Click + → fill title/description → Save | Task in TODO column |
| move_task_drag | Drag task to IN_PROGRESS | Task in new column |
| move_task_dropdown | Open task → change status dropdown | Task moves to column |
| edit_task | Edit description → Save | Updated content |
| delete_task | Delete → confirm | Removed from board |
| assign_task | Set assignee | Assignee avatar shown |
| set_due_date | Set due date | Date badge visible |
| overdue_highlight | Set past due date | Red highlight |
| filter_by_assignee | Select assignee filter | Filtered tasks |
| task_comments | Add comment | Comment visible |
| task_attachments | Upload file | Attachment shown |

---

## P5.5: Sessions Tests

### File: `tests/e2e/sessions.spec.js`

| Test | Steps | Assertion |
|------|-------|-----------|
| list_sessions | Navigate / | Sessions list visible |
| view_session_detail | Click session card | Modal with details |
| view_console_logs | Open session with logs | Console logs tab visible |
| view_network_errors | Open session with errors | Network tab with errors |
| view_js_exceptions | Open session with exceptions | Exceptions tab |
| view_recorded_requests | Open session with requests | HAR data visible |
| filter_all | Click "All" filter | All sessions shown |
| filter_bugs | Click "Bugs" filter | Only error sessions |
| filter_chains | Click "Chains" filter | Only sessions with requests |
| delete_session | Delete → confirm | Removed from list |
| analyze_session | Click Analyze | Analysis results shown |
| export_session | Click Export | JSON downloaded |
| generate_from_session | Click "Generate Tests" | Redirect to /generator/:id |

---

## P5.6: Generator Tests

### File: `tests/e2e/generator.spec.js`

| Test | Steps | Assertion |
|------|-------|-----------|
| upload_swagger_json | Select JSON file | File name shown, Generate enabled |
| upload_swagger_yaml | Select YAML file | File accepted |
| upload_invalid_file | Select .txt file | Error message |
| select_framework_pytest | Click pytest card | Selected state |
| select_framework_postman | Click postman card | Selected state |
| select_provider | Select Anthropic | Provider shown |
| select_model | Select model | Model shown |
| generate_from_swagger | Upload → select options → Generate | Progress bar, then results |
| generate_from_session | Navigate /generator/:sessionId | Auto-load session, generate |
| generation_progress | Start generation | Progress %, current endpoint, logs |
| generation_complete | Wait for completion | Results summary, download button |
| download_zip | Click Download | ZIP file downloaded |
| view_generated_code | Click Preview | Code with syntax highlighting |
| copy_code | Click Copy | Copied to clipboard |
| generation_error | Use invalid swagger | Error message shown |
| retry_generation | After error → click Retry | New attempt starts |
| history_shows_generation | Complete generation | Entry in history panel |
| history_redownload | Click redownload in history | ZIP downloaded |
| tab_swagger | Click Swagger tab | Upload component shown |
| tab_session | Click Session tab | Session selector shown |
| tab_url | Click URL tab | URL input shown |
| url_add_endpoint | Add GET /api/users | Endpoint in list |
| url_remove_endpoint | Click X on endpoint | Removed from list |
| url_generate | Add endpoints → Generate | Generation starts |

---

## P5.7: Settings Tests

### File: `tests/e2e/settings.spec.js`

| Test | Steps | Assertion |
|------|-------|-----------|
| view_settings | Navigate /settings | Settings page loads |
| change_theme | Toggle dark/light | Theme changes |
| save_api_key | Enter API key → Save | Key masked, "Configured" shown |
| clear_api_key | Click Clear | Key removed |
| change_default_provider | Select provider | Saved to localStorage |
| change_default_model | Select model | Saved |
| export_settings | Click Export | JSON downloaded |
| import_settings | Upload settings JSON | Settings applied |
| profile_update | Change name → Save | Name updated |
| password_change | Enter old/new password → Save | Success message |
| notification_toggle | Toggle notifications | Setting saved |

---

## P5.8: Navigation Tests

### File: `tests/e2e/navigation.spec.js`

| Test | Steps | Assertion |
|------|-------|-----------|
| navbar_links | Click each nav link | Correct route navigated |
| breadcrumb_navigation | Click breadcrumb | Navigate to parent |
| back_button | Click back | Previous page |
| deep_link | Navigate directly to /articles/test-slug | Article opens |
| 404_handling | Navigate /nonexistent | 404 page or redirect |
| mobile_menu | Resize to mobile → click hamburger | Menu opens |
| keyboard_navigation | Tab through elements | Focus visible |

---

## Test Fixtures

### File: `tests/e2e/fixtures/test-data.json`

| Fixture | Fields |
|---------|--------|
| testUser | email, password |
| testArticle | title, content, category, status |
| testTestCase | title, steps[], expected, priority |
| testTask | title, description, status, assignee |
| testSwagger | OpenAPI 3.0 spec with 3 endpoints |
| testSession | url, console_logs[], recorded_requests[] |

---

## Setup Requirements

### Cypress Config: `cypress.config.js`

| Setting | Value |
|---------|-------|
| baseUrl | http://localhost:5173 |
| viewportWidth | 1280 |
| viewportHeight | 720 |
| video | true |
| screenshotOnRunFailure | true |
| defaultCommandTimeout | 10000 |
| retries.runMode | 2 |
| retries.openMode | 0 |

### Before All

1. Start backend: `cd backend && uvicorn app.main:app`
2. Start frontend: `cd dashboard-vue && npm run dev`
3. Seed test data via API or fixtures

### Before Each (in support/e2e.js)

1. `cy.resetDb()` - Reset database to known state
2. `cy.clearLocalStorage()` - Clear tokens
3. `cy.login()` - Login as test user (where needed)

### Run Tests

| Mode | Command | Description |
|------|---------|-------------|
| Interactive | `npx cypress open` | Visual runner with time-travel debug |
| Headless | `npx cypress run` | CI mode with video recording |
| Single spec | `npx cypress run --spec "cypress/e2e/articles.cy.js"` | Run one file |
| Browser | `npx cypress open --browser chrome` | Specific browser |

---

## Quality Gates

- [ ] All 13 routes covered
- [ ] All CRUD operations tested
- [ ] All filters/search tested
- [ ] Error states tested
- [ ] Empty states tested
- [ ] Mobile responsive tested
- [ ] 80+ test cases total
- [ ] All tests green

## Commits

```
[Wave 7.0] P5.1: Add auth E2E tests
[Wave 7.0] P5.2: Add articles E2E tests
[Wave 7.0] P5.3: Add testcases E2E tests
[Wave 7.0] P5.4: Add tasks E2E tests
[Wave 7.0] P5.5: Add sessions E2E tests
[Wave 7.0] P5.6: Add generator E2E tests
[Wave 7.0] P5.7: Add settings E2E tests
[Wave 7.0] P5.8: Add navigation E2E tests
```
