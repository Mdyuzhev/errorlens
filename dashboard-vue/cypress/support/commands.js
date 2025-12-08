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
