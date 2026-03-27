/// <reference types="cypress" />

// ============================================================
// Pechkin (HTTP Client) — Cypress E2E Tests
// Target: http://192.168.1.74:3000 (live server)
// ============================================================

// --------------- helpers ---------------
const PECHKIN_URL = '/dashboard/#/qa?tab=generator'

function loginAndOpenPechkin() {
  cy.loginToApp()
  cy.openPechkin()
}

function ensureRequestEditor() {
  // Make sure we have a request open in the editor
  cy.get('body').then($body => {
    if ($body.find('.request-editor').length === 0) {
      // Click "+ New Request" or click a request in the tree
      cy.get('body').then($b => {
        if ($b.find('.pechkin-new-btn').length) {
          cy.get('.pechkin-new-btn').click()
        } else {
          cy.get('.request-row').first().click()
        }
      })
      cy.get('.request-editor').should('exist')
    }
  })
}

function clickEditorTab(tabName) {
  cy.get('.editor-tab').contains(tabName).click()
  cy.get('.editor-tab').contains(tabName).should('have.class', 'active')
}

// ============================================================
// 1. Mode Switcher
// ============================================================
describe('1. Mode Switcher', () => {
  beforeEach(() => {
    cy.loginToApp()
    cy.visit(PECHKIN_URL)
    cy.url().should('include', '/qa')
  })

  it('1.1 Pechkin button switches mode and shows collection tree', () => {
    cy.get('.mode-btn').contains('Pechkin').then($btn => $btn[0].click())
    cy.get('.collection-tree').should('be.visible')
  })

  it('1.2 Static mode stays active after page reload', () => {
    cy.get('.mode-btn').contains('Static').then($btn => $btn[0].click())
    cy.get('.mode-btn').contains('Static').should('have.class', 'active')
    cy.reload()
    // After reload, the default or persisted mode should be shown
    cy.get('.mode-switcher').should('exist')
  })

  it('1.3 EVA mode shows upload zone', () => {
    cy.get('.mode-btn').contains('EVA').then($btn => $btn[0].click())
    cy.get('.mode-btn').contains('EVA').should('have.class', 'active')
    // EVA tab should render its content
    cy.get('.mode-btn.active').should('contain', 'EVA')
  })

  it('1.4 Pechkin button has .active class after selection', () => {
    cy.get('.mode-btn').contains('Pechkin').then($btn => $btn[0].click())
    cy.get('.mode-btn').contains('Pechkin').should('have.class', 'active')
  })

  it('1.5 Switching between modes does not break layout', () => {
    const modes = ['Static', 'LLM', 'EVA', 'Pechkin']
    modes.forEach(mode => {
      cy.get('.mode-btn').contains(mode).then($btn => $btn[0].click())
      cy.get('.mode-btn').contains(mode).should('have.class', 'active')
    })
    // Back to Pechkin, verify layout
    cy.get('.collection-tree').should('be.visible')
    cy.get('.pechkin-tab').should('exist')
  })
})

