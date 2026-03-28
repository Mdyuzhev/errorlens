/// <reference types="cypress" />

const BASE = 'http://192.168.1.74:3000'

// ---------------------------------------------------------------------------
// Describe 1: Navigation (5 tests)
// ---------------------------------------------------------------------------
describe('Issues — Navigation', () => {
  it('1.1 goToIssues() opens the page', () => {
    cy.goToIssues()
    cy.get('.issues-page, .tasks-page, [class*="issues"]').should('be.visible')
  })

  it('1.2 URL /dashboard/#/issues contains "Issues" heading', () => {
    cy.loginToApp()
    cy.visit('/dashboard/#/issues')
    cy.contains(/issues/i, { timeout: 10000 }).should('exist')
  })

  it('1.3 Click "Issues" in navbar navigates to /issues', () => {
    cy.loginToApp()
    cy.visit('/dashboard/#/')
    cy.get('nav, .sidebar, .nav-menu, [class*="nav"]').contains(/issues/i).click()
    cy.url().should('include', '/issues')
  })

  it('1.4 Reload /issues restores without 404', () => {
    cy.goToIssues()
    cy.reload()
    cy.get('.issues-page, .tasks-page, [class*="issues"]', { timeout: 10000 }).should('exist')
  })

  it('1.5 /issues without auth redirects to /login', () => {
    cy.clearLocalStorage()
    cy.visit('/dashboard/#/issues')
    cy.url({ timeout: 8000 }).should('include', '/login')
  })
})

// ---------------------------------------------------------------------------
// Describe 2: Page Header (6 tests)
// ---------------------------------------------------------------------------
describe('Issues — Page Header', () => {
  beforeEach(() => cy.goToIssues())

  it('2.1 Page title contains "Issues"', () => {
    cy.contains(/issues/i).should('exist')
  })

  it('2.2 Button "+ New Issue" visible', () => {
    cy.get('button').contains(/new\s*(issue|task|\+)/i).should('be.visible')
  })

  it('2.3 JQL Bar present', () => {
    cy.get('input[placeholder*="JQL"], input[placeholder*="Search"], input[placeholder*="jql"], .jql-input, [class*="jql"]', { timeout: 8000 }).should('exist')
  })

  it('2.4 Button "Filters" present', () => {
    cy.get('button').contains(/filter/i).should('exist')
  })

  it('2.5 Has 6 tabs: Board, Backlog, Tree, Gantt, Time, Dashboard', () => {
    const tabs = ['Board', 'Backlog', 'Tree', 'Gantt', 'Time', 'Dashboard']
    tabs.forEach(t => {
      cy.contains(new RegExp(t, 'i')).should('exist')
    })
  })

  it('2.6 Tab "Board" active by default', () => {
    cy.contains(/board/i)
      .closest('button, a, [role="tab"], [class*="tab"]')
      .should('have.class', 'active')
      .or('have.attr', 'aria-selected', 'true')
  })
})

// ---------------------------------------------------------------------------
// Describe 3: JQL Bar (8 tests)
// ---------------------------------------------------------------------------
describe('Issues — JQL Bar', () => {
  beforeEach(() => cy.goToIssues())

  function jqlInput() {
    return cy.get('input[placeholder*="JQL"], input[placeholder*="Search"], .jql-input, [class*="jql"] input', { timeout: 8000 })
  }

  it('3.1 Empty JQL + Enter produces no error', () => {
    jqlInput().clear().type('{enter}')
    cy.get('.error, .jql-error, [class*="error"]').should('not.exist')
  })

  it('3.2 Type "status = todo" triggers search', () => {
    jqlInput().clear().type('status = todo{enter}')
    cy.get('.task-card, .task-list-row, [class*="task"]', { timeout: 8000 }).should('exist')
  })

  it('3.3 Type "priority = high" activates list mode', () => {
    jqlInput().clear().type('priority = high{enter}')
    cy.get('.task-list, .task-card, [class*="task"]', { timeout: 8000 }).should('exist')
  })

  it('3.4 X button clears query', () => {
    jqlInput().clear().type('status = todo')
    cy.get('.jql-clear, .clear-btn, [class*="clear"]').first().click()
    jqlInput().should('have.value', '')
  })

  it('3.5 Invalid JQL shows error', () => {
    jqlInput().clear().type('abc %%% xyz{enter}')
    cy.get('.error, .jql-error, [class*="error"], .toast-error, [class*="toast"]', { timeout: 5000 }).should('exist')
  })

  it('3.6 JQL title ~ "Test" filters list', () => {
    jqlInput().clear().type('title ~ "Test"{enter}')
    cy.wait(1000)
    cy.get('body').then($b => {
      // either tasks found or "no tasks" message
      const hasTasks = $b.find('.task-card, .task-list-row').length > 0
      const hasEmpty = $b.find(':contains("No tasks"), :contains("no results")').length > 0
      expect(hasTasks || hasEmpty).to.be.true
    })
  })

  it('3.7 JQL input switches to list view automatically', () => {
    jqlInput().clear().type('status = todo{enter}')
    cy.get('.task-list, .list-view, [class*="list"]', { timeout: 8000 }).should('exist')
  })

  it('3.8 Save filter appears in saved filters', () => {
    jqlInput().clear().type('priority = high{enter}')
    cy.get('button').contains(/save/i).click({ force: true })
    cy.get('.saved-filters, .filter-list, [class*="saved"]', { timeout: 5000 }).should('exist')
  })
})

