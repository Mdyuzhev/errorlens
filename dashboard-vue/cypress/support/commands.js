// Custom Cypress commands for ErrorLens

Cypress.Commands.add('login', (username = 'owner1', password = 'Test123!') => {
  cy.request({
    method: 'POST',
    url: `${Cypress.env('API_URL') || 'http://localhost:8000'}/auth/login`,
    body: { username, password }
  }).then((response) => {
    expect(response.status).to.eq(200)
    localStorage.setItem('access_token', response.body.access_token)
    localStorage.setItem('refresh_token', response.body.refresh_token)
  })
})

Cypress.Commands.add('logout', () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  cy.visit('/login')
})

Cypress.Commands.add('createArticle', (data) => {
  const token = localStorage.getItem('access_token')
  return cy.request({
    method: 'POST',
    url: `${Cypress.env('API_URL') || 'http://localhost:8000'}/articles`,
    headers: { Authorization: `Bearer ${token}` },
    body: data
  }).then((response) => response.body.id)
})

Cypress.Commands.add('createTestCase', (data) => {
  const token = localStorage.getItem('access_token')
  return cy.request({
    method: 'POST',
    url: `${Cypress.env('API_URL') || 'http://localhost:8000'}/testcases`,
    headers: { Authorization: `Bearer ${token}` },
    body: data
  }).then((response) => response.body.id)
})

Cypress.Commands.add('createTask', (data) => {
  const token = localStorage.getItem('access_token')
  return cy.request({
    method: 'POST',
    url: `${Cypress.env('API_URL') || 'http://localhost:8000'}/tasks`,
    headers: { Authorization: `Bearer ${token}` },
    body: data
  }).then((response) => response.body.id)
})

Cypress.Commands.add('resetDb', () => {
  // Reset test data - implement based on your backend
  cy.log('Database reset skipped - implement based on backend API')
})

Cypress.Commands.add('seedData', (fixtureName) => {
  cy.fixture(fixtureName).then((data) => {
    // Seed data - implement based on your backend
    cy.log(`Seeding data from ${fixtureName}`)
  })
})

// --- Pechkin Commands ---

Cypress.Commands.add('loginToApp', (username = 'owner1', password = 'Test123!') => {
  cy.visit('/dashboard/#/login')
  cy.get('input[type="text"]').clear().type(username)
  cy.get('input[type="password"]').clear().type(password)
  cy.get('button[type="submit"]').click()
  cy.url().should('not.include', '/login')
  cy.window().then(win => {
    expect(win.localStorage.getItem('access_token')).to.exist
  })
})

Cypress.Commands.add('apiLogin', () => {
  cy.request('POST', '/api/v1/auth/login', {
    username: 'owner1', password: 'Test123!'
  }).then(resp => {
    window.localStorage.setItem('access_token', resp.body.access_token)
  })
})

Cypress.Commands.add('openPechkin', () => {
  cy.visit('/dashboard/#/qa?tab=generator')
  cy.url().should('include', '/qa')
  cy.contains('Генератор').click()
  cy.get('.mode-btn').contains('Pechkin').then($btn => $btn[0].click())
  cy.contains('Collections').should('be.visible')
})

Cypress.Commands.add('selectMethod', (method) => {
  cy.get('select.method-select').then($sel => {
    $sel.val(method)
    $sel[0].dispatchEvent(new Event('change', { bubbles: true }))
    $sel[0].dispatchEvent(new Event('input', { bubbles: true }))
  })
  cy.get('select.method-select').should('have.value', method)
})

Cypress.Commands.add('createTestCollection', (name = 'CY-Test') => {
  cy.window().then(win => {
    const token = win.localStorage.getItem('access_token')
    cy.request({
      method: 'GET',
      url: '/api/v1/projects',
      headers: { Authorization: `Bearer ${token}` }
    }).then(resp => {
      const projectId = resp.body[0]?.id
      cy.request({
        method: 'POST',
        url: '/api/v1/pechkin/collections',
        headers: { Authorization: `Bearer ${token}` },
        body: { project_id: projectId, name }
      }).as('createdCollection')
    })
  })
})

Cypress.Commands.add('deleteCollection', (id) => {
  cy.window().then(win => {
    const token = win.localStorage.getItem('access_token')
    cy.request({
      method: 'DELETE',
      url: `/api/v1/pechkin/collections/${id}`,
      headers: { Authorization: `Bearer ${token}` },
      failOnStatusCode: false
    })
  })
})

// Creates a collection with one request via API, navigates to Pechkin, opens that request
Cypress.Commands.add('createCollectionWithRequest', () => {
  cy.loginToApp()
  cy.window().then(win => {
    const token = win.localStorage.getItem('access_token')
    // Get project id
    cy.request({
      method: 'GET',
      url: '/api/v1/projects',
      headers: { Authorization: `Bearer ${token}` }
    }).then(projResp => {
      const projectId = projResp.body[0]?.id
      // Create collection
      const colName = 'CY-Auto-' + Date.now()
      cy.request({
        method: 'POST',
        url: '/api/v1/pechkin/collections',
        headers: { Authorization: `Bearer ${token}` },
        body: { project_id: projectId, name: colName }
      }).then(colResp => {
        const colId = colResp.body.id
        // Create a request inside the collection
        cy.request({
          method: 'POST',
          url: `/api/v1/pechkin/collections/${colId}/requests`,
          headers: { Authorization: `Bearer ${token}` },
          body: { name: 'CY-Request', method: 'GET', url: 'https://httpbin.org/get' }
        }).then(() => {
          cy.wrap(colId).as('testColId')
          // Navigate to Pechkin
          cy.openPechkin()
          // Expand and click the collection, then click the request
          cy.contains('.collection-name', colName).closest('.collection-row').within(() => {
            cy.get('.expand-btn').click()
          })
          cy.get('.request-row').first().click()
          cy.get('.url-input').should('be.visible')
        })
      })
    })
  })
})

// Cleanup: delete the test collection created by createCollectionWithRequest
Cypress.Commands.add('deleteTestCollection', () => {
  cy.get('@testColId').then(colId => {
    cy.window().then(win => {
      const token = win.localStorage.getItem('access_token')
      cy.request({
        method: 'DELETE',
        url: `/api/v1/pechkin/collections/${colId}`,
        headers: { Authorization: `Bearer ${token}` },
        failOnStatusCode: false
      })
    })
  })
})