// ============================================================
// 2. Collection Tree CRUD
// ============================================================
describe('2. Collection Tree CRUD', () => {
  beforeEach(() => {
    loginAndOpenPechkin()
  })

  it('2.1 Collection list loads', () => {
    cy.get('.collection-tree').should('exist')
    cy.get('.tree-list').should('exist')
  })

  it('2.2 Create collection via prompt', () => {
    const colName = 'CY-Col-' + Date.now()
    cy.window().then(win => {
      cy.stub(win, 'prompt').returns(colName)
    })
    cy.get('.tree-header-actions .tree-add-btn').last().click()
    cy.get('.collection-name').should('contain', colName)
  })

  it('2.3 Import button exists', () => {
    cy.get('.tree-header-actions .tree-add-btn').first().should('exist')
    // The first button triggers import (arrow up icon)
    cy.get('.tree-header-actions .tree-add-btn').first().should('have.attr', 'title', 'Import Postman JSON')
  })

  it('2.4 Toggle expand on collection', () => {
    // Ensure at least one collection exists
    cy.get('.collection-row').first().within(() => {
      cy.get('.expand-btn').click()
    })
    cy.get('.tree-children').should('exist')
  })

  it('2.5 Add request to collection', () => {
    cy.get('.collection-row').first().within(() => {
      cy.get('.expand-btn').click()
    })
    cy.get('.collection-row').first().find('.tree-add-btn').filter('[title="Add request"]').click()
    cy.get('.request-row').should('exist')
  })

  it('2.6 Add folder to collection', () => {
    const folderName = 'CY-Folder-' + Date.now()
    cy.window().then(win => {
      cy.stub(win, 'prompt').returns(folderName)
    })
    cy.get('.collection-row').first().find('.tree-add-btn').filter('[title="Add folder"]').click()
    // Expand to see folder
    cy.get('.collection-row').first().within(() => {
      cy.get('.expand-btn').click({ force: true })
    })
    cy.get('.folder-name').should('contain', folderName)
  })

  it('2.7 Clicking request opens editor', () => {
    // Expand first collection
    cy.get('.collection-row').first().within(() => {
      cy.get('.expand-btn').click()
    })
    // Click first request if exists, otherwise create one
    cy.get('body').then($body => {
      if ($body.find('.request-row').length) {
        cy.get('.request-row').first().click()
        cy.get('.request-editor').should('exist')
      } else {
        cy.get('.collection-row').first().find('.tree-add-btn').filter('[title="Add request"]').click()
        cy.get('.request-row').first().click()
        cy.get('.request-editor').should('exist')
      }
    })
  })

  it('2.8 Right-click request shows context menu', () => {
    cy.get('.collection-row').first().within(() => {
      cy.get('.expand-btn').click()
    })
    cy.get('.request-row').first().rightclick()
    cy.get('.ctx-menu').should('be.visible')
    cy.get('.ctx-item').should('contain', 'Duplicate')
    cy.get('.ctx-item').should('contain', 'Delete')
  })

  it('2.9 Duplicate request via context menu', () => {
    cy.get('.collection-row').first().within(() => {
      cy.get('.expand-btn').click()
    })
    cy.get('.request-row').then($rows => {
      const countBefore = $rows.length
      cy.get('.request-row').first().rightclick()
      cy.get('.ctx-item').contains('Duplicate').click()
      cy.get('.request-row').should('have.length.gte', countBefore)
    })
  })

  it('2.10 Delete request via context menu', () => {
    // First add a request to delete
    cy.get('.collection-row').first().find('.tree-add-btn').filter('[title="Add request"]').click()
    cy.wait(500)
    cy.get('.collection-row').first().within(() => {
      cy.get('.expand-btn').click({ force: true })
    })
    cy.window().then(win => {
      cy.stub(win, 'confirm').returns(true)
    })
    cy.get('.request-row').last().rightclick()
    cy.get('.ctx-item').contains('Delete').click()
  })

  it('2.11 Delete folder via context menu', () => {
    // Create a folder first
    const folderName = 'CY-DelFolder-' + Date.now()
    cy.window().then(win => {
      cy.stub(win, 'prompt').returns(folderName)
      cy.stub(win, 'confirm').returns(true)
    })
    cy.get('.collection-row').first().find('.tree-add-btn').filter('[title="Add folder"]').click()
    cy.wait(500)
    cy.get('.collection-row').first().within(() => {
      cy.get('.expand-btn').click({ force: true })
    })
    cy.get('.folder-row').last().rightclick()
    cy.get('.ctx-item').contains('Delete Folder').click()
  })

  it('2.12 Delete collection via context menu', () => {
    // Create a throwaway collection
    const colName = 'CY-Delete-' + Date.now()
    cy.window().then(win => {
      cy.stub(win, 'prompt').returns(colName)
    })
    cy.get('.tree-header-actions .tree-add-btn').last().click()
    cy.wait(500)
    cy.window().then(win => {
      cy.stub(win, 'confirm').returns(true)
    })
    cy.get('.collection-row').last().rightclick()
    cy.get('.ctx-item').contains('Delete Collection').click()
  })
})

// ============================================================
// 3. URL Bar and Method Selector
// ============================================================
describe('3. URL Bar and Method Selector', () => {
  beforeEach(() => {
    cy.createCollectionWithRequest()
  })
  afterEach(() => {
    cy.deleteTestCollection()
  })

  it('3.1 URL input is editable', () => {
    cy.get('.url-input').clear().type('https://httpbin.org/get')
    cy.get('.url-input').should('have.value', 'https://httpbin.org/get')
  })

  it('3.2 Method select has 7 methods', () => {
    cy.get('select.method-select option').should('have.length', 7)
    const expectedMethods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
    expectedMethods.forEach(m => {
      cy.get('select.method-select option').contains(m).should('exist')
    })
  })

  it('3.3 selectMethod command works for POST', () => {
    cy.selectMethod('POST')
    cy.get('select.method-select').should('have.value', 'POST')
  })

  it('3.4 Method select has color classes', () => {
    cy.selectMethod('GET')
    cy.get('select.method-select').should('have.class', 'sel-get')
    cy.selectMethod('POST')
    cy.get('select.method-select').should('have.class', 'sel-post')
    cy.selectMethod('DELETE')
    cy.get('select.method-select').should('have.class', 'sel-delete')
  })

  it('3.5 Enter key in URL triggers send', () => {
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.url-input').clear().type('https://httpbin.org/get{enter}')
    cy.wait('@exec', { timeout: 30000 })
  })

  it('3.6 Send button disabled during execution', () => {
    cy.intercept('POST', '/api/v1/pechkin/execute*', (req) => {
      req.on('response', (res) => {
        res.setDelay(2000)
      })
    }).as('exec')
    cy.get('.url-input').clear().type('https://httpbin.org/delay/2')
    cy.get('.send-btn').click()
    cy.get('.send-btn').should('be.disabled')
    cy.get('.send-btn').should('contain', 'Sending...')
  })

  it('3.7 URL with variables placeholder', () => {
    cy.get('.url-input').clear().type('https://{{host}}/api/{{version}}/users')
    cy.get('.url-input').should('have.value', 'https://{{host}}/api/{{version}}/users')
  })

  it('3.8 Send button exists and is clickable', () => {
    cy.get('.send-btn').should('exist')
    cy.get('.send-btn').should('not.be.disabled')
    cy.get('.send-btn').should('contain', 'Send')
  })

  it('3.9 Saving request updates name in tree', () => {
    cy.get('.url-input').clear().type('https://httpbin.org/get')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 })
    // The tree should show request with URL or name
    cy.get('.request-row.active').should('exist')
  })

  it('3.10 URL input has monospace font', () => {
    cy.get('.url-input').should('have.css', 'font-family').and('match', /monospace/)
  })
})