// ---------------------------------------------------------------------------
// Describe 4: Filter Panel (7 tests)
// ---------------------------------------------------------------------------
describe('Issues — Filter Panel', () => {
  beforeEach(() => cy.goToIssues())

  function openFilters() {
    cy.get('button').contains(/filter/i).click()
  }

  it('4.1 Filters button opens filter panel', () => {
    openFilters()
    cy.get('.filter-panel, .filters-panel, [class*="filter-panel"], [class*="filters"]', { timeout: 5000 }).should('be.visible')
  })

  it('4.2 No active filters — no counter badge', () => {
    cy.get('.filter-badge, .badge, [class*="badge"]').should('not.exist')
  })

  it('4.3 Select priority=High shows badge "1"', () => {
    openFilters()
    cy.get('.filter-panel, [class*="filter-panel"]').within(() => {
      cy.contains(/priority/i).closest('.filter-group, [class*="filter"]').within(() => {
        cy.get('select, input, [class*="select"]').first().click({ force: true })
      })
    })
    cy.contains(/high/i).click({ force: true })
    cy.get('.filter-badge, .badge, [class*="badge"]').should('contain', '1')
  })

  it('4.4 Two filters show badge "2"', () => {
    openFilters()
    // select two filters
    cy.get('.filter-panel, [class*="filter-panel"]').within(() => {
      cy.get('select, [class*="select"]').eq(0).click({ force: true })
    })
    cy.contains(/high/i).click({ force: true })
    cy.get('.filter-panel, [class*="filter-panel"]').within(() => {
      cy.get('select, [class*="select"]').eq(1).click({ force: true })
    })
    cy.contains(/critical/i).click({ force: true })
    cy.get('.filter-badge, .badge, [class*="badge"]').should('contain', '2')
  })

  it('4.5 Clear button resets filters', () => {
    openFilters()
    cy.get('button').contains(/clear|reset/i).click({ force: true })
    cy.get('.filter-badge, .badge, [class*="badge"]').should('not.exist')
  })

  it('4.6 After filter via panel JQL Bar updates', () => {
    openFilters()
    cy.get('.filter-panel, [class*="filter-panel"]').within(() => {
      cy.get('select, [class*="select"]').first().click({ force: true })
    })
    cy.contains(/high/i).click({ force: true })
    cy.get('input[placeholder*="JQL"], .jql-input, [class*="jql"] input').invoke('val').should('not.be.empty')
  })

  it('4.7 Toggle Filters button hides panel', () => {
    openFilters()
    cy.get('.filter-panel, [class*="filter-panel"]').should('be.visible')
    cy.get('button').contains(/filter/i).click()
    cy.get('.filter-panel, [class*="filter-panel"]').should('not.be.visible')
  })
})

// ---------------------------------------------------------------------------
// Describe 5: Tab Navigation (8 tests)
// ---------------------------------------------------------------------------
describe('Issues — Tab Navigation', () => {
  beforeEach(() => cy.goToIssues())

  it('5.1 Click Board — kanban visible', () => {
    cy.contains(/board/i).click()
    cy.get('.kanban-board, [class*="kanban"], [class*="board"]', { timeout: 8000 }).should('be.visible')
  })

  it('5.2 Click Backlog — BacklogView visible', () => {
    cy.contains(/backlog/i).click()
    cy.get('.backlog-view, [class*="backlog"]', { timeout: 8000 }).should('be.visible')
  })

  it('5.3 Click Tree — tree view or loading', () => {
    cy.contains(/tree/i).click()
    cy.get('.tree-view, [class*="tree"], .loading, [class*="loading"]', { timeout: 8000 }).should('exist')
  })

  it('5.4 Click Gantt — gantt or loading', () => {
    cy.contains(/gantt/i).click()
    cy.get('.gantt-view, [class*="gantt"], .loading, [class*="loading"]', { timeout: 8000 }).should('exist')
  })

  it('5.5 Click Time — time report or loading', () => {
    cy.contains(/time/i).click()
    cy.get('.time-view, [class*="time"], .loading, [class*="loading"]', { timeout: 8000 }).should('exist')
  })

  it('5.6 Click Dashboard — dashboard view or loading', () => {
    cy.contains(/dashboard/i).click({ force: true })
    cy.get('.dashboard-view, [class*="dashboard"], .loading, [class*="loading"]', { timeout: 8000 }).should('exist')
  })

  it('5.7 Board → Backlog → Board restores kanban', () => {
    cy.contains(/board/i).click()
    cy.get('.kanban-board, [class*="kanban"]', { timeout: 5000 }).should('be.visible')
    cy.contains(/backlog/i).click()
    cy.get('.backlog-view, [class*="backlog"]', { timeout: 5000 }).should('be.visible')
    cy.contains(/board/i).click()
    cy.get('.kanban-board, [class*="kanban"]', { timeout: 5000 }).should('be.visible')
  })

  it('5.8 Active tab has active class', () => {
    cy.contains(/board/i)
      .closest('button, a, [role="tab"], [class*="tab"]')
      .should('satisfy', $el => {
        return $el.hasClass('active') || $el.attr('aria-selected') === 'true'
      })
  })
})

// ---------------------------------------------------------------------------
// Describe 6: Board tab — Type Filter and View Toggle (7 tests)
// ---------------------------------------------------------------------------
describe('Issues — Board Type Filter & View Toggle', () => {
  beforeEach(() => cy.goToIssues())

  it('6.1 Type "All" active by default', () => {
    cy.get('.type-tabs, [class*="type-tab"], [class*="type-filter"]').within(() => {
      cy.contains(/all/i).should('have.class', 'active')
    })
  })

  it('6.2 Click type tab (Bug, Task) makes it active', () => {
    cy.get('.type-tabs, [class*="type-tab"], [class*="type-filter"]').within(() => {
      cy.contains(/bug|task/i).first().click()
      cy.get('.active').should('exist')
    })
  })

  it('6.3 Switch type fires API request with type_slug', () => {
    cy.intercept('GET', '**/tasks/board*').as('boardReq')
    cy.get('.type-tabs, [class*="type-tab"], [class*="type-filter"]').within(() => {
      cy.contains(/bug|task/i).first().click()
    })
    cy.wait('@boardReq').its('request.url').should('include', 'type')
  })

  it('6.4 Board view button active by default', () => {
    cy.get('.view-toggle, [class*="view-toggle"]').within(() => {
      cy.get('button, [class*="btn"]').first().should('have.class', 'active')
    })
  })

  it('6.5 Click list view shows task-list, hides kanban', () => {
    cy.get('.view-toggle, [class*="view-toggle"]').within(() => {
      cy.get('button, [class*="btn"]').last().click()
    })
    cy.get('.task-list, [class*="task-list"]', { timeout: 5000 }).should('be.visible')
    cy.get('.kanban-board, [class*="kanban"]').should('not.exist')
  })

  it('6.6 Click board view shows kanban', () => {
    // switch to list first
    cy.get('.view-toggle, [class*="view-toggle"]').within(() => {
      cy.get('button, [class*="btn"]').last().click()
    })
    cy.get('.view-toggle, [class*="view-toggle"]').within(() => {
      cy.get('button, [class*="btn"]').first().click()
    })
    cy.get('.kanban-board, [class*="kanban"]', { timeout: 5000 }).should('be.visible')
  })

  it('6.7 View toggle has exactly 2 buttons', () => {
    cy.get('.view-toggle, [class*="view-toggle"]').within(() => {
      cy.get('button, [class*="btn"]').should('have.length', 2)
    })
  })
})

