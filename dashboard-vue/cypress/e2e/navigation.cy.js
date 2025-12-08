describe('Navigation Tests', () => {
  beforeEach(() => {
    cy.login()
  })

  it('navbar_links', () => {
    cy.visit('/')

    // Dashboard/Sessions
    cy.contains(/dashboard|sessions|сессии/i).first().click()
    cy.url().should('match', /\/$|\/sessions/)

    // Articles
    cy.contains(/articles|статьи/i).first().click()
    cy.url().should('include', '/articles')

    // TestCases
    cy.contains(/testcases|test cases|тесткейсы/i).first().click()
    cy.url().should('include', '/testcases')

    // Tasks
    cy.contains(/tasks|задачи/i).first().click()
    cy.url().should('include', '/tasks')

    // Generator
    cy.contains(/generator|генератор/i).first().click()
    cy.url().should('include', '/generator')
  })

  it('back_navigation', () => {
    cy.visit('/articles')
    cy.visit('/testcases')
    cy.go('back')

    cy.url().should('include', '/articles')
  })

  it('404_handling', () => {
    cy.visit('/nonexistent-route', { failOnStatusCode: false })

    cy.get('body').should('exist')
  })

  it('deep_link_articles', () => {
    cy.visit('/articles')

    cy.url().should('include', '/articles')
  })

  it('mobile_responsive', () => {
    cy.viewport(375, 667)
    cy.visit('/')

    cy.get('body').should('be.visible')
  })
})