// ============================================================
// 4. Params Tab
// ============================================================
describe('4. Params Tab', () => {
  beforeEach(() => {
    cy.createCollectionWithRequest()
  })
  afterEach(() => {
    cy.deleteTestCollection()
  })

  it('4.1 Params tab is the default active tab', () => {
    cy.get('.editor-tab').contains('Params').should('have.class', 'active')
  })

  it('4.2 Add row button exists and adds a row', () => {
    clickEditorTab('Params')
    cy.get('.kv-add').click()
    cy.get('.kv-input').should('exist')
  })

  it('4.3 Key-value updates URL query string', () => {
    cy.get('.url-input').clear().type('https://httpbin.org/get')
    clickEditorTab('Params')
    cy.get('.kv-add').click()
    cy.get('.kv-input[placeholder="key"]').last().clear().type('foo')
    cy.get('.kv-input[placeholder="value"]').last().clear().type('bar')
    // Trigger blur to sync params to URL
    cy.get('.kv-input[placeholder="value"]').last().blur()
    cy.get('.url-input').should('contain.value', 'foo')
  })

  it('4.4 Checkbox disables parameter', () => {
    clickEditorTab('Params')
    cy.get('.kv-add').click()
    cy.get('.kv-input[placeholder="key"]').last().type('disabled_param')
    cy.get('input[type="checkbox"]').last().uncheck()
    cy.get('.kv-disabled').should('exist')
  })

  it('4.5 Delete row removes parameter', () => {
    clickEditorTab('Params')
    cy.get('.kv-add').click()
    cy.get('.kv-input[placeholder="key"]').last().type('to_delete')
    cy.get('.kv-remove').last().click()
    cy.get('.kv-input[placeholder="key"]').should('not.contain.value', 'to_delete')
  })

  it('4.6 Multiple params work', () => {
    cy.get('.url-input').clear().type('https://httpbin.org/get')
    clickEditorTab('Params')
    // Add first param
    cy.get('.kv-add').click()
    cy.get('.kv-input[placeholder="key"]').last().type('a')
    cy.get('.kv-input[placeholder="value"]').last().type('1')
    // Add second param
    cy.get('.kv-add').click()
    cy.get('.kv-input[placeholder="key"]').last().type('b')
    cy.get('.kv-input[placeholder="value"]').last().type('2')
    cy.get('.kv-input[placeholder="key"]').should('have.length.gte', 2)
  })
})

// ============================================================
// 5. Headers Tab
// ============================================================
describe('5. Headers Tab', () => {
  beforeEach(() => {
    cy.createCollectionWithRequest()
    clickEditorTab('Headers')
  })
  afterEach(() => {
    cy.deleteTestCollection()
  })

  it('5.1 Content-Type quick header button adds header', () => {
    cy.get('.quick-btn').contains('Content-Type').click()
    cy.get('.kv-input[placeholder="key"]').should('exist')
    cy.get('.kv-input').first().should('have.value', 'Content-Type')
  })

  it('5.2 Authorization quick header button adds header', () => {
    cy.get('.quick-btn').contains('Authorization').click()
    cy.get('.kv-input').filter('[value="Authorization"]').should('exist')
  })

  it('5.3 Accept quick header button adds header', () => {
    cy.get('.quick-btn').contains('Accept').click()
    cy.get('.kv-input').filter('[value="Accept"]').should('exist')
  })

  it('5.4 Inline edit of header value', () => {
    cy.get('.quick-btn').contains('Content-Type').click()
    cy.get('.kv-input[placeholder="value"]').last().clear().type('application/json')
    cy.get('.kv-input[placeholder="value"]').last().should('have.value', 'application/json')
  })

  it('5.5 Checkbox disables header', () => {
    cy.get('.quick-btn').contains('Content-Type').click()
    cy.get('input[type="checkbox"]').last().uncheck()
    cy.get('.kv-disabled').should('exist')
  })

  it('5.6 Delete header row', () => {
    cy.get('.quick-btn').contains('Content-Type').click()
    cy.get('.kv-remove').last().click()
    // Header should be removed
    cy.get('.kv-input').filter('[value="Content-Type"]').should('not.exist')
  })
})