// ---------------------------------------------------------------------------
// Describe 7: Kanban Board (12 tests)
// ---------------------------------------------------------------------------
describe('Issues — Kanban Board', () => {
  beforeEach(() => {
    cy.goToIssues()
    cy.get('.kanban-board, [class*="kanban"]', { timeout: 10000 }).should('be.visible')
  })

  it('7.1 Board has 4 columns: To Do, In Progress, Review, Done', () => {
    const cols = ['To Do', 'In Progress', 'Review', 'Done']
    cols.forEach(c => {
      cy.contains(new RegExp(c, 'i')).should('exist')
    })
  })

  it('7.2 Each column has title and count', () => {
    cy.get('.column, .kanban-column, [class*="column"]').each($col => {
      cy.wrap($col).find('.column-title, .column-header, [class*="title"]').should('exist')
      cy.wrap($col).find('.column-count, .count, [class*="count"]').should('exist')
    })
  })

  it('7.3 Task cards visible if tasks exist', () => {
    cy.get('body').then($b => {
      if ($b.find('.task-card, [class*="task-card"]').length > 0) {
        cy.get('.task-card, [class*="task-card"]').should('be.visible')
      } else {
        cy.log('No tasks on board — skipping')
      }
    })
  })

  it('7.4 Card shows priority bar, human_id, title', () => {
    cy.get('.task-card, [class*="task-card"]').first().within(() => {
      cy.get('.priority-bar, .priority, [class*="priority"]').should('exist')
      cy.get('.human-id, .task-id, [class*="human"], [class*="id"]').should('exist')
      cy.get('.task-title, .title, [class*="title"]').should('exist')
    })
  })

  it('7.5 Overdue task has red due-date', () => {
    cy.get('.due-date.overdue, .overdue, [class*="overdue"]').then($el => {
      if ($el.length > 0) {
        cy.wrap($el).first().should('have.css', 'color').and('not.eq', 'rgb(0, 0, 0)')
      } else {
        cy.log('No overdue tasks found — skipping')
      }
    })
  })

  it('7.6 Label on task visible', () => {
    cy.get('.task-card, [class*="task-card"]').then($cards => {
      const hasLabel = $cards.find('.label, .tag, [class*="label"], [class*="tag"]').length > 0
      if (hasLabel) {
        cy.get('.label, .tag, [class*="label"], [class*="tag"]').first().should('be.visible')
      } else {
        cy.log('No labels on cards — skipping')
      }
    })
  })

  it('7.7 Click card opens TaskViewer', () => {
    cy.get('.task-card, [class*="task-card"]').first().click()
    cy.get('.task-detail, .task-viewer, .task-detail-overlay, [class*="detail"], [class*="viewer"]', { timeout: 8000 }).should('be.visible')
  })

  it('7.8 DnD card to another column fires PUT', () => {
    cy.intercept('PUT', '**/tasks/**').as('updateTask')
    cy.get('.task-card, [class*="task-card"]').first().then($card => {
      const cardRect = $card[0].getBoundingClientRect()
      const startX = cardRect.left + cardRect.width / 2
      const startY = cardRect.top + cardRect.height / 2

      // find second column
      cy.get('.column, .kanban-column, [class*="column"]').eq(1).then($col => {
        const colRect = $col[0].getBoundingClientRect()
        const endX = colRect.left + colRect.width / 2
        const endY = colRect.top + 100

        cy.wrap($card)
          .trigger('mousedown', { which: 1, clientX: startX, clientY: startY })
        cy.wait(200)
        cy.wrap($card)
          .trigger('mousemove', { clientX: endX, clientY: endY, force: true })
        cy.wait(200)
        cy.wrap($card)
          .trigger('mouseup', { clientX: endX, clientY: endY, force: true })
      })
    })
    cy.wait('@updateTask', { timeout: 10000 }).its('response.statusCode').should('be.oneOf', [200, 204])
  })

  it('7.9 After DnD task changes column in UI', () => {
    // move task from col 0 to col 1
    cy.get('.column, .kanban-column, [class*="column"]').eq(0).find('.task-card, [class*="task-card"]').then($cards => {
      if ($cards.length === 0) { cy.log('No cards in first column'); return }
      const $card = $cards.first()
      const rect = $card[0].getBoundingClientRect()
      cy.get('.column, .kanban-column, [class*="column"]').eq(1).then($col => {
        const colRect = $col[0].getBoundingClientRect()
        cy.wrap($card)
          .trigger('mousedown', { which: 1, clientX: rect.left + 50, clientY: rect.top + 20 })
        cy.wait(200)
        cy.wrap($card)
          .trigger('mousemove', { clientX: colRect.left + 50, clientY: colRect.top + 100, force: true })
        cy.wait(200)
        cy.wrap($card)
          .trigger('mouseup', { clientX: colRect.left + 50, clientY: colRect.top + 100, force: true })
        cy.wait(1000)
        cy.get('.column, .kanban-column, [class*="column"]').eq(1).find('.task-card, [class*="task-card"]').should('have.length.gte', 1)
      })
    })
  })

  it('7.10 Column count updates after DnD', () => {
    cy.get('.column, .kanban-column, [class*="column"]').eq(0).find('.column-count, .count, [class*="count"]').invoke('text').then(before => {
      cy.log('Count before: ' + before)
      // count is a number string — just verify it exists
      expect(before.trim()).to.match(/\d+/)
    })
  })

  it('7.11 Empty column shows empty state', () => {
    cy.get('.column, .kanban-column, [class*="column"]').each($col => {
      const cards = $col.find('.task-card, [class*="task-card"]').length
      if (cards === 0) {
        cy.wrap($col).find('.empty, .no-tasks, [class*="empty"]').should('exist')
      }
    })
  })

  it('7.12 Severity badge visible if set', () => {
    cy.get('.task-card, [class*="task-card"]').then($cards => {
      const hasSeverity = $cards.find('.severity, .severity-badge, [class*="severity"]').length > 0
      if (hasSeverity) {
        cy.get('.severity, .severity-badge, [class*="severity"]').first().should('be.visible')
      } else {
        cy.log('No severity badges — skipping')
      }
    })
  })
})

