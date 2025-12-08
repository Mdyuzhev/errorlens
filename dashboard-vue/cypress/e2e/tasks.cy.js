describe('Tasks Tests', () => {
  beforeEach(() => {
    cy.login()
  })

  it('view_board', () => {
    cy.visit('/tasks')
    cy.get('[data-testid="kanban-board"], .kanban, .board, .task-column').should('exist')
  })

  it('create_task', () => {
    cy.visit('/tasks')
    cy.contains(/new|создать|add|\+/i).first().click()

    cy.get('input[name="title"], input[placeholder*="title"], input[placeholder*="название"]').type('Test Task')
    cy.get('textarea[name="description"], textarea[placeholder*="description"]').type('Task description')
    cy.contains(/save|сохранить|create/i).click()

    cy.contains('Test Task', { timeout: 5000 }).should('be.visible')
  })

  it('filter_by_assignee', () => {
    cy.visit('/tasks')
    cy.get('select[name="assignee"], .assignee-filter').first().select(1, { force: true })

    cy.wait(500)
  })
})