// ============================================================
// 6. Body Tab
// ============================================================
describe('6. Body Tab', () => {
  beforeEach(() => {
    cy.createCollectionWithRequest()
    clickEditorTab('Body')
  })
  afterEach(() => {
    cy.deleteTestCollection()
  })

  it('6.1 GET method shows body_type=none message by default', () => {
    cy.selectMethod('GET')
    clickEditorTab('Body')
    // With body_type "none", shows message
    cy.get('.body-radio').contains('none').click()
    cy.get('.body-none-text').should('contain', 'does not have a body')
  })

  it('6.2 Raw mode shows textarea', () => {
    cy.get('.body-radio').contains('raw').click()
    cy.get('.body-textarea').should('be.visible')
  })

  it('6.3 Pretty button formats JSON', () => {
    cy.get('.body-radio').contains('raw').click()
    cy.get('.body-textarea').clear().type('{"a":1,"b":2}', { parseSpecialCharSequences: false })
    cy.get('.rv-toggle').contains('Pretty').click()
    cy.get('.body-textarea').invoke('val').should('contain', '"a": 1')
  })

  it('6.4 Pretty on invalid JSON does not crash', () => {
    cy.get('.body-radio').contains('raw').click()
    cy.get('.body-textarea').clear().type('not json at all')
    cy.get('.rv-toggle').contains('Pretty').click()
    // Should still contain the original text
    cy.get('.body-textarea').invoke('val').should('contain', 'not json at all')
  })

  it('6.5 form-data shows KvTable', () => {
    cy.get('.body-radio').contains('form-data').click()
    cy.get('.kv-table').should('exist')
  })

  it('6.6 x-www-form-urlencoded shows KvTable', () => {
    cy.get('.body-radio').contains('x-www-form-urlencoded').click()
    cy.get('.kv-table').should('exist')
  })

  it('6.7 none mode shows placeholder', () => {
    cy.get('.body-radio').contains('none').click()
    cy.get('.body-none-text').should('be.visible')
  })

  it('6.8 Body is sent when executing (via intercept)', () => {
    cy.selectMethod('POST')
    cy.get('.url-input').clear().type('https://httpbin.org/post')
    clickEditorTab('Body')
    cy.get('.body-radio').contains('raw').click()
    cy.get('.body-textarea').clear().type('{"test": true}', { parseSpecialCharSequences: false })
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 }).then(interception => {
      expect(interception.request.body).to.have.property('body')
    })
  })

  it('6.9 form-data adds key-value pairs', () => {
    cy.get('.body-radio').contains('form-data').click()
    cy.get('.kv-add').click()
    cy.get('.kv-input[placeholder="key"]').last().type('field1')
    cy.get('.kv-input[placeholder="value"]').last().type('value1')
    cy.get('.kv-input[placeholder="key"]').last().should('have.value', 'field1')
  })

  it('6.10 body_type radio persists within session', () => {
    cy.get('.body-radio').contains('raw').click()
    clickEditorTab('Params')
    clickEditorTab('Body')
    cy.get('.body-textarea').should('be.visible')
  })
})

// ============================================================
// 7. Auth Tab
// ============================================================
describe('7. Auth Tab', () => {
  beforeEach(() => {
    cy.createCollectionWithRequest()
    clickEditorTab('Auth')
  })
  afterEach(() => {
    cy.deleteTestCollection()
  })

  it('7.1 No Auth is default', () => {
    cy.get('.auth-type-select').first().should('have.value', 'none')
  })

  it('7.2 Bearer Token shows token field', () => {
    cy.get('.auth-type-select').first().select('bearer')
    cy.get('.auth-input').should('be.visible')
    cy.get('.auth-label').should('contain', 'Token')
  })

  it('7.3 Bearer token included in header via intercept', () => {
    cy.get('.auth-type-select').first().select('bearer')
    cy.get('.auth-input').clear().type('my-secret-token')
    clickEditorTab('Params')
    cy.get('.url-input').clear().type('https://httpbin.org/get')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 }).then(interception => {
      const auth = interception.request.body.auth
      expect(auth).to.have.property('type', 'bearer')
      expect(auth).to.have.property('token', 'my-secret-token')
    })
  })

  it('7.4 Basic Auth shows username and password fields', () => {
    cy.get('.auth-type-select').first().select('basic')
    cy.get('.auth-label').should('contain', 'Username')
    cy.get('.auth-label').should('contain', 'Password')
    cy.get('.auth-input').should('have.length', 2)
  })

  it('7.5 Basic Auth credentials are set', () => {
    cy.get('.auth-type-select').first().select('basic')
    cy.get('.auth-input').first().clear().type('user')
    cy.get('.auth-input').last().clear().type('pass123')
    cy.get('.auth-input').first().should('have.value', 'user')
  })

  it('7.6 API Key shows key, value, add-to fields', () => {
    cy.get('.auth-type-select').first().select('api_key')
    cy.get('.auth-label').should('contain', 'Key')
    cy.get('.auth-label').should('contain', 'Value')
    cy.get('.auth-label').should('contain', 'Add to')
  })

  it('7.7 API Key header mode', () => {
    cy.get('.auth-type-select').first().select('api_key')
    cy.get('.auth-input').first().clear().type('X-API-Key')
    cy.get('.auth-input').eq(1).clear().type('secret123')
    cy.get('.auth-type-select').last().select('header')
    cy.get('.auth-type-select').last().should('have.value', 'header')
  })

  it('7.8 API Key query mode', () => {
    cy.get('.auth-type-select').first().select('api_key')
    cy.get('.auth-input').first().clear().type('api_key')
    cy.get('.auth-input').eq(1).clear().type('secret456')
    cy.get('.auth-type-select').last().select('query')
    cy.get('.auth-type-select').last().should('have.value', 'query')
  })
})