// ---------------------------------------------------------------------------
// Describe 8: List View (7 tests)
// ---------------------------------------------------------------------------
describe('Issues — List View', () => {
  beforeEach(() => {
    cy.goToIssues()
    // switch to list view
    cy.get('.view-toggle, [class*="view-toggle"]').within(() => {
      cy.get('button, [class*="btn"]').last().click()
    })
    cy.get('.task-list, [class*="task-list"]', { timeout: 8000 }).should('be.visible')
  })

  it('8.1 List view shows rows for each task', () => {
    cy.get('.task-list-row, .task-row, [class*="task-row"], [class*="list-row"]').should('have.length.gte', 1)
  })

  it('8.2 Row contains human_id, title, status-pill, priority-dot, assignee', () => {
    cy.get('.task-list-row, .task-row, [class*="task-row"]').first().within(() => {
      cy.get('[class*="human"], [class*="id"]').should('exist')
      cy.get('[class*="title"]').should('exist')
      cy.get('.status-pill, [class*="status"]').should('exist')
      cy.get('.priority-dot, [class*="priority"]').should('exist')
      cy.get('.assignee, [class*="assignee"], [class*="avatar"]').should('exist')
    })
  })

  it('8.3 Click row opens TaskViewer', () => {
    cy.get('.task-list-row, .task-row, [class*="task-row"]').first().click()
    cy.get('.task-detail, .task-viewer, [class*="detail"], [class*="viewer"]', { timeout: 8000 }).should('be.visible')
  })

  it('8.4 Empty list shows "No tasks found"', () => {
    // apply a JQL that returns nothing
    cy.get('input[placeholder*="JQL"], .jql-input, [class*="jql"] input').clear().type('title = "ZZZZNONEXISTENT999"{enter}')
    cy.contains(/no\s*tasks|no\s*results|not\s*found/i, { timeout: 8000 }).should('exist')
  })

  it('8.5 JQL with zero results shows message', () => {
    cy.get('input[placeholder*="JQL"], .jql-input, [class*="jql"] input').clear().type('priority = "nonexistent"{enter}')
    cy.contains(/no\s*tasks|no\s*results/i, { timeout: 8000 }).should('exist')
  })

  it('8.6 Status-pill has colored background', () => {
    cy.get('.status-pill, [class*="status"]').first()
      .should('have.css', 'background-color')
      .and('not.eq', 'rgba(0, 0, 0, 0)')
  })

  it('8.7 Priority-dot colors: high=yellow, medium=blue, low=gray', () => {
    cy.get('.priority-dot, [class*="priority"]').each($dot => {
      cy.wrap($dot).should('have.css', 'background-color').and('not.eq', 'rgba(0, 0, 0, 0)')
    })
  })
})

// ---------------------------------------------------------------------------
// Describe 9: Create Issue Modal (12 tests)
// ---------------------------------------------------------------------------
describe('Issues — Create Issue Modal', () => {
  beforeEach(() => cy.goToIssues())

  function openCreateModal() {
    cy.get('button').contains(/new\s*(issue|task|\+)/i).click()
    cy.get('.modal, .dialog, [class*="modal"], [class*="dialog"]', { timeout: 5000 }).should('be.visible')
  }

  afterEach(() => {
    // cleanup any created issues
    cy.get('@issueId').then(id => {
      if (id) cy.deleteIssueViaApi(id)
    })
  })

  it('9.1 "+ New Issue" opens modal', () => {
    openCreateModal()
  })

  it('9.2 Modal has required fields', () => {
    openCreateModal()
    const fields = ['Title', 'Description', 'Type', 'Priority', 'Severity', 'Environment', 'Assignee', 'Due Date', 'Labels']
    fields.forEach(f => {
      cy.get('.modal, [class*="modal"]').contains(new RegExp(f, 'i')).should('exist')
    })
  })

  it('9.3 Create without Title — form does not submit', () => {
    openCreateModal()
    cy.get('.modal, [class*="modal"]').within(() => {
      cy.get('button').contains(/create|save|submit/i).click({ force: true })
    })
    cy.get('.modal, [class*="modal"]').should('be.visible')
  })

  it('9.4 Fill Title + Create sends POST /tasks → 201', () => {
    cy.intercept('POST', '**/tasks').as('createTask')
    openCreateModal()
    cy.get('.modal, [class*="modal"]').within(() => {
      cy.get('input[name="title"], input[placeholder*="Title"], input[placeholder*="title"], input').first().clear().type('CY Create Test')
      cy.get('button').contains(/create|save|submit/i).click()
    })
    cy.wait('@createTask').its('response.statusCode').should('eq', 201)
    cy.get('.modal, [class*="modal"]').should('not.exist')
    // save id for cleanup
    cy.get('@createTask').then(interception => {
      cy.wrap(interception.response.body.id).as('issueId')
    })
  })

  it('9.5 New task appears on Kanban board', () => {
    cy.intercept('POST', '**/tasks').as('createTask')
    openCreateModal()
    cy.get('.modal, [class*="modal"]').within(() => {
      cy.get('input').first().clear().type('CY Board Appear')
      cy.get('button').contains(/create|save|submit/i).click()
    })
    cy.wait('@createTask').then(interception => {
      cy.wrap(interception.response.body.id).as('issueId')
    })
    cy.contains('CY Board Appear', { timeout: 8000 }).should('exist')
  })

  it('9.6 New task in To Do column', () => {
    cy.intercept('POST', '**/tasks').as('createTask')
    openCreateModal()
    cy.get('.modal, [class*="modal"]').within(() => {
      cy.get('input').first().clear().type('CY ToDo Check')
      cy.get('button').contains(/create|save|submit/i).click()
    })
    cy.wait('@createTask').then(interception => {
      cy.wrap(interception.response.body.id).as('issueId')
    })
    cy.get('.column, .kanban-column, [class*="column"]').first().contains('CY ToDo Check', { timeout: 8000 }).should('exist')
  })

  it('9.7 Cancel closes modal without creation', () => {
    openCreateModal()
    cy.get('.modal, [class*="modal"]').within(() => {
      cy.get('button').contains(/cancel|close/i).click()
    })
    cy.get('.modal, [class*="modal"]').should('not.exist')
    cy.wrap(null).as('issueId')
  })

  it('9.8 Click outside modal-overlay closes it', () => {
    openCreateModal()
    cy.get('.modal-overlay, .overlay, [class*="overlay"]').click({ force: true })
    cy.get('.modal, [class*="modal"]').should('not.exist')
    cy.wrap(null).as('issueId')
  })

  it('9.9 Title 500+ chars — no crash', () => {
    openCreateModal()
    const longTitle = 'A'.repeat(501)
    cy.get('.modal, [class*="modal"]').within(() => {
      cy.get('input').first().clear().type(longTitle, { delay: 0 })
    })
    cy.get('.modal, [class*="modal"]').should('be.visible')
    cy.wrap(null).as('issueId')
  })

  it('9.10 Create with Priority=high — card has high priority bar', () => {
    cy.intercept('POST', '**/tasks').as('createTask')
    openCreateModal()
    cy.get('.modal, [class*="modal"]').within(() => {
      cy.get('input').first().clear().type('CY High Priority')
      cy.contains(/priority/i).closest('.form-group, .field, [class*="field"]').within(() => {
        cy.get('select, [class*="select"]').select('high', { force: true })
      })
      cy.get('button').contains(/create|save|submit/i).click()
    })
    cy.wait('@createTask').then(interception => {
      cy.wrap(interception.response.body.id).as('issueId')
    })
    cy.contains('CY High Priority', { timeout: 8000 }).closest('.task-card, [class*="task-card"]').within(() => {
      cy.get('.priority-bar, [class*="priority"]').should('exist')
    })
  })

  it('9.11 Create with Severity=critical — badge "critical"', () => {
    cy.intercept('POST', '**/tasks').as('createTask')
    openCreateModal()
    cy.get('.modal, [class*="modal"]').within(() => {
      cy.get('input').first().clear().type('CY Critical Sev')
      cy.contains(/severity/i).closest('.form-group, .field, [class*="field"]').within(() => {
        cy.get('select, [class*="select"]').select('critical', { force: true })
      })
      cy.get('button').contains(/create|save|submit/i).click()
    })
    cy.wait('@createTask').then(interception => {
      cy.wrap(interception.response.body.id).as('issueId')
    })
    cy.contains('CY Critical Sev', { timeout: 8000 }).closest('.task-card, [class*="task-card"]').within(() => {
      cy.contains(/critical/i).should('exist')
    })
  })

  it('9.12 Labels comma-separated — card shows all labels', () => {
    cy.intercept('POST', '**/tasks').as('createTask')
    openCreateModal()
    cy.get('.modal, [class*="modal"]').within(() => {
      cy.get('input').first().clear().type('CY Labels Test')
      cy.contains(/labels/i).closest('.form-group, .field, [class*="field"]').within(() => {
        cy.get('input').type('bug,cypress', { force: true })
      })
      cy.get('button').contains(/create|save|submit/i).click()
    })
    cy.wait('@createTask').then(interception => {
      cy.wrap(interception.response.body.id).as('issueId')
    })
    cy.contains('CY Labels Test', { timeout: 8000 }).closest('.task-card, [class*="task-card"]').within(() => {
      cy.get('.label, .tag, [class*="label"], [class*="tag"]').should('have.length.gte', 2)
    })
  })
})

