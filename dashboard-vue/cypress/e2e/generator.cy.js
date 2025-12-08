describe('Generator Tests', () => {
  beforeEach(() => {
    cy.login()
  })

  it('visit_generator_page', () => {
    cy.visit('/generator')
    cy.contains(/generator|генератор/i).should('be.visible')
  })

  it('tab_swagger', () => {
    cy.visit('/generator')
    cy.contains(/swagger|openapi/i).click()

    cy.get('input[type="file"], .file-upload').should('exist')
  })

  it('tab_session', () => {
    cy.visit('/generator')
    cy.contains(/session|сессия/i).click()

    cy.get('select, .session-selector').should('exist')
  })

  it('tab_url', () => {
    cy.visit('/generator')
    cy.contains(/url|endpoint/i).click()

    cy.get('input[type="url"], input[type="text"]').should('exist')
  })

  it('select_framework_pytest', () => {
    cy.visit('/generator')
    cy.contains(/pytest/i).click()

    cy.get('.framework-card.selected, [data-selected="true"]').should('exist')
  })

  it('select_framework_postman', () => {
    cy.visit('/generator')
    cy.contains(/postman/i).click()

    cy.get('.framework-card.selected, [data-selected="true"]').should('exist')
  })

  it('upload_swagger_json', () => {
    cy.visit('/generator')

    cy.fixture('test-data.json').then((data) => {
      const swaggerContent = JSON.stringify(data.testSwagger)
      const blob = new Blob([swaggerContent], { type: 'application/json' })
      const file = new File([blob], 'swagger.json', { type: 'application/json' })

      cy.get('input[type="file"]').first().selectFile({
        contents: Cypress.Buffer.from(swaggerContent),
        fileName: 'swagger.json',
        mimeType: 'application/json'
      }, { force: true })

      cy.wait(500)
    })
  })

  it('history_panel_exists', () => {
    cy.visit('/generator')
    cy.get('.history, [data-testid="history"]').should('exist')
  })
})