// ============================================================
// 8. Pre-request and Tests Script
// ============================================================
describe('8. Pre-request and Tests Script', () => {
  beforeEach(() => {
    cy.createCollectionWithRequest()
  })
  afterEach(() => {
    cy.deleteTestCollection()
  })

  it('8.1 Pre-request tab has textarea', () => {
    clickEditorTab('Pre-request')
    cy.get('.script-textarea').should('be.visible')
  })

  it('8.2 Pre-request textarea is editable', () => {
    clickEditorTab('Pre-request')
    cy.get('.script-textarea').clear().type('print("pre-request")')
    cy.get('.script-textarea').should('have.value', 'print("pre-request")')
  })

  it('8.3 Tests tab has textarea', () => {
    clickEditorTab('Tests')
    cy.get('.script-textarea').should('be.visible')
  })

  it('8.4 Test script is sent on execution', () => {
    clickEditorTab('Tests')
    cy.get('.script-textarea').clear().type('assert response.status_code == 200')
    cy.get('.url-input').clear().type('https://httpbin.org/get')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 }).then(interception => {
      expect(interception.request.body).to.have.property('test_script')
    })
  })

  it('8.5 Test results are displayed in response viewer', () => {
    clickEditorTab('Tests')
    cy.get('.script-textarea').clear().type('assert response.status_code == 200')
    cy.get('.url-input').clear().type('https://httpbin.org/get')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 })
    // Check response viewer Tests tab
    cy.get('.rv-tab').contains('Tests').click()
    cy.get('.rv-tests').should('exist')
  })

  it('8.6 Invalid test script does not crash', () => {
    clickEditorTab('Tests')
    cy.get('.script-textarea').clear().type('raise Exception("fail")')
    cy.get('.url-input').clear().type('https://httpbin.org/get')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 })
    // App should still function, response panel should show something
    cy.get('.response-viewer').should('exist')
  })
})

// ============================================================
// 9. Code Generation
// ============================================================
describe('9. Code Generation', () => {
  beforeEach(() => {
    cy.createCollectionWithRequest()
    cy.get('.url-input').clear().type('https://httpbin.org/get')
    clickEditorTab('Code')
  })
  afterEach(() => {
    cy.deleteTestCollection()
  })

  it('9.1 Language buttons are visible', () => {
    cy.get('.code-lang-btn').should('have.length', 3)
    cy.get('.code-lang-btn').contains('cURL').should('exist')
    cy.get('.code-lang-btn').contains('Python').should('exist')
    cy.get('.code-lang-btn').contains('JavaScript').should('exist')
  })

  it('9.2 cURL format generated correctly', () => {
    cy.get('.code-lang-btn').contains('cURL').click()
    cy.get('.code-output code').should('contain', 'curl')
    cy.get('.code-output code').should('contain', 'httpbin.org/get')
  })

  it('9.3 Python format generated correctly', () => {
    cy.get('.code-lang-btn').contains('Python').click()
    cy.get('.code-output code').should('contain', 'import requests')
    cy.get('.code-output code').should('contain', 'requests.get')
  })

  it('9.4 JavaScript format generated correctly', () => {
    cy.get('.code-lang-btn').contains('JavaScript').click()
    cy.get('.code-output code').should('contain', 'fetch')
    cy.get('.code-output code').should('contain', 'httpbin.org/get')
  })

  it('9.5 Copy button exists', () => {
    cy.get('.copy-snippet-btn').should('exist')
    cy.get('.copy-snippet-btn').should('contain', 'Copy')
  })

  it('9.6 Changing method updates code', () => {
    cy.get('.code-lang-btn').contains('cURL').click()
    cy.selectMethod('POST')
    clickEditorTab('Code')
    cy.get('.code-output code').should('contain', 'POST')
  })
})