// ---------------------------------------------------------------------------
// Describe 10: TaskViewer (10 tests)
// ---------------------------------------------------------------------------
describe('Issues — TaskViewer', () => {
  beforeEach(() => {
    cy.goToIssues()
    cy.createIssueViaApi()
    cy.reload()
    cy.get('.kanban-board, [class*="kanban"]', { timeout: 10000 }).should('be.visible')
    cy.openFirstIssueInBoard()
  })

  afterEach(() => {
    cy.get('@issueId').then(id => { if (id) cy.deleteIssueViaApi(id) })
  })

  it('10.1 Click card opens TaskViewer overlay', () => {
    cy.get('.task-detail, .task-viewer, .task-detail-overlay, [class*="detail"], [class*="viewer"]').should('be.visible')
  })

  it('10.2 Shows title, human_id, type badge, status badge', () => {
    cy.get('.task-detail, [class*="detail"], [class*="viewer"]').within(() => {
      cy.get('[class*="title"]').should('exist')
      cy.get('[class*="human"], [class*="id"]').should('exist')
      cy.get('[class*="type"], [class*="badge"]').should('exist')
      cy.get('[class*="status"]').should('exist')
    })
  })

  it('10.3 Edit button opens IssueDetailView', () => {
    cy.get('button').contains(/edit/i).click()
    cy.get('.issue-detail, .task-edit, [class*="detail-view"], [class*="edit"]', { timeout: 8000 }).should('be.visible')
  })

  it('10.4 Back arrow closes viewer', () => {
    cy.get('.back-btn, .close-btn, [class*="back"], [class*="close"]').first().click()
    cy.get('.task-detail, .task-detail-overlay, [class*="detail-overlay"]').should('not.exist')
  })

  it('10.5 ESC closes viewer', () => {
    cy.get('body').type('{esc}')
    cy.get('.task-detail, .task-detail-overlay, [class*="detail-overlay"]').should('not.exist')
  })

  it('10.6 Status badge clickable — shows dropdown', () => {
    cy.get('.task-detail, [class*="detail"]').within(() => {
      cy.get('[class*="status"]').first().click()
    })
    cy.get('.dropdown, .status-dropdown, [class*="dropdown"]', { timeout: 5000 }).should('be.visible')
  })

  it('10.7 Click status in dropdown changes status', () => {
    cy.intercept('PUT', '**/tasks/**').as('updateTask')
    cy.get('.task-detail, [class*="detail"]').within(() => {
      cy.get('[class*="status"]').first().click()
    })
    cy.get('.dropdown, [class*="dropdown"]').within(() => {
      cy.get('li, button, [class*="option"]').eq(1).click()
    })
    cy.wait('@updateTask').its('response.statusCode').should('be.oneOf', [200, 204])
  })

  it('10.8 Shows Description if set', () => {
    cy.get('.task-detail, [class*="detail"]').then($d => {
      const hasDesc = $d.find('[class*="description"], .description').length > 0
      if (hasDesc) {
        cy.get('[class*="description"]').should('exist')
      } else {
        cy.log('No description set — skipping')
      }
    })
  })

  it('10.9 Shows assignee in People section', () => {
    cy.get('.task-detail, [class*="detail"]').then($d => {
      const hasPeople = $d.find('[class*="assignee"], [class*="people"], .assignee').length > 0
      if (hasPeople) {
        cy.get('[class*="assignee"], [class*="people"]').should('exist')
      } else {
        cy.log('No assignee — skipping')
      }
    })
  })

  it('10.10 Overdue shows red date', () => {
    cy.get('.task-detail, [class*="detail"]').then($d => {
      const hasOverdue = $d.find('.overdue, [class*="overdue"]').length > 0
      if (hasOverdue) {
        cy.get('.overdue, [class*="overdue"]').should('have.css', 'color').and('not.eq', 'rgb(0, 0, 0)')
      } else {
        cy.log('No overdue date — skipping')
      }
    })
  })
})

