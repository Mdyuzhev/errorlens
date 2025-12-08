describe('Sessions Tests', () => {
  beforeEach(() => {
    cy.login()
  })

  it('list_sessions', () => {
    cy.visit('/')
    cy.get('[data-testid="sessions-list"], .sessions-list, .session-card').should('exist')
  })

  it('view_session_detail', () => {
    cy.visit('/')
    cy.get('.session-card, .session-item, [data-testid="session"]').first().click()

    cy.get('.modal, .dialog, .session-detail').should('be.visible')
  })

  it('filter_all', () => {
    cy.visit('/')
    cy.contains(/all|все/i).click()

    cy.wait(500)
  })

  it('filter_bugs', () => {
    cy.visit('/')
    cy.contains(/bugs|ошибки/i).click()

    cy.wait(500)
  })

  it('filter_chains', () => {
    cy.visit('/')
    cy.contains(/chains|цепочки/i).click()

    cy.wait(500)
  })
})
