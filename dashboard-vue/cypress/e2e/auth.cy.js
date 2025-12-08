describe('Auth Tests', () => {
  beforeEach(() => {
    cy.clearLocalStorage()
  })

  it('login_success', () => {
    cy.visit('/login')
    cy.get('input[type="text"]').type('owner1')
    cy.get('input[type="password"]').type('Test123!')
    cy.get('button[type="submit"]').click()

    cy.url().should('not.include', '/login')
    cy.window().then((win) => {
      expect(win.localStorage.getItem('access_token')).to.exist
    })
  })

  it('login_invalid_credentials', () => {
    cy.visit('/login')
    cy.get('input[type="text"]').type('owner1')
    cy.get('input[type="password"]').type('wrongpassword')
    cy.get('button[type="submit"]').click()

    cy.contains(/error|invalid|incorrect/i).should('be.visible')
    cy.url().should('include', '/login')
  })

  it('login_empty_fields', () => {
    cy.visit('/login')
    cy.get('button[type="submit"]').click()

    cy.url().should('include', '/login')
  })

  it('logout', () => {
    cy.login()
    cy.visit('/')

    cy.contains(/logout|выход/i).click()

    cy.url().should('include', '/login')
    cy.window().then((win) => {
      expect(win.localStorage.getItem('access_token')).to.be.null
    })
  })

  it('auth_guard_redirect', () => {
    cy.visit('/')
    cy.url().should('include', '/login')
  })

  it('auth_guard_allows', () => {
    cy.login()
    cy.visit('/')
    cy.url().should('not.include', '/login')
  })
})