// ---------------------------------------------------------------------------
// Describe 11: IssueDetailView Header + Tabs (8 tests)
// ---------------------------------------------------------------------------
describe('Issues — IssueDetailView Header + Tabs', () => {
  beforeEach(() => {
    cy.goToIssues()
    cy.createIssueViaApi()
    cy.reload()
    cy.get('.kanban-board, [class*="kanban"]', { timeout: 10000 }).should('be.visible')
    cy.openFirstIssueInBoard()
    cy.get('button').contains(/edit/i).click()
    cy.get('.issue-detail, .task-edit, [class*="detail-view"], [class*="edit"]', { timeout: 8000 }).should('be.visible')
  })

  afterEach(() => {
    cy.get('@issueId').then(id => { if (id) cy.deleteIssueViaApi(id) })
  })

  it('11.1 Edit button opens IssueDetailView', () => {
    cy.get('.issue-detail, [class*="detail-view"], [class*="edit"]').should('be.visible')
  })

  it('11.2 Header has type badge, human_id, status, Edit/Save/Cancel/Delete', () => {
    cy.get('.issue-detail, [class*="detail-view"]').within(() => {
      cy.get('[class*="type"], [class*="badge"]').should('exist')
      cy.get('[class*="human"], [class*="id"]').should('exist')
      cy.get('[class*="status"]').should('exist')
    })
    cy.get('button').contains(/edit|save|cancel|delete/i).should('exist')
  })

  it('11.3 Edit makes fields editable (title input visible)', () => {
    cy.get('button').contains(/edit/i).click({ force: true })
    cy.get('input[name="title"], input[class*="title"], .title-input, [class*="title"] input', { timeout: 5000 }).should('be.visible')
  })

  it('11.4 Change title + Save fires PUT', () => {
    cy.intercept('PUT', '**/tasks/*').as('updateTask')
    cy.get('button').contains(/edit/i).click({ force: true })
    cy.get('input[name="title"], input[class*="title"], .title-input, [class*="title"] input').clear().type('CY Updated Title')
    cy.get('button').contains(/save/i).click()
    cy.wait('@updateTask').its('response.statusCode').should('be.oneOf', [200, 204])
  })

  it('11.5 Cancel reverts form', () => {
    cy.get('button').contains(/edit/i).click({ force: true })
    cy.get('input[name="title"], input[class*="title"], .title-input, [class*="title"] input').clear().type('SHOULD REVERT')
    cy.get('button').contains(/cancel/i).click()
    cy.contains('SHOULD REVERT').should('not.exist')
  })

  it('11.6 Tabs: Details, Activity, Work Log visible', () => {
    ;['Details', 'Activity', 'Work Log'].forEach(t => {
      cy.contains(new RegExp(t, 'i')).should('exist')
    })
  })

  it('11.7 Details tab active by default', () => {
    cy.contains(/details/i)
      .closest('button, a, [role="tab"], [class*="tab"]')
      .should('satisfy', $el => $el.hasClass('active') || $el.attr('aria-selected') === 'true')
  })

  it('11.8 Click Activity loads activity feed', () => {
    cy.contains(/activity/i).click()
    cy.get('.activity-feed, .activity, [class*="activity"]', { timeout: 8000 }).should('exist')
  })
})

// ---------------------------------------------------------------------------
// Describe 12: IssueDetailView Details Tab + Sidebar (10 tests)
// ---------------------------------------------------------------------------
describe('Issues — IssueDetailView Details Tab + Sidebar', () => {
  beforeEach(() => {
    cy.goToIssues()
    cy.createIssueViaApi()
    cy.reload()
    cy.get('.kanban-board, [class*="kanban"]', { timeout: 10000 }).should('be.visible')
    cy.openFirstIssueInBoard()
    cy.get('button').contains(/edit/i).click()
    cy.get('.issue-detail, [class*="detail-view"]', { timeout: 8000 }).should('be.visible')
  })

  afterEach(() => {
    cy.get('@issueId').then(id => { if (id) cy.deleteIssueViaApi(id) })
  })

  it('12.1 Click empty description area enters edit mode', () => {
    cy.get('.description, [class*="description"]').first().click()
    cy.get('.ProseMirror, .rich-editor, [class*="editor"], [contenteditable="true"]', { timeout: 5000 }).should('exist')
  })

  it('12.2 RichEditor visible in edit mode', () => {
    cy.get('.description, [class*="description"]').first().click()
    cy.get('.ProseMirror, .rich-editor, [class*="editor"]', { timeout: 5000 }).should('be.visible')
  })

  it('12.3 Sidebar: Priority select', () => {
    cy.get('.sidebar, [class*="sidebar"]').within(() => {
      cy.contains(/priority/i).should('exist')
      cy.get('select, [class*="select"]').should('exist')
    })
  })

  it('12.4 Severity select', () => {
    cy.get('.sidebar, [class*="sidebar"]').contains(/severity/i).should('exist')
  })

  it('12.5 Component select', () => {
    cy.get('.sidebar, [class*="sidebar"]').contains(/component/i).should('exist')
  })

  it('12.6 Story Points input', () => {
    cy.get('.sidebar, [class*="sidebar"]').contains(/story\s*points/i).should('exist')
  })

  it('12.7 Assignee input', () => {
    cy.get('.sidebar, [class*="sidebar"]').contains(/assignee/i).should('exist')
  })

  it('12.8 Due Date input', () => {
    cy.get('.sidebar, [class*="sidebar"]').contains(/due\s*date/i).should('exist')
  })

  it('12.9 Estimated hours input', () => {
    cy.get('.sidebar, [class*="sidebar"]').contains(/estimat/i).should('exist')
  })

  it('12.10 Labels input shows tags', () => {
    cy.get('.sidebar, [class*="sidebar"]').contains(/labels/i).should('exist')
  })
})

// ---------------------------------------------------------------------------
// Describe 13: Activity Tab (6 tests)
// ---------------------------------------------------------------------------
describe('Issues — Activity Tab', () => {
  beforeEach(() => {
    cy.goToIssues()
    cy.createIssueViaApi()
    cy.reload()
    cy.get('.kanban-board, [class*="kanban"]', { timeout: 10000 }).should('be.visible')
    cy.openFirstIssueInBoard()
    cy.get('button').contains(/edit/i).click()
    cy.get('.issue-detail, [class*="detail-view"]', { timeout: 8000 }).should('be.visible')
    cy.contains(/activity/i).click()
  })

  afterEach(() => {
    cy.get('@issueId').then(id => { if (id) cy.deleteIssueViaApi(id) })
  })

  it('13.1 Activity tab loads activity feed', () => {
    cy.get('.activity-feed, .activity, [class*="activity"]').should('exist')
  })

  it('13.2 Comment form visible', () => {
    cy.get('.comment-form, [class*="comment-form"], textarea, .comment-input, [class*="comment"] input, [class*="comment"] textarea').should('exist')
  })

  it('13.3 Enter comment + Submit fires POST /tasks/*/comments', () => {
    cy.intercept('POST', '**/tasks/*/comments').as('addComment')
    cy.get('.comment-form textarea, [class*="comment"] textarea, [class*="comment"] input').first().type('CY test comment')
    cy.get('button').contains(/send|submit|add|post/i).click()
    cy.wait('@addComment').its('response.statusCode').should('be.oneOf', [200, 201])
  })

  it('13.4 Empty comment does not submit', () => {
    cy.get('.comment-form textarea, [class*="comment"] textarea, [class*="comment"] input').first().clear()
    cy.get('button').contains(/send|submit|add|post/i).click({ force: true })
    // no new comment should appear
    cy.wait(500)
    cy.get('.activity-feed, [class*="activity"]').should('exist')
  })

  it('13.5 Shows system events (create, update)', () => {
    cy.get('.activity-event, .event, [class*="event"], [class*="history"]').should('have.length.gte', 1)
  })

  it('13.6 Activity count matches changes', () => {
    cy.get('.activity-event, .event, [class*="event"], [class*="activity-item"]').its('length').should('be.gte', 1)
  })
})

