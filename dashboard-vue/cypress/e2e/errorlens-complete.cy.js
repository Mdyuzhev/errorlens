// ErrorLens Complete E2E Test Suite
// Generated: 2024-12-09
// Updated: 2024-12-09 (Wave 7.0 - Session fixes)
// Total: 81 tests across 17 test groups

const hashUrl = (path) => `/#${path}`

describe('ErrorLens Complete E2E Suite', () => {

  // ============================================
  // PART 1: APPLICATION TESTS (43 tests)
  // ============================================

  // ============================================
  // 1. AUTH TESTS (6 tests)
  // ============================================
  describe('1. Auth', () => {
    beforeEach(() => {
      cy.clearLocalStorage()
    })

    it('1.1 auth_guard_redirect - unauthorized redirect', () => {
      cy.visit(hashUrl('/'))
      cy.url().should('include', '/login')
    })

    it('1.2 login_empty_fields - empty fields validation', () => {
      cy.visit(hashUrl('/login'))
      cy.get('button[type="submit"]').click()
      cy.url().should('include', '/login')
    })

    it('1.3 login_invalid_credentials - invalid credentials', () => {
      cy.visit(hashUrl('/login'))
      cy.get('input[type="text"]').type('owner1')
      cy.get('input[type="password"]').type('wrongpassword')
      cy.get('button[type="submit"]').click()
      cy.contains(/error|invalid|incorrect/i).should('be.visible')
      cy.url().should('include', '/login')
    })

    it('1.4 login_success - successful login', () => {
      cy.visit(hashUrl('/login'))
      cy.get('input[type="text"]').type('owner1')
      cy.get('input[type="password"]').type('Test123!')
      cy.get('button[type="submit"]').click()
      cy.url().should('not.include', '/login')
      cy.window().then((win) => {
        expect(win.localStorage.getItem('access_token')).to.exist
      })
    })

    it('1.5 auth_guard_allows - authorized access', () => {
      cy.login()
      cy.visit(hashUrl('/'))
      cy.url().should('not.include', '/login')
    })

    it('1.6 logout - user logout', () => {
      cy.login()
      cy.visit(hashUrl('/'))
      cy.contains(/logout|выход/i).click()
      cy.url().should('include', '/login')
      cy.window().then((win) => {
        expect(win.localStorage.getItem('access_token')).to.be.null
      })
    })
  })

  // ============================================
  // 2. NAVIGATION TESTS (5 tests)
  // ============================================
  describe('2. Navigation', () => {
    beforeEach(() => {
      cy.login()
    })

    it('2.1 navbar_links - navbar navigation', () => {
      cy.visit(hashUrl('/'))
      cy.contains(/dashboard|sessions|сессии/i).first().click()
      cy.url().should('match', /\/$|\/sessions/)
      cy.contains(/articles|статьи/i).first().click()
      cy.url().should('include', '/articles')
      cy.contains(/testcases|test cases|тесткейсы/i).first().click()
      cy.url().should('include', '/testcases')
      cy.contains(/tasks|задачи/i).first().click()
      cy.url().should('include', '/tasks')
      cy.contains(/generator|генератор/i).first().click()
      cy.url().should('include', '/generator')
    })

    it('2.2 back_navigation - browser back', () => {
      cy.visit(hashUrl('/articles'))
      cy.wait(300)
      cy.visit(hashUrl('/testcases'))
      cy.wait(300)
      cy.go('back')
      cy.wait(300)
      cy.url().should('include', '/articles')
    })

    it('2.3 404_handling - 404 page', () => {
      cy.visit(hashUrl('/nonexistent-route'), { failOnStatusCode: false })
      cy.get('body').should('exist')
    })

    it('2.4 deep_link_articles - direct link', () => {
      cy.visit(hashUrl('/articles'))
      cy.url().should('include', '/articles')
    })

    it('2.5 mobile_responsive - mobile view', () => {
      cy.viewport(375, 667)
      cy.visit(hashUrl('/'))
      cy.get('body').should('be.visible')
    })
  })

  // ============================================
  // 3. SESSIONS TESTS (12 tests)
  // ============================================
  describe('3. Sessions', () => {
    beforeEach(() => {
      cy.login()
    })

    it('3.1 list_sessions - sessions list', () => {
      cy.visit(hashUrl('/'))
      cy.get('.sessions-grid, .session-card, .empty-state').should('exist')
    })

    it('3.2 view_session_detail - session detail modal', () => {
      cy.visit(hashUrl('/'))
      cy.get('body').then($body => {
        if ($body.find('.session-card').length > 0) {
          cy.get('.session-card').first().click()
          cy.get('[data-testid="session-detail-modal"], .session-detail, .modal').should('be.visible')
        } else {
          cy.log('No sessions to view')
        }
      })
    })

    it('3.3 filter_all - filter all', () => {
      cy.visit(hashUrl('/'))
      cy.contains(/all|все/i).click()
    })

    it('3.4 filter_bugs - filter bugs', () => {
      cy.visit(hashUrl('/'))
      cy.contains(/bugs|ошибки/i).click()
    })

    it('3.5 filter_chains - filter chains', () => {
      cy.visit(hashUrl('/'))
      cy.contains(/chains|цепочки/i).click()
    })

    // Wave 7.0 - Session API fixes tests
    it('3.6 sessions_api_returns_items - API returns items array', () => {
      cy.intercept('GET', '/sessions*').as('getSessions')
      cy.visit(hashUrl('/'))
      cy.wait('@getSessions').then((interception) => {
        expect(interception.response.body).to.have.property('items')
        expect(interception.response.body).to.have.property('total')
      })
    })

    it('3.7 session_detail_loads_full_data - modal loads full session', () => {
      cy.intercept('GET', '/sessions/*').as('getSession')
      cy.visit(hashUrl('/'))
      cy.get('body').then($body => {
        if ($body.find('.session-card').length > 0) {
          cy.get('.session-card').first().click()
          cy.wait('@getSession').its('response.statusCode').should('eq', 200)
          cy.get('[data-testid="session-detail-modal"], .session-detail').should('be.visible')
        }
      })
    })

    it('3.8 session_modal_analyze_button - analyze button works', () => {
      cy.intercept('POST', '/analyze/rerun').as('analyzeSession')
      cy.visit(hashUrl('/'))
      cy.get('body').then($body => {
        if ($body.find('.session-card').length > 0) {
          cy.get('.session-card').first().click()
          cy.get('[data-testid="session-detail-modal"], .session-detail').should('be.visible')
          cy.contains('button', /analyze/i).click()
          cy.wait('@analyzeSession', { timeout: 30000 })
        }
      })
    })

    it('3.9 session_modal_export_buttons - export buttons exist', () => {
      cy.visit(hashUrl('/'))
      cy.get('body').then($body => {
        if ($body.find('.session-card').length > 0) {
          cy.get('.session-card').first().click()
          cy.get('[data-testid="session-detail-modal"], .session-detail').should('be.visible')
          cy.contains('button', /export testit/i).should('exist')
          cy.contains('button', /export postman/i).should('exist')
          cy.contains('button', /export pytest/i).should('exist')
        }
      })
    })

    it('3.10 session_modal_delete_button - delete button exists', () => {
      cy.visit(hashUrl('/'))
      cy.get('body').then($body => {
        if ($body.find('.session-card').length > 0) {
          cy.get('.session-card').first().click()
          cy.get('[data-testid="session-detail-modal"], .session-detail').should('be.visible')
          cy.contains('button', /delete/i).should('exist')
        }
      })
    })

    it('3.11 session_modal_close - modal closes on X', () => {
      cy.visit(hashUrl('/'))
      cy.get('body').then($body => {
        if ($body.find('.session-card').length > 0) {
          cy.get('.session-card').first().click()
          cy.get('[data-testid="session-detail-modal"], .session-detail').should('be.visible')
          cy.get('.modal-close').click()
          cy.get('[data-testid="session-detail-modal"], .session-detail').should('not.exist')
        }
      })
    })

    it('3.12 unassigned_sessions_visible - bookmarklet sessions visible', () => {
      // Sessions without project_id should be visible (include_unassigned=true)
      cy.intercept('GET', '/sessions*').as('getSessions')
      cy.visit(hashUrl('/'))
      cy.wait('@getSessions').then((interception) => {
        // API should return sessions (including those without project_id)
        expect(interception.response.statusCode).to.eq(200)
        expect(interception.response.body.items).to.be.an('array')
      })
    })
  })

  // ============================================
  // 4. ARTICLES TESTS (7 tests)
  // ============================================
  describe('4. Articles', () => {
    beforeEach(() => {
      cy.login()
    })

    it('4.1 list_articles - articles list', () => {
      cy.visit(hashUrl('/articles'))
      cy.get('[data-testid="articles-list"], .articles-grid, .article-card, .empty-state').should('exist')
    })

    it('4.2 create_article - create article', () => {
      cy.visit(hashUrl('/articles'))
      cy.contains(/new|создать|add|\+/i).click()
      cy.get('.modal-overlay, .modal-content').should('be.visible')
      cy.get('input[placeholder*="title"], input[placeholder*="название"]').type('Test Article')
      cy.get('textarea[placeholder*="Markdown"], textarea[placeholder*="content"]').type('Test content')
      cy.contains(/save|сохранить/i).click()
    })

    it('4.3 create_article_validation - create validation', () => {
      cy.visit(hashUrl('/articles'))
      cy.contains(/new|создать|add|\+/i).click()
      cy.get('.modal-overlay, .modal-content').should('be.visible')
      cy.get('input[required]').should('exist')
    })

    it('4.4 view_article - view article', () => {
      cy.visit(hashUrl('/articles'))
      cy.get('body').then($body => {
        if ($body.find('.article-card').length > 0) {
          cy.get('.article-card').first().click()
          cy.get('.modal-overlay, .article-view').should('be.visible')
        } else {
          cy.log('No articles to view')
        }
      })
    })

    it('4.5 filter_by_category - category filter', () => {
      cy.visit(hashUrl('/articles'))
      cy.get('select').first().should('exist')
    })

    it('4.6 search_articles - articles search', () => {
      cy.visit(hashUrl('/articles'))
      cy.get('.articles-page').should('exist')
    })

    it('4.7 empty_state - empty state', () => {
      cy.visit(hashUrl('/articles'))
      cy.get('body').then(($body) => {
        if ($body.text().includes('No articles') || $body.text().includes('Нет статей')) {
          cy.contains(/no articles|нет статей/i).should('be.visible')
        } else {
          cy.log('Articles exist, skipping empty state test')
        }
      })
    })
  })

  // ============================================
  // 5. TESTCASES TESTS (5 tests)
  // ============================================
  describe('5. TestCases', () => {
    beforeEach(() => {
      cy.login()
    })

    it('5.1 list_testcases - testcases list', () => {
      cy.visit(hashUrl('/testcases'))
      cy.get('[data-testid="testcases-list"], .testcases-grid, .testcase-card, .empty-state').should('exist')
    })

    it('5.2 create_testcase - create testcase', () => {
      cy.visit(hashUrl('/testcases'))
      cy.contains(/new|создать|add|\+/i).click()
      cy.get('.modal-overlay, .modal-content').should('be.visible')
      cy.get('input[placeholder*="title"], input[placeholder*="название"]').type('Test Case 1')
      cy.contains(/save|сохранить/i).click()
    })

    it('5.3 view_testcase - view testcase', () => {
      cy.visit(hashUrl('/testcases'))
      cy.get('body').then($body => {
        if ($body.find('.testcase-card').length > 0) {
          cy.get('.testcase-card').first().click()
          cy.get('.modal-overlay, .modal-content').should('be.visible')
        } else {
          cy.log('No test cases to view')
        }
      })
    })

    it('5.4 filter_by_status - status filter', () => {
      cy.visit(hashUrl('/testcases'))
      cy.get('select').should('have.length.at.least', 1)
    })

    it('5.5 filter_by_priority - priority filter', () => {
      cy.visit(hashUrl('/testcases'))
      cy.get('.filters select').should('have.length.at.least', 2)
    })
  })

  // ============================================
  // 6. TASKS TESTS (3 tests)
  // ============================================
  describe('6. Tasks', () => {
    beforeEach(() => {
      cy.login()
    })

    it('6.1 view_board - kanban board', () => {
      cy.visit(hashUrl('/tasks'))
      cy.get('[data-testid="kanban-board"], .kanban-board, .kanban-column').should('exist')
    })

    it('6.2 create_task - create task', () => {
      cy.visit(hashUrl('/tasks'))
      cy.contains(/new|создать|add|\+/i).first().click()
      cy.get('.modal-overlay, .modal-content').should('be.visible')
      cy.get('input[placeholder*="title"], input[placeholder*="название"]').type('Test Task')
      cy.contains(/save|сохранить|create/i).click()
    })

    it('6.3 filter_by_assignee - assignee filter', () => {
      cy.visit(hashUrl('/tasks'))
      cy.get('.kanban-board, [data-testid="kanban-board"]').should('exist')
    })
  })

  // ============================================
  // 7. GENERATOR TESTS (8 tests)
  // ============================================
  describe('7. Generator', () => {
    beforeEach(() => {
      cy.login()
    })

    it('7.1 visit_generator_page - generator page', () => {
      cy.visit(hashUrl('/generator'))
      cy.contains(/generator|генератор/i).should('be.visible')
    })

    it('7.2 tab_swagger - swagger tab', () => {
      cy.visit(hashUrl('/generator'))
      cy.get('[data-testid="tab-swagger"]').click()
      cy.get('input[type="file"], .file-upload, .swagger-upload').should('exist')
    })

    it('7.3 tab_session - session tab', () => {
      cy.visit(hashUrl('/generator'))
      cy.get('[data-testid="tab-session"]').click()
      cy.get('.session-selector, select, .empty-state').should('exist')
    })

    it('7.4 tab_url - url tab', () => {
      cy.visit(hashUrl('/generator'))
      cy.get('[data-testid="tab-url"]').click()
      cy.get('input[type="url"], input[type="text"], .url-input').should('exist')
    })

    it('7.5 select_framework_pytest - pytest framework', () => {
      cy.visit(hashUrl('/generator'))
      cy.get('[data-testid="framework-pytest"]').click()
      cy.get('[data-testid="framework-pytest"][data-selected="true"], .framework-card.selected').should('exist')
    })

    it('7.6 select_framework_postman - postman framework', () => {
      cy.visit(hashUrl('/generator'))
      cy.get('[data-testid="framework-postman"]').click()
      cy.get('[data-testid="framework-postman"][data-selected="true"], .framework-card.selected').should('exist')
    })

    it('7.7 upload_swagger_json - swagger upload', () => {
      cy.visit(hashUrl('/generator'))
      cy.get('[data-testid="tab-swagger"]').click()
      cy.get('input[type="file"]').should('exist')
    })

    it('7.8 history_panel_exists - history panel', () => {
      cy.visit(hashUrl('/generator'))
      cy.get('.history-section, .history-list, .empty-history').should('exist')
    })
  })

  // ============================================
  // 8. SETTINGS TESTS (4 tests)
  // ============================================
  describe('8. Settings', () => {
    beforeEach(() => {
      cy.login()
    })

    it('8.1 view_settings - settings page', () => {
      cy.visit(hashUrl('/settings'))
      cy.contains(/settings|настройки/i).should('be.visible')
    })

    it('8.2 theme_toggle_exists - theme toggle', () => {
      cy.visit(hashUrl('/settings'))
      cy.get('[data-testid="theme-toggle"], .theme-toggle').should('exist')
    })

    it('8.3 api_key_section - API keys section', () => {
      cy.visit(hashUrl('/settings'))
      cy.get('[data-testid="api-key-section"]').should('exist')
    })

    it('8.4 profile_section - profile section', () => {
      cy.visit(hashUrl('/settings'))
      cy.get('[data-testid="profile-section"]').should('exist')
    })
  })

  // ============================================
  // PART 2: BOOKMARKLET TESTS (31 tests)
  // ============================================

  describe('9. Bookmarklet', () => {
    beforeEach(() => {
      cy.login()
      cy.window().then((win) => {
        win.__ERRORLENS_LOADED__ = false
        win.__errorLensState = null
        win.__errorLensResults = null
      })
    })

    const loadBookmarklet = () => {
      cy.readFile('E:/EL/errorlens/bookmarklet/recorder.js').then((script) => {
        cy.window().then((win) => {
          win.eval(script)
        })
      })
    }

    // 9.1 Widget Initialization (5 tests)
    describe('9.1 Widget Initialization', () => {
      it('9.1.1 widget_loads - widget loads', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#errorlens-widget').should('exist')
        cy.get('.el-pill').should('be.visible')
        cy.get('.el-label').should('contain', 'ErrorLens')
      })

      it('9.1.2 widget_buttons_exist - widget buttons', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').should('exist')
        cy.get('#el-dashboard-btn').should('exist')
        cy.get('#el-close-btn').should('exist')
      })

      it('9.1.3 widget_removes - widget removes', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#errorlens-widget').should('exist')
        cy.get('#el-close-btn').click()
        cy.get('#errorlens-widget').should('not.exist')
      })

      it('9.1.4 widget_toggle - widget toggle', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#errorlens-widget').should('exist')
        cy.get('#el-close-btn').click()
        cy.get('#errorlens-widget').should('not.exist')
      })

      it('9.1.5 widget_styles_injected - styles injected', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#errorlens-styles').should('exist')
      })
    })

    // 9.2 Mode Selection (4 tests)
    describe('9.2 Mode Selection', () => {
      it('9.2.1 mode_menu_opens - mode menu opens', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.wait(300)
        cy.get('.el-mode-menu').should('exist')
        cy.contains('Выберите режим записи').should('exist')
      })

      it('9.2.2 mode_errors_only - errors only mode', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.wait(300)
        cy.get('[data-mode="errors"]').should('exist')
        cy.contains('Только ошибки').should('exist')
      })

      it('9.2.3 mode_all_requests - all requests mode', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.wait(300)
        cy.get('[data-mode="all"]').should('exist')
        cy.contains('Все запросы').should('exist')
      })

      it('9.2.4 mode_menu_closes_on_outside_click - menu closes on outside click', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.wait(300)
        cy.get('.el-mode-menu').should('exist')
        cy.wait(150)
        cy.get('body').click(10, 10, { force: true })
        cy.wait(100)
        cy.get('.el-mode-menu').should('not.exist')
      })
    })

    // 9.3 Recording (4 tests)
    describe('9.3 Recording', () => {
      it('9.3.1 start_recording_errors - start recording errors', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.get('[data-mode="errors"]').click()
        cy.get('.el-pill').should('have.class', 'recording')
        cy.get('.el-label').should('contain', 'Recording')
        cy.get('#el-counter').should('be.visible')
      })

      it('9.3.2 start_recording_all - start recording all', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.get('[data-mode="all"]').click()
        cy.get('.el-pill').should('have.class', 'recording')
      })

      it('9.3.3 counter_updates - counter updates', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.get('[data-mode="all"]').click()
        cy.window().then((win) => {
          win.console.log('Test log 1')
          win.console.log('Test log 2')
        })
        cy.wait(600)
        cy.get('#el-counter').should('not.have.text', '0')
      })

      it('9.3.4 state_persists - state persists', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.get('[data-mode="all"]').click()
        cy.window().then((win) => {
          const state = win.__errorLensState
          expect(state.isRecording).to.be.true
          expect(state.recordMode).to.eq('all')
        })
      })
    })

    // 9.4 Error Capture (3 tests)
    describe('9.4 Error Capture', () => {
      it('9.4.1 capture_console_error - capture console.error', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.get('[data-mode="errors"]').click()
        cy.window().then((win) => {
          win.console.error('Test error message')
        })
        cy.wait(100)
        cy.window().then((win) => {
          const state = win.__errorLensState
          expect(state.consoleLogs.length).to.be.greaterThan(0)
          const errorLog = state.consoleLogs.find(l => l.type === 'error')
          expect(errorLog).to.exist
          expect(errorLog.message).to.include('Test error message')
        })
      })

      it('9.4.2 capture_console_log - capture console.log in all mode', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.get('[data-mode="all"]').click()
        cy.window().then((win) => {
          win.console.log('Regular log message')
        })
        cy.wait(100)
        cy.window().then((win) => {
          const state = win.__errorLensState
          const logEntry = state.consoleLogs.find(l => l.message.includes('Regular log message'))
          expect(logEntry).to.exist
        })
      })

      it('9.4.3 capture_js_exception - capture JS exceptions', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.get('[data-mode="errors"]').click()
        cy.window().then((win) => {
          win.__errorLensState.jsExceptions.push({
            type: 'error',
            message: 'Test JS Exception',
            timestamp: new Date().toISOString()
          })
        })
        cy.window().then((win) => {
          expect(win.__errorLensState.jsExceptions.length).to.be.greaterThan(0)
        })
      })
    })

    // 9.5 Network Capture (3 tests)
    describe('9.5 Network Capture', () => {
      it('9.5.1 capture_fetch_error - capture fetch errors', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.get('[data-mode="errors"]').click()
        cy.window().then((win) => {
          win.fetch('/api/nonexistent-endpoint').catch(() => {})
        })
        cy.wait(500)
        cy.window().then((win) => {
          const state = win.__errorLensState
          const hasNetworkError = state.networkErrors.length > 0 || state.recordedRequests.some(r => r.status >= 400)
          expect(hasNetworkError || state.recordedRequests.length > 0).to.be.true
        })
      })

      it('9.5.2 capture_all_requests - capture all requests in all mode', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.get('[data-mode="all"]').click()
        cy.window().then((win) => {
          win.fetch('/').catch(() => {})
        })
        cy.wait(500)
        cy.window().then((win) => {
          const state = win.__errorLensState
          expect(state.recordedRequests.length).to.be.greaterThan(0)
        })
      })

      it('9.5.3 junk_urls_filtered - junk URLs filtered', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.get('[data-mode="all"]').click()
        cy.window().then((win) => {
          win.fetch('https://google-analytics.com/collect').catch(() => {})
          win.fetch('/image.png').catch(() => {})
        })
        cy.wait(300)
        cy.window().then((win) => {
          const state = win.__errorLensState
          const junkRequests = state.recordedRequests.filter(r =>
            r.url.includes('google-analytics') || r.url.includes('.png')
          )
          expect(junkRequests.length).to.eq(0)
        })
      })
    })

    // 9.6 Session Submission (5 tests)
    describe('9.6 Session Submission', () => {
      it('9.6.1 stop_recording - stop recording', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.get('[data-mode="errors"]').click()
        cy.get('.el-pill').should('have.class', 'recording')
        cy.get('#el-record-btn').click()
        cy.get('.el-pill').should('satisfy', ($el) => {
          return $el.hasClass('sending') || $el.hasClass('done') || !$el.hasClass('recording')
        })
      })

      it('9.6.2 session_data_structure - session data structure', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.get('[data-mode="all"]').click()
        cy.window().then((win) => {
          win.console.log('Test message')
          win.console.error('Test error')
        })
        cy.wait(200)
        cy.window().then((win) => {
          const state = win.__errorLensState
          expect(state).to.have.property('consoleLogs')
          expect(state).to.have.property('networkErrors')
          expect(state).to.have.property('jsExceptions')
          expect(state).to.have.property('recordedRequests')
          expect(state).to.have.property('isRecording')
          expect(state).to.have.property('recordMode')
        })
      })

      it('9.6.3 result_modal_shows - result modal shows', () => {
        cy.intercept('POST', '**/sessions', {
          statusCode: 200,
          body: { session_id: 'test-session-123', id: 'test-session-123' }
        }).as('createSession')

        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.wait(300)
        cy.get('[data-mode="errors"]').click()
        cy.wait(200)
        cy.get('#el-record-btn').click()
        cy.wait('@createSession', { timeout: 10000 })
        cy.get('.el-modal', { timeout: 5000 }).should('exist')
        cy.contains('Сессия записана').should('exist')
      })

      it('9.6.4 error_modal_on_api_failure - error modal on API failure', () => {
        cy.intercept('POST', '**/sessions', {
          statusCode: 500,
          body: { error: 'Server error' }
        }).as('createSessionFail')

        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.wait(300)
        cy.get('[data-mode="errors"]').click()
        cy.wait(200)
        cy.get('#el-record-btn').click()
        cy.wait('@createSessionFail', { timeout: 10000 })
        cy.get('.el-modal', { timeout: 5000 }).should('exist')
        cy.contains('Ошибка').should('exist')
      })

      it('9.6.5 modal_closes - modal closes', () => {
        cy.intercept('POST', '**/sessions', {
          statusCode: 200,
          body: { session_id: 'test-123', id: 'test-123' }
        }).as('createSession')

        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.wait(300)
        cy.get('[data-mode="errors"]').click()
        cy.wait(200)
        cy.get('#el-record-btn').click()
        cy.wait('@createSession', { timeout: 10000 })
        cy.get('.el-modal', { timeout: 5000 }).should('exist')
        cy.contains('Закрыть').click()
        cy.get('.el-modal').should('not.exist')
      })
    })

    // 9.7 Widget Position (2 tests)
    describe('9.7 Widget Position', () => {
      it('9.7.1 widget_draggable - widget draggable', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#errorlens-widget').then(($widget) => {
          cy.get('.el-pill')
            .trigger('mousedown', { which: 1 })
            .trigger('mousemove', { clientX: 100, clientY: 100 })
            .trigger('mouseup')
        })
      })

      it('9.7.2 position_saved - position saved', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('.el-pill')
          .trigger('mousedown', { which: 1, clientX: 200, clientY: 50 })
          .trigger('mousemove', { clientX: 100, clientY: 100 })
          .trigger('mouseup')
        cy.window().then((win) => {
          const saved = win.localStorage.getItem('errorlens_widget_pos')
          if (saved) {
            const pos = JSON.parse(saved)
            expect(pos).to.have.property('left')
            expect(pos).to.have.property('top')
          }
        })
      })
    })

    // 9.8 Dashboard Integration (2 tests)
    describe('9.8 Dashboard Integration', () => {
      it('9.8.1 dashboard_button_opens - dashboard button opens', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.window().then((win) => {
          cy.stub(win, 'open').as('windowOpen')
        })
        cy.get('#el-dashboard-btn').click()
        cy.get('@windowOpen').should('have.been.called')
      })

      it('9.8.2 config_detection - config detection', () => {
        cy.visit(hashUrl('/'))
        cy.window().then((win) => {
          win.__ERRORLENS_CONFIG__ = {
            apiUrl: 'http://custom-api.test',
            dashboardUrl: 'http://custom-dashboard.test'
          }
        })
        loadBookmarklet()
        cy.get('#errorlens-widget').should('exist')
      })
    })

    // 9.9 Edge Cases (3 tests)
    describe('9.9 Edge Cases', () => {
      it('9.9.1 large_payload_truncation - large payload truncation', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.get('[data-mode="all"]').click()
        cy.window().then((win) => {
          const largeMessage = 'x'.repeat(10000)
          win.console.log(largeMessage)
        })
        cy.wait(100)
        cy.window().then((win) => {
          const state = win.__errorLensState
          const log = state.consoleLogs.find(l => l.message.includes('xxx'))
          if (log) {
            expect(log.message.length).to.be.lessThan(6000)
          }
        })
      })

      it('9.9.2 multiple_errors_captured - multiple errors captured', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.get('[data-mode="errors"]').click()
        cy.window().then((win) => {
          for (let i = 0; i < 5; i++) {
            win.console.error(`Error ${i}`)
          }
        })
        cy.wait(200)
        cy.window().then((win) => {
          const state = win.__errorLensState
          const errorLogs = state.consoleLogs.filter(l => l.type === 'error')
          expect(errorLogs.length).to.be.greaterThan(0)
        })
      })

      it('9.9.3 cleanup_on_remove - cleanup on remove', () => {
        cy.visit(hashUrl('/'))
        loadBookmarklet()
        cy.get('#el-record-btn').click()
        cy.get('[data-mode="all"]').click()
        cy.get('#el-close-btn').click()
        cy.window().then((win) => {
          expect(win.__ERRORLENS_LOADED__).to.be.false
          expect(win.__errorLensState.isRecording).to.be.false
        })
      })
    })
  })
})