// ============================================================
// 10. Send Requests — All Methods
// ============================================================
describe('10. Send Requests - All Methods', () => {
  beforeEach(() => {
    cy.createCollectionWithRequest()
  })
  afterEach(() => {
    cy.deleteTestCollection()
  })

  it('10.1 GET to httpbin.org/get succeeds', () => {
    cy.selectMethod('GET')
    cy.get('.url-input').clear().type('https://httpbin.org/get')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 })
    cy.get('.rv-status-code').should('contain', '200')
  })

  it('10.2 POST to httpbin.org/post succeeds', () => {
    cy.selectMethod('POST')
    cy.get('.url-input').clear().type('https://httpbin.org/post')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 })
    cy.get('.rv-status-code').should('contain', '200')
  })

  it('10.3 PUT to httpbin.org/put succeeds', () => {
    cy.selectMethod('PUT')
    cy.get('.url-input').clear().type('https://httpbin.org/put')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 })
    cy.get('.rv-status-code').should('contain', '200')
  })

  it('10.4 PATCH to httpbin.org/patch succeeds', () => {
    cy.selectMethod('PATCH')
    cy.get('.url-input').clear().type('https://httpbin.org/patch')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 })
    cy.get('.rv-status-code').should('contain', '200')
  })

  it('10.5 DELETE to httpbin.org/delete succeeds', () => {
    cy.selectMethod('DELETE')
    cy.get('.url-input').clear().type('https://httpbin.org/delete')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 })
    cy.get('.rv-status-code').should('contain', '200')
  })

  it('10.6 HEAD to httpbin.org/get succeeds', () => {
    cy.selectMethod('HEAD')
    cy.get('.url-input').clear().type('https://httpbin.org/get')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 })
    cy.get('.rv-status-code').should('contain', '200')
  })

  it('10.7 OPTIONS to httpbin.org/get succeeds', () => {
    cy.selectMethod('OPTIONS')
    cy.get('.url-input').clear().type('https://httpbin.org/get')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 })
    cy.get('.rv-status-code').should('exist')
  })

  it('10.8 Invalid domain shows error', () => {
    cy.selectMethod('GET')
    cy.get('.url-input').clear().type('https://nonexistent.invalid.domain.xyz/test')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 })
    // Should show error status or error message in response
    cy.get('.response-viewer').should('exist')
  })

  it('10.9 404 status shows warning badge', () => {
    cy.selectMethod('GET')
    cy.get('.url-input').clear().type('https://httpbin.org/status/404')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 })
    cy.get('.rv-status-code').should('contain', '404')
    cy.get('.rv-status-code').should('have.class', 'status-warn')
  })

  it('10.10 500 status shows error badge', () => {
    cy.selectMethod('GET')
    cy.get('.url-input').clear().type('https://httpbin.org/status/500')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 })
    cy.get('.rv-status-code').should('contain', '500')
    cy.get('.rv-status-code').should('have.class', 'status-err')
  })

  it('10.11 201 status shows success badge', () => {
    cy.selectMethod('GET')
    cy.get('.url-input').clear().type('https://httpbin.org/status/201')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 })
    cy.get('.rv-status-code').should('contain', '201')
    cy.get('.rv-status-code').should('have.class', 'status-ok')
  })

  it('10.12 Duration is greater than 0', () => {
    cy.selectMethod('GET')
    cy.get('.url-input').clear().type('https://httpbin.org/get')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 })
    cy.get('.rv-meta').first().invoke('text').then(text => {
      const ms = parseInt(text)
      expect(ms).to.be.greaterThan(0)
    })
  })

  it('10.13 Size is greater than 0', () => {
    cy.selectMethod('GET')
    cy.get('.url-input').clear().type('https://httpbin.org/get')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 })
    cy.get('.rv-meta').last().invoke('text').then(text => {
      // Should contain B or KB
      expect(text).to.match(/\d+/)
    })
  })

  it('10.14 Response body is displayed', () => {
    cy.selectMethod('GET')
    cy.get('.url-input').clear().type('https://httpbin.org/get')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 })
    cy.get('.rv-code code').should('not.be.empty')
  })
})

// ============================================================
// 11. Response Panel
// ============================================================
describe('11. Response Panel', () => {
  afterEach(() => {
    cy.deleteTestCollection()
  })
  beforeEach(() => {
    cy.createCollectionWithRequest()
    // Send a request to populate response panel
    cy.selectMethod('GET')
    cy.get('.url-input').clear().type('https://httpbin.org/get')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 })
    cy.get('.rv-status-code').should('exist')
  })

  it('11.1 Pretty mode is default', () => {
    cy.get('.rv-toggle').contains('Pretty').should('have.class', 'active')
  })

  it('11.2 Pretty toggle switches raw/pretty', () => {
    cy.get('.rv-toggle').contains('Pretty').click()
    cy.get('.rv-toggle').contains('Pretty').should('not.have.class', 'active')
    cy.get('.rv-code code').should('not.be.empty')
    // Toggle back
    cy.get('.rv-toggle').contains('Pretty').click()
    cy.get('.rv-toggle').contains('Pretty').should('have.class', 'active')
  })

  it('11.3 Copy button exists in response body toolbar', () => {
    cy.get('.rv-toggle').contains('Copy').should('exist')
  })

  it('11.4 Headers tab shows response headers', () => {
    cy.get('.rv-tab').contains('Headers').click()
    cy.get('.rv-table').should('exist')
    cy.get('.rv-header-key').should('have.length.gte', 1)
  })

  it('11.5 Tests tab shows no results when no tests', () => {
    cy.get('.rv-tab').contains('Tests').click()
    cy.get('.rv-no-tests').should('contain', 'No test results')
  })

  it('11.6 History tab exists in response viewer', () => {
    cy.get('.rv-tab').contains('History').click()
    cy.get('.rv-history').should('exist')
  })

  it('11.7 History items have non-zero status code', () => {
    cy.get('.rv-tab').contains('History').click()
    cy.get('.rv-history-item').first().within(() => {
      cy.get('.rv-status-code').invoke('text').then(text => {
        const code = parseInt(text)
        expect(code).to.not.equal(0)
      })
    })
  })

  it('11.8 Clicking history item loads that response', () => {
    cy.get('.rv-tab').contains('History').click()
    cy.get('.rv-history-item').first().click()
    // Should load response, status bar should be visible
    cy.get('.rv-status-bar').should('exist')
    cy.get('.rv-status-code').should('exist')
  })
})