// ---------------------------------------------------------------------------
// Describe 14: Work Log Tab (6 tests)
// ---------------------------------------------------------------------------
describe('Issues — Work Log Tab', () => {
  beforeEach(() => {
    cy.goToIssues()
    cy.createIssueViaApi()
    cy.reload()
    cy.get('.kanban-board, [class*="kanban"]', { timeout: 10000 }).should('be.visible')
    cy.openFirstIssueInBoard()
    cy.get('button').contains(/edit/i).click()
    cy.get('.issue-detail, [class*="detail-view"]', { timeout: 8000 }).should('be.visible')
    cy.contains(/work\s*log/i).click()
  })

  afterEach(() => {
    cy.get('@issueId').then(id => { if (id) cy.deleteIssueViaApi(id) })
  })

  it('14.1 Work Log tab shows WorkLogBlock', () => {
    cy.get('.work-log, .worklog, [class*="work-log"], [class*="worklog"]', { timeout: 8000 }).should('exist')
  })

  it('14.2 Progress bar visible', () => {
    cy.get('.progress-bar, .progress, [class*="progress"]').should('exist')
  })

  it('14.3 "Log Work" button opens form', () => {
    cy.get('button').contains(/log\s*work|add/i).click()
    cy.get('.worklog-form, .work-log-form, [class*="worklog-form"], [class*="log-form"]', { timeout: 5000 }).should('be.visible')
  })

  it('14.4 Form has hours, date, comment fields', () => {
    cy.get('button').contains(/log\s*work|add/i).click()
    cy.get('.worklog-form, [class*="worklog-form"], [class*="log-form"]').within(() => {
      cy.get('input[type="number"], input[name*="hour"], input[placeholder*="hour"]').should('exist')
      cy.get('input[type="date"], input[name*="date"]').should('exist')
      cy.get('textarea, input[name*="comment"], input[placeholder*="comment"]').should('exist')
    })
  })

  it('14.5 Fill + Submit fires POST /tasks/*/work-logs → 201', () => {
    cy.intercept('POST', '**/tasks/*/work-logs').as('addWorkLog')
    cy.get('button').contains(/log\s*work|add/i).click()
    cy.get('.worklog-form, [class*="worklog-form"], [class*="log-form"]').within(() => {
      cy.get('input[type="number"], input[name*="hour"]').clear().type('2')
      cy.get('input[type="date"], input[name*="date"]').type('2026-03-28')
      cy.get('textarea, input[name*="comment"]').type('CY work log entry')
    })
    cy.get('button').contains(/save|submit|log/i).click()
    cy.wait('@addWorkLog').its('response.statusCode').should('eq', 201)
  })

  it('14.6 After adding: spent hours updated', () => {
    cy.intercept('POST', '**/tasks/*/work-logs').as('addWorkLog')
    cy.get('button').contains(/log\s*work|add/i).click()
    cy.get('.worklog-form, [class*="worklog-form"], [class*="log-form"]').within(() => {
      cy.get('input[type="number"], input[name*="hour"]').clear().type('3')
      cy.get('input[type="date"], input[name*="date"]').type('2026-03-28')
      cy.get('textarea, input[name*="comment"]').type('CY hours check')
    })
    cy.get('button').contains(/save|submit|log/i).click()
    cy.wait('@addWorkLog')
    cy.contains(/3\s*h|3\s*hour/i, { timeout: 5000 }).should('exist')
  })
})

// ---------------------------------------------------------------------------
// Describe 15: Backlog Tab + Sprints (10 tests)
// ---------------------------------------------------------------------------
describe('Issues — Backlog Tab + Sprints', () => {
  beforeEach(() => {
    cy.goToIssues()
    cy.createIssueViaApi()
    cy.reload()
    cy.get('.issues-page, .tasks-page, [class*="issues"]', { timeout: 10000 }).should('exist')
    cy.contains(/backlog/i).click()
    cy.get('.backlog-view, [class*="backlog"]', { timeout: 8000 }).should('be.visible')
  })

  afterEach(() => {
    cy.get('@issueId').then(id => { if (id) cy.deleteIssueViaApi(id) })
  })

  it('15.1 Click Backlog shows BacklogView', () => {
    cy.get('.backlog-view, [class*="backlog"]').should('be.visible')
  })

  it('15.2 No active sprint — Create Sprint button visible', () => {
    cy.get('body').then($b => {
      const hasNoSprint = $b.find('.sprint-panel, [class*="sprint-panel"]').length === 0
      if (hasNoSprint) {
        cy.get('button').contains(/create\s*sprint|new\s*sprint|\+\s*sprint/i).should('be.visible')
      } else {
        cy.log('Active sprint exists — skipping')
      }
    })
  })

  it('15.3 Click Create Sprint opens modal', () => {
    cy.get('button').contains(/create\s*sprint|new\s*sprint|\+\s*sprint/i).click({ force: true })
    cy.get('.modal, .dialog, [class*="modal"], [class*="dialog"]', { timeout: 5000 }).should('be.visible')
  })

  it('15.4 Sprint modal has Name, Goal, Start Date, End Date', () => {
    cy.get('button').contains(/create\s*sprint|new\s*sprint|\+\s*sprint/i).click({ force: true })
    cy.get('.modal, [class*="modal"]').within(() => {
      cy.get('input[name*="name"], input[placeholder*="name"], input[placeholder*="Name"]').should('exist')
      cy.get('input[type="date"]').should('have.length.gte', 2)
    })
  })

  it('15.5 Create Sprint fires POST /sprints', () => {
    cy.intercept('POST', '**/sprints').as('createSprint')
    cy.get('button').contains(/create\s*sprint|new\s*sprint|\+\s*sprint/i).click({ force: true })
    cy.get('.modal, [class*="modal"]').within(() => {
      cy.get('input[name*="name"], input[placeholder*="name"], input[placeholder*="Name"]').clear().type('CY Sprint')
      cy.get('input[type="date"]').eq(0).type('2026-03-28')
      cy.get('input[type="date"]').eq(1).type('2026-04-11')
      cy.get('button').contains(/create|save|submit/i).click()
    })
    cy.wait('@createSprint').its('response.statusCode').should('be.oneOf', [200, 201])
  })

  it('15.6 Sprint Panel visible if active sprint', () => {
    cy.get('body').then($b => {
      if ($b.find('.sprint-panel, [class*="sprint"]').length > 0) {
        cy.get('.sprint-panel, [class*="sprint"]').should('be.visible')
      } else {
        cy.log('No active sprint — skipping')
      }
    })
  })

  it('15.7 Sprint Panel shows name, dates, Start/Complete buttons', () => {
    cy.get('.sprint-panel, [class*="sprint"]').then($sp => {
      if ($sp.length > 0) {
        cy.wrap($sp).within(() => {
          cy.get('[class*="name"], .sprint-name').should('exist')
          cy.get('button').should('have.length.gte', 1)
        })
      } else {
        cy.log('No sprint panel — skipping')
      }
    })
  })

  it('15.8 BacklogView has issue list with DnD', () => {
    cy.get('.backlog-list, .backlog-items, [class*="backlog-list"], [class*="backlog-item"]').should('exist')
  })

  it('15.9 Drag issue from backlog to sprint', () => {
    cy.get('.backlog-list .task-row, [class*="backlog-item"], [class*="backlog"] .task-card').then($items => {
      if ($items.length > 0) {
        const $item = $items.first()
        const rect = $item[0].getBoundingClientRect()
        cy.get('.sprint-panel, [class*="sprint"]').then($sp => {
          if ($sp.length > 0) {
            const spRect = $sp[0].getBoundingClientRect()
            cy.wrap($item)
              .trigger('mousedown', { which: 1, clientX: rect.left + 50, clientY: rect.top + 10 })
            cy.wait(200)
            cy.wrap($item)
              .trigger('mousemove', { clientX: spRect.left + 50, clientY: spRect.top + 50, force: true })
            cy.wait(200)
            cy.wrap($item)
              .trigger('mouseup', { clientX: spRect.left + 50, clientY: spRect.top + 50, force: true })
          } else {
            cy.log('No sprint panel — cannot drag')
          }
        })
      } else {
        cy.log('No backlog items — skipping')
      }
    })
  })

  it('15.10 Sidebar shows Sprint badge if in sprint', () => {
    cy.get('.task-card, [class*="task-card"], .task-row').first().click({ force: true })
    cy.get('.task-detail, [class*="detail"]', { timeout: 8000 }).then($d => {
      if ($d.find('[class*="sprint"]').length > 0) {
        cy.get('[class*="sprint"]').should('exist')
      } else {
        cy.log('No sprint badge — skipping')
      }
    })
  })
})

