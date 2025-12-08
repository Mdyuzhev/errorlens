describe('TestCases Tests', () => {
  beforeEach(() => {
    cy.login()
  })

  it('list_testcases', () => {
    cy.visit('/testcases')
    cy.get('[data-testid="testcases-list"], .testcases-list, .testcase-card').should('exist')
  })

  it('create_testcase', () => {
    cy.visit('/testcases')
    cy.contains(/new|создать|add/i).click()

    cy.get('input[name="title"], input[placeholder*="title"], input[placeholder*="название"]').type('Test Case 1')
    cy.get('textarea[name="steps"], textarea[placeholder*="steps"], textarea[placeholder*="шаги"]').type('Step 1\nStep 2')
    cy.contains(/save|сохранить/i).click()

    cy.contains('Test Case 1', { timeout: 5000 }).should('be.visible')
  })

  it('view_testcase', () => {
    cy.visit('/testcases')
    cy.get('.testcase-card, .testcase-item, [data-testid="testcase"]').first().click()

    cy.get('.modal, .dialog, .testcase-detail').should('be.visible')
  })

  it('filter_by_status', () => {
    cy.visit('/testcases')
    cy.get('select[name="status"], .status-filter, button').contains(/status|статус/i).click({ force: true })

    cy.wait(500)
  })

  it('filter_by_priority', () => {
    cy.visit('/testcases')
    cy.get('select[name="priority"], .priority-filter, button').contains(/priority|приоритет/i).click({ force: true })

    cy.wait(500)
  })
})