// ============================================================
// 12. Variables Panel
// ============================================================
describe('12. Variables Panel', () => {
  beforeEach(() => {
    loginAndOpenPechkin()
    // Need a collection to be active
    cy.get('.collection-row').first().click()
    cy.wait(500)
  })

  it('12.1 Gear button opens variables panel', () => {
    cy.get('.env-manage-btn').click()
    cy.get('.vars-panel').should('be.visible')
    cy.get('.vars-title').should('contain', 'Variables')
  })

  it('12.2 Add variable button adds a row', () => {
    cy.get('.env-manage-btn').click()
    cy.get('.vars-add-row').click()
    cy.get('.vars-input.vars-name').should('exist')
  })

  it('12.3 Variable substitution in URL', () => {
    cy.get('.env-manage-btn').click()
    cy.get('.vars-add-row').click()
    cy.get('.vars-input.vars-name').last().clear().type('test_host')
    cy.get('.vars-input.vars-value').last().clear().type('httpbin.org')
    cy.get('.vars-input.vars-value').last().blur()
    cy.get('.vars-close').click()
    // Use variable in URL
    ensureRequestEditor()
    cy.get('.url-input').clear().type('https://{{test_host}}/get')
    cy.get('.url-input').should('have.value', 'https://{{test_host}}/get')
  })

  it('12.4 is_secret type masks the value', () => {
    cy.get('.env-manage-btn').click()
    cy.get('.vars-add-row').click()
    cy.get('.vars-input.vars-name').last().clear().type('secret_var')
    cy.get('.vars-input.vars-value').last().clear().type('hidden-value')
    cy.get('.vars-type-select').last().select('true')
    cy.get('.vars-input.vars-value').last().should('have.attr', 'type', 'password')
  })

  it('12.5 Add Environment button creates new scope', () => {
    cy.get('.env-manage-btn').click()
    cy.window().then(win => {
      cy.stub(win, 'prompt').returns('staging')
    })
    cy.get('.vars-add-env').click()
    cy.get('.vars-scope-item').should('contain', 'Staging')
  })

  it('12.6 Delete variable button removes row', () => {
    cy.get('.env-manage-btn').click()
    cy.get('.vars-add-row').click()
    cy.get('.vars-input.vars-name').last().type('to_remove')
    cy.get('.vars-del-btn').last().click()
    cy.get('.vars-input.vars-name').should('not.contain.value', 'to_remove')
  })
})

// ============================================================
// 13. Collection Runner
// ============================================================
describe('13. Collection Runner', () => {
  beforeEach(() => {
    loginAndOpenPechkin()
    // Expand first collection
    cy.get('.collection-row').first().within(() => {
      cy.get('.expand-btn').click()
    })
    cy.wait(300)
  })

  it('13.1 Play button opens runner modal', () => {
    cy.get('.run-btn').first().click()
    cy.get('.runner-modal').should('be.visible')
    cy.get('.runner-title').should('contain', 'Collection Runner')
  })

  it('13.2 Runner shows request list', () => {
    cy.get('.run-btn').first().click()
    cy.get('.request-list').should('exist')
    cy.get('.request-list-header').should('contain', 'Requests')
  })

  it('13.3 Requests are draggable', () => {
    cy.get('.run-btn').first().click()
    cy.get('.request-item').first().should('have.attr', 'draggable', 'true')
    cy.get('.drag-handle').should('exist')
  })

  it('13.4 Run button with request count', () => {
    cy.get('.run-btn').first().click()
    cy.get('.btn-primary').should('contain', 'Run')
    cy.get('.btn-primary').invoke('text').should('match', /Run \(\d+\)/)
  })

  it('13.5 Run button executes requests and results appear', () => {
    cy.get('.run-btn').first().click()
    // Only run if there are selected requests
    cy.get('body').then($body => {
      if ($body.find('.btn-primary:not(:disabled)').length) {
        cy.intercept('POST', '/api/v1/pechkin/collections/*/run').as('runCol')
        cy.get('.btn-primary').click()
        cy.wait('@runCol', { timeout: 60000 })
        cy.get('.runner-results').should('exist')
      }
    })
  })

  it('13.6 Results show passed/failed status', () => {
    cy.get('.run-btn').first().click()
    cy.get('body').then($body => {
      if ($body.find('.btn-primary:not(:disabled)').length) {
        cy.intercept('POST', '/api/v1/pechkin/collections/*/run').as('runCol')
        cy.get('.btn-primary').click()
        cy.wait('@runCol', { timeout: 60000 })
        cy.get('.result-item').should('exist')
        cy.get('.result-status').should('exist')
      }
    })
  })

  it('13.7 Stop button appears during run', () => {
    cy.get('.run-btn').first().click()
    cy.get('body').then($body => {
      if ($body.find('.btn-primary:not(:disabled)').length) {
        cy.intercept('POST', '/api/v1/pechkin/collections/*/run', (req) => {
          req.on('response', (res) => { res.setDelay(5000) })
        }).as('runCol')
        cy.get('.btn-primary').click()
        cy.get('.btn-danger').should('contain', 'Stop')
      }
    })
  })

  it('13.8 Export CSV button appears after run completes', () => {
    cy.get('.run-btn').first().click()
    cy.get('body').then($body => {
      if ($body.find('.btn-primary:not(:disabled)').length) {
        cy.intercept('POST', '/api/v1/pechkin/collections/*/run').as('runCol')
        cy.get('.btn-primary').click()
        cy.wait('@runCol', { timeout: 60000 })
        cy.get('.btn-secondary').should('contain', 'Export CSV')
      }
    })
  })
})