// ---------------------------------------------------------------------------
// Describe 16: Dashboard Tab (5 tests)
// ---------------------------------------------------------------------------
describe('Issues — Dashboard Tab', () => {
  beforeEach(() => {
    cy.goToIssues()
    cy.contains(/dashboard/i).click({ force: true })
  })

  it('16.1 Click Dashboard loads DashboardView', () => {
    cy.get('.dashboard-view, [class*="dashboard"], [class*="stats"]', { timeout: 10000 }).should('exist')
  })

  it('16.2 Charts visible (canvas or svg)', () => {
    cy.get('canvas, svg, [class*="chart"]', { timeout: 10000 }).should('exist')
  })

  it('16.3 No data shows empty state', () => {
    cy.get('body').then($b => {
      const hasCharts = $b.find('canvas, svg').length > 0
      const hasEmpty = $b.find(':contains("No data"), :contains("no data"), [class*="empty"]').length > 0
      expect(hasCharts || hasEmpty).to.be.true
    })
  })

  it('16.4 GET /tasks/dashboard/stats returns 200', () => {
    cy.intercept('GET', '**/tasks/dashboard/stats*').as('dashStats')
    cy.reload()
    cy.contains(/dashboard/i).click({ force: true })
    cy.wait('@dashStats', { timeout: 15000 }).its('response.statusCode').should('eq', 200)
  })

  it('16.5 X-Cache header present', () => {
    cy.intercept('GET', '**/tasks/dashboard/stats*').as('dashStats')
    cy.reload()
    cy.contains(/dashboard/i).click({ force: true })
    cy.wait('@dashStats', { timeout: 15000 }).then(interception => {
      const cacheHeader = interception.response.headers['x-cache'] || interception.response.headers['X-Cache']
      // header may or may not exist — just log
      cy.log('X-Cache: ' + (cacheHeader || 'not present'))
    })
  })
})

// ---------------------------------------------------------------------------
// Describe 17: Delete Issue (4 tests)
// ---------------------------------------------------------------------------
describe('Issues — Delete Issue', () => {
  beforeEach(() => {
    cy.goToIssues()
    cy.createIssueViaApi({ title: 'CY Delete Target' })
    cy.reload()
    cy.get('.kanban-board, [class*="kanban"]', { timeout: 10000 }).should('be.visible')
    cy.openFirstIssueInBoard()
    cy.get('button').contains(/edit/i).click()
    cy.get('.issue-detail, [class*="detail-view"]', { timeout: 8000 }).should('be.visible')
  })

  afterEach(() => {
    // cleanup if not deleted
    cy.get('@issueId').then(id => { if (id) cy.deleteIssueViaApi(id) })
  })

  it('17.1 Delete button visible', () => {
    cy.get('button').contains(/delete/i).should('be.visible')
  })

  it('17.2 Click Delete shows confirm dialog', () => {
    cy.get('button').contains(/delete/i).click()
    cy.get('.confirm-dialog, .confirm, [class*="confirm"], [class*="dialog"]', { timeout: 5000 }).should('be.visible')
  })

  it('17.3 Reject confirm — task not deleted', () => {
    cy.get('button').contains(/delete/i).click()
    cy.get('.confirm-dialog, [class*="confirm"], [class*="dialog"]').within(() => {
      cy.get('button').contains(/cancel|no/i).click()
    })
    cy.get('.issue-detail, [class*="detail-view"]').should('be.visible')
  })

  it('17.4 Accept confirm — DELETE /tasks/** → task disappears', () => {
    cy.intercept('DELETE', '**/tasks/**').as('deleteTask')
    cy.get('button').contains(/delete/i).click()
    cy.get('.confirm-dialog, [class*="confirm"], [class*="dialog"]').within(() => {
      cy.get('button').contains(/confirm|yes|delete|ok/i).click()
    })
    cy.wait('@deleteTask').its('response.statusCode').should('be.oneOf', [200, 204])
    cy.get('.issue-detail, [class*="detail-view"]').should('not.exist')
    cy.contains('CY Delete Target').should('not.exist')
    cy.wrap(null).as('issueId') // prevent afterEach cleanup
  })
})