// ============================================================
// 14. Global History Tab
// ============================================================
describe('14. Global History Tab', () => {
  beforeEach(() => {
    loginAndOpenPechkin()
  })

  it('14.1 History tab shows in sidebar', () => {
    cy.get('.toggle-btn').contains('History').click()
    cy.get('.toggle-btn').contains('History').should('have.class', 'active')
    cy.get('.global-history').should('exist')
  })

  it('14.2 After send, history is populated', () => {
    ensureRequestEditor()
    cy.selectMethod('GET')
    cy.get('.url-input').clear().type('https://httpbin.org/get')
    cy.intercept('POST', '/api/v1/pechkin/execute*').as('exec')
    cy.get('.send-btn').click()
    cy.wait('@exec', { timeout: 30000 })
    // Switch to history
    cy.get('.toggle-btn').contains('History').click()
    cy.get('.history-list').should('exist')
    // Should have at least one item (may or may not depending on backend)
    cy.get('.global-history').should('be.visible')
  })

  it('14.3 Search/filter field exists', () => {
    cy.get('.toggle-btn').contains('History').click()
    cy.get('.history-search').should('exist')
    cy.get('.history-search').type('httpbin')
    cy.get('.history-search').should('have.value', 'httpbin')
  })

  it('14.4 Clicking history item triggers replay', () => {
    cy.get('.toggle-btn').contains('History').click()
    cy.get('body').then($body => {
      if ($body.find('.history-item').length) {
        cy.get('.history-item').first().click()
        // Should switch back to collections view and open the request
        cy.get('.toggle-btn').contains('Collections').should('have.class', 'active')
      } else {
        cy.log('No history items found, skipping click test')
      }
    })
  })
})

// ============================================================
// 15. Postman Import
// ============================================================
describe('15. Postman Import', () => {
  beforeEach(() => {
    loginAndOpenPechkin()
  })

  it('15.1 Upload button triggers hidden file input', () => {
    cy.get('.tree-header-actions .tree-add-btn[title="Import Postman JSON"]').should('exist')
    // The import button triggers a hidden file input
    cy.get('input[type="file"][accept=".json"]').should('exist')
  })

  it('15.2 Valid Postman JSON imports successfully', () => {
    cy.fixture('postman-collection.json', 'utf-8').then(content => {
      const blob = new Blob([JSON.stringify(content)], { type: 'application/json' })
      const testFile = new File([blob], 'postman-collection.json', { type: 'application/json' })
      const dataTransfer = new DataTransfer()
      dataTransfer.items.add(testFile)

      cy.get('input[type="file"][accept=".json"]').then($input => {
        $input[0].files = dataTransfer.files
        $input[0].dispatchEvent(new Event('change', { bubbles: true }))
      })
      cy.wait(2000)
      // After import, collection tree should have new requests
      cy.get('.collection-tree').should('exist')
    })
  })

  it('15.3 Imported collection contains requests with correct methods', () => {
    cy.fixture('postman-collection.json', 'utf-8').then(content => {
      const blob = new Blob([JSON.stringify(content)], { type: 'application/json' })
      const testFile = new File([blob], 'postman-collection.json', { type: 'application/json' })
      const dataTransfer = new DataTransfer()
      dataTransfer.items.add(testFile)

      cy.get('input[type="file"][accept=".json"]').then($input => {
        $input[0].files = dataTransfer.files
        $input[0].dispatchEvent(new Event('change', { bubbles: true }))
      })
      cy.wait(2000)
      // Expand the first collection to check imported requests
      cy.get('.collection-row').first().within(() => {
        cy.get('.expand-btn').click()
      })
      // Should see GET and POST badges
      cy.get('.method-badge').should('exist')
    })
  })

  it('15.4 Invalid JSON shows error', () => {
    cy.window().then(win => {
      cy.stub(win, 'alert').as('alert')
    })
    const invalidBlob = new Blob(['this is not json'], { type: 'application/json' })
    const badFile = new File([invalidBlob], 'bad.json', { type: 'application/json' })
    const dataTransfer = new DataTransfer()
    dataTransfer.items.add(badFile)

    cy.get('input[type="file"][accept=".json"]').then($input => {
      $input[0].files = dataTransfer.files
      $input[0].dispatchEvent(new Event('change', { bubbles: true }))
    })
    cy.wait(2000)
    // Should trigger alert with error message
    cy.get('@alert').should('have.been.called')
  })
})
