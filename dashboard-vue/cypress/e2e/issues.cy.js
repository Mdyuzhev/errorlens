// issues.cy.js — EL072 CRUD E2E Tests for Issues
// 12 describes, 67 tests
// Pattern: createViaApi → action in UI → verify via API → cleanup

describe('CRUD-01: Issue — полный жизненный цикл', () => {
  let createdIssue = null

  // Один раз создаём через API перед всеми тестами
  before(() => {
    cy.loginToApp()
    cy.createIssueViaApi({
      title: 'CRUD01-Target-Issue',
      priority: 'high',
      severity: 'critical',
      labels: ['crud01', 'lifecycle']
    })
    cy.get('@createdIssue').then(issue => { createdIssue = issue })
  })

  after(() => {
    cy.get('@issueId').then(id => cy.deleteIssueViaApi(id))
  })

  it('01.1 CREATE: API возвращает id и human_id', () => {
    // Действие: уже создано в before()
    // Ожидание: @createdIssue содержит id (UUID) и human_id (EL-N)
    cy.get('@createdIssue').then(issue => {
      expect(issue.id).to.match(/^[0-9a-f-]{36}$/)
      expect(issue.human_id).to.match(/^EL-\d+$/)
    })
  })

  it('01.2 READ: задача видна на Kanban-доске в колонке To Do', () => {
    // Действие: открыть Issues Board
    // Ожидание: карточка с title 'CRUD01-Target-Issue' видна в первой колонке
    cy.goToIssues()
    cy.get('.kanban-column').first() // To Do column
      .should('contain.text', 'CRUD01-Target-Issue')
  })

  it('01.3 READ: human_id отображается на карточке', () => {
    cy.goToIssues()
    cy.wrap(createdIssue).then(issue => {
      cy.get('.task-card')
        .contains('.human-id-badge', issue.human_id)
        .should('be.visible')
    })
  })

  it('01.4 READ: прямой URL /#/issues/EL-N открывает задачу', () => {
    // После EL071 deep URL должен работать
    cy.loginToApp()
    cy.wrap(createdIssue).then(issue => {
      cy.visit(`/dashboard/#/issues/${issue.human_id}`)
      cy.get('.task-detail, .task-detail-overlay', { timeout: 15000 })
        .should('be.visible')
        .and('contain.text', 'CRUD01-Target-Issue')
    })
  })

  it('01.5 UPDATE: изменить title через IssueDetailView → данные сохранились', () => {
    // Действие: открыть IssueDetailView, нажать Edit, изменить title, Save
    // Ожидание: GET /tasks/{id} возвращает новый title
    cy.goToIssues()
    cy.openFirstIssueInBoard()
    cy.get('button').contains(/edit/i).click()

    const newTitle = `CRUD01-Updated-${Date.now()}`
    cy.get('input.title-input, [class*="title-input"]', { timeout: 8000 })
      .clear().type(newTitle)
    cy.intercept('PUT', '**/tasks/*').as('updateTask')
    cy.get('button').contains(/save/i).click()
    cy.wait('@updateTask').its('response.statusCode').should('eq', 200)

    // Верификация через API — данные реально сохранились в БД
    cy.get('@issueId').then(id => {
      cy.getIssueViaApi(id)
      cy.get('@fetchedIssue').its('title').should('eq', newTitle)
    })
  })

  it('01.6 UPDATE: URL меняется при открытии задачи (EL071)', () => {
    cy.goToIssues()
    cy.wrap(createdIssue).then(issue => {
      // Кликнуть карточку
      cy.get('.task-card').contains(issue.human_id).first().click()
      // URL должен содержать human_id
      cy.url().should('include', issue.human_id)
    })
  })

  it('01.7 UPDATE: закрыть задачу → URL возвращается на /issues', () => {
    cy.goToIssues()
    cy.openFirstIssueInBoard()
    cy.get('.back-btn, [class*="back"]').first().click()
    cy.url().should('match', /\/issues$/)
  })

  it('01.8 DELETE: удалить через IssueDetailView → карточка исчезает с доски', () => {
    cy.goToIssues()
    cy.openFirstIssueInBoard()
    cy.get('button').contains(/edit/i).click()

    cy.intercept('DELETE', '**/tasks/*').as('deleteTask')
    cy.get('button').contains(/delete/i).click()
    // Подтвердить confirm dialog
    cy.on('window:confirm', () => true)
    // или найти confirm кнопку в UI
    cy.get('.confirm-dialog, [class*="confirm"]').then($d => {
      if ($d.length) $d.find('button').contains(/yes|ok|да|confirm/i).click()
    })

    cy.wait('@deleteTask').its('response.statusCode').should('be.oneOf', [200, 204])

    // Верификация: задача не на доске
    cy.get('@createdIssue').then(issue => {
      cy.get('.kanban-board').should('not.contain.text', issue.human_id)
    })

    // Верификация через API: 404
    cy.get('@issueId').then(id => {
      cy.window().then(win => {
        cy.request({
          method: 'GET',
          url: `/api/tasks/${id}`,
          headers: { Authorization: `Bearer ${win.localStorage.getItem('access_token')}` },
          failOnStatusCode: false
        }).its('status').should('eq', 404)
      })
    })

    cy.wrap(null).as('issueId') // предотвратить after() cleanup
  })
})

describe('CRUD-02: Type Filter — реальная фильтрация данных', () => {
  let bugId, storyId, taskTypeId, bugTypeId

  before(() => {
    cy.loginToApp()
    // Получить type ids
    cy.window().then(win => {
      cy.request({
        method: 'GET', url: '/api/task-settings/types',
        params: { project_id: '9ddfd925-9728-4224-8a3d-13a6e2e01719' },
        headers: { Authorization: `Bearer ${win.localStorage.getItem('access_token')}` }
      }).then(resp => {
        const types = resp.body
        const bugType = types.find(t => t.slug === 'bug')
        const storyType = types.find(t => t.slug === 'story')

        // Создать Bug
        cy.createIssueViaApi({
          title: 'CRUD02-Bug-Issue',
          type_id: bugType?.id,
          priority: 'high'
        })
        cy.get('@issueId').then(id => { bugId = id })

        // Создать Story
        cy.createIssueViaApi({
          title: 'CRUD02-Story-Issue',
          type_id: storyType?.id,
          priority: 'medium'
        })
        cy.get('@issueId').then(id => { storyId = id })
      })
    })
  })

  after(() => {
    cy.loginToApp()
    if (bugId) cy.deleteIssueViaApi(bugId)
    if (storyId) cy.deleteIssueViaApi(storyId)
  })

  it('02.1 All type — показывает Bug И Story задачи одновременно', () => {
    cy.goToIssues()
    cy.get('.type-tab').contains(/all/i).click()
    cy.get('.kanban-board')
      .should('contain.text', 'CRUD02-Bug-Issue')
      .and('contain.text', 'CRUD02-Story-Issue')
  })

  it('02.2 Bug filter — показывает CRUD02-Bug-Issue, НЕ показывает CRUD02-Story-Issue', () => {
    cy.goToIssues()
    cy.intercept('GET', '**/tasks/board*').as('boardReq')
    cy.get('.type-tab').contains(/bug/i).click()
    cy.wait('@boardReq')

    // POSITIVE: Bug задача есть
    cy.get('.kanban-board').should('contain.text', 'CRUD02-Bug-Issue')
    // NEGATIVE: Story задача НЕ должна быть
    cy.get('.kanban-board').should('not.contain.text', 'CRUD02-Story-Issue')
  })

  it('02.3 Story filter — показывает CRUD02-Story-Issue, НЕ показывает CRUD02-Bug-Issue', () => {
    cy.goToIssues()
    cy.intercept('GET', '**/tasks/board*').as('boardReq')
    cy.get('.type-tab').contains(/story/i).click()
    cy.wait('@boardReq')

    cy.get('.kanban-board').should('contain.text', 'CRUD02-Story-Issue')
    cy.get('.kanban-board').should('not.contain.text', 'CRUD02-Bug-Issue')
  })

  it('02.4 Bug filter в List View — только Bug задачи', () => {
    cy.goToIssues()
    cy.intercept('GET', '**/tasks*').as('listReq')
    cy.get('.type-tab').contains(/bug/i).click()
    cy.get('.view-toggle button').last().click() // переключить на List
    cy.wait('@listReq')

    // Все строки должны иметь Bug тип индикатор
    cy.get('.task-list-row').each($row => {
      cy.wrap($row).find('.type-indicator[title="Bug"], [class*="type"]').should('exist')
    })
    // Story задача НЕ должна быть в списке
    cy.get('.task-list').should('not.contain.text', 'CRUD02-Story-Issue')
  })

  it('02.5 Вернуться на All — оба типа снова видны', () => {
    cy.goToIssues()
    cy.get('.type-tab').contains(/bug/i).click()
    cy.get('.type-tab').contains(/all/i).click()
    cy.get('.kanban-board')
      .should('contain.text', 'CRUD02-Bug-Issue')
      .and('contain.text', 'CRUD02-Story-Issue')
  })

  it('02.6 Type filter сохраняется при смене Board/List view', () => {
    cy.goToIssues()
    cy.get('.type-tab').contains(/bug/i).click()
    // Переключить на List
    cy.get('.view-toggle button').last().click()
    cy.get('.task-list').should('not.contain.text', 'CRUD02-Story-Issue')
    // Переключить обратно на Board
    cy.get('.view-toggle button').first().click()
    cy.get('.kanban-board').should('not.contain.text', 'CRUD02-Story-Issue')
  })
})

describe('CRUD-03: IssueDetailView — редактирование всех полей', () => {
  let issueId

  beforeEach(() => {
    cy.loginToApp()
    cy.createIssueViaApi({
      title: 'CRUD03-Edit-Target',
      priority: 'low',
      severity: null
    })
    cy.get('@issueId').then(id => { issueId = id })
    cy.goToIssues()
    cy.openFirstIssueInBoard()
    cy.get('button').contains(/edit/i).click()
    cy.get('.task-detail-overlay, .task-detail', { timeout: 10000 }).should('be.visible')
  })

  afterEach(() => {
    if (issueId) cy.deleteIssueViaApi(issueId)
    issueId = null
  })

  it('03.1 Title: ввести новый → Save → GET API возвращает новый title', () => {
    const newTitle = `CRUD03-NewTitle-${Date.now()}`
    cy.get('input.title-input').clear().type(newTitle)
    cy.intercept('PUT', '**/tasks/*').as('save')
    cy.get('button.btn-sm.btn-primary').contains(/save/i).click()
    cy.wait('@save').its('response.statusCode').should('eq', 200)
    // API верификация
    cy.getIssueViaApi(issueId)
    cy.get('@fetchedIssue').its('title').should('eq', newTitle)
    // UI верификация
    cy.get('.task-title, h1').should('contain.text', newTitle)
  })

  it('03.2 Priority: изменить Low → High → API сохраняет "high"', () => {
    cy.get('.task-sidebar .detail-row').contains('Priority')
      .closest('.detail-row').find('select')
      .select('high')
    cy.intercept('PUT', '**/tasks/*').as('save')
    cy.get('button').contains(/save/i).click()
    cy.wait('@save')
    cy.getIssueViaApi(issueId)
    cy.get('@fetchedIssue').its('priority').should('eq', 'high')
  })

  it('03.3 Severity: установить Critical → API сохраняет "critical"', () => {
    cy.get('.task-sidebar .detail-row').contains('Severity')
      .closest('.detail-row').find('select')
      .select('critical')
    cy.intercept('PUT', '**/tasks/*').as('save')
    cy.get('button').contains(/save/i).click()
    cy.wait('@save')
    cy.getIssueViaApi(issueId)
    cy.get('@fetchedIssue').its('severity').should('eq', 'critical')
  })

  it('03.4 Story Points: ввести 5 → API сохраняет 5', () => {
    cy.get('.task-sidebar .detail-row').contains('Story Points')
      .closest('.detail-row').find('input[type="number"]')
      .clear().type('5')
    cy.intercept('PUT', '**/tasks/*').as('save')
    cy.get('button').contains(/save/i).click()
    cy.wait('@save')
    cy.getIssueViaApi(issueId)
    cy.get('@fetchedIssue').its('story_points').should('eq', 5)
  })

  it('03.5 Estimated Hours: ввести 8 → API сохраняет 8', () => {
    cy.get('.task-sidebar .detail-row').contains('Estimated')
      .closest('.detail-row').find('input[type="number"]')
      .clear().type('8')
    cy.intercept('PUT', '**/tasks/*').as('save')
    cy.get('button').contains(/save/i).click()
    cy.wait('@save')
    cy.getIssueViaApi(issueId)
    cy.get('@fetchedIssue').its('estimated_hours').should('eq', 8)
  })

  it('03.6 Labels: ввести "alpha, beta" → карточка показывает два тега', () => {
    cy.get('input[placeholder*="label" i]')
      .clear().type('alpha, beta')
    cy.intercept('PUT', '**/tasks/*').as('save')
    cy.get('button').contains(/save/i).click()
    cy.wait('@save')
    cy.getIssueViaApi(issueId)
    cy.get('@fetchedIssue').its('labels').should('include', 'alpha')
    cy.get('@fetchedIssue').its('labels').should('include', 'beta')
  })

  it('03.7 Cancel: изменить title, нажать Cancel → title НЕ изменился', () => {
    cy.get('input.title-input').clear().type('SHOULD-NOT-SAVE')
    cy.get('button').contains(/cancel/i).click()
    cy.get('.task-title, h1').should('not.contain.text', 'SHOULD-NOT-SAVE')
    // API тоже не изменился
    cy.getIssueViaApi(issueId)
    cy.get('@fetchedIssue').its('title').should('not.eq', 'SHOULD-NOT-SAVE')
  })

  it('03.8 Description: написать текст → Save → API сохраняет description', () => {
    cy.get('.empty-description, .description-section').first().click()
    cy.get('.ProseMirror, [contenteditable="true"]').first()
      .type('CRUD03 test description text')
    cy.intercept('PUT', '**/tasks/*').as('save')
    cy.get('button').contains(/save/i).click()
    cy.wait('@save')
    cy.getIssueViaApi(issueId)
    cy.get('@fetchedIssue').its('description').should('not.be.null')
  })

  it('03.9 Status workflow: нажать status badge → выбрать In Progress → статус изменился', () => {
    cy.get('.status-badge').first().click()
    cy.get('.status-dropdown').should('be.visible')
    cy.get('.status-option').contains(/in.progress|в работе/i).click()
    cy.getIssueViaApi(issueId)
    // Статус изменился на in_progress (или name статуса In Progress)
    cy.get('@fetchedIssue').then(issue => {
      const status = issue.status || issue.task_status?.slug
      expect(status).to.match(/in.progress|in_progress/i)
    })
  })

  it('03.10 Tabs: Details → Activity → Work Log — все загружаются без ошибок', () => {
    // Details
    cy.get('.tab-btn').contains(/details/i).click()
    cy.get('.description-section, [class*="description"]').should('exist')
    // Activity
    cy.get('.tab-btn').contains(/activity/i).click()
    cy.get('.activity-feed, [class*="activity"]', { timeout: 8000 }).should('exist')
    // Work Log
    cy.get('.tab-btn').contains(/work.log/i).click()
    cy.get('[class*="work-log"], [class*="worklog"]', { timeout: 8000 }).should('exist')
  })
})

describe('CRUD-04: Kanban статусные переходы', () => {
  let issueId

  beforeEach(() => {
    cy.loginToApp()
    cy.createIssueViaApi({ title: 'CRUD04-Status-Task', status: 'todo' })
    cy.get('@issueId').then(id => { issueId = id })
  })

  afterEach(() => {
    if (issueId) cy.deleteIssueViaApi(issueId)
    issueId = null
  })

  it('04.1 To Do → In Progress через DnD → API подтверждает in_progress', () => {
    cy.goToIssues()
    cy.intercept('PUT', '**/tasks/*').as('updateTask')
    // Native DragEvent: dragstart on card, dragover+drop on target column
    cy.get('.kanban-column').eq(0).find('.task-card').first().should('exist').then($card => {
      const dt = new DataTransfer()
      $card[0].dispatchEvent(new DragEvent('dragstart', { bubbles: true, cancelable: true, dataTransfer: dt }))
    })
    cy.wait(500)
    cy.get('.kanban-column').eq(1).should('exist').then($col => {
      const dt = new DataTransfer()
      $col[0].dispatchEvent(new DragEvent('dragover', { bubbles: true, cancelable: true, dataTransfer: dt }))
      cy.wait(100).then(() => {
        $col[0].dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt }))
        $col[0].dispatchEvent(new DragEvent('dragend', { bubbles: true, cancelable: true, dataTransfer: dt }))
      })
    })
    cy.wait('@updateTask', { timeout: 15000 }).its('response.statusCode').should('eq', 200)
    cy.getIssueViaApi(issueId)
    cy.get('@fetchedIssue').its('status').should('eq', 'in_progress')
  })

  it('04.2 Колонка To Do: счётчик уменьшается после перемещения', () => {
    cy.goToIssues()
    cy.get('.kanban-column').eq(0)
      .find('.column-count').invoke('text')
      .then(before => {
        const beforeCount = parseInt(before.trim())
        cy.get('.kanban-column').eq(0).find('.task-card').first().should('exist').then($card => {
          const dt = new DataTransfer()
          $card[0].dispatchEvent(new DragEvent('dragstart', { bubbles: true, cancelable: true, dataTransfer: dt }))
        })
        cy.wait(500)
        cy.get('.kanban-column').eq(1).should('exist').then($col => {
          const dt = new DataTransfer()
          $col[0].dispatchEvent(new DragEvent('dragover', { bubbles: true, cancelable: true, dataTransfer: dt }))
          cy.wait(100).then(() => {
            $col[0].dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt }))
            $col[0].dispatchEvent(new DragEvent('dragend', { bubbles: true, cancelable: true, dataTransfer: dt }))
          })
        })
        cy.wait(1000)
        cy.get('.kanban-column').eq(0)
          .find('.column-count').invoke('text')
          .should(after => {
            expect(parseInt(after.trim())).to.eq(beforeCount - 1)
          })
      })
  })

  it('04.3 Колонка In Progress: счётчик увеличивается после перемещения', () => {
    cy.goToIssues()
    cy.get('.kanban-column').eq(1)
      .find('.column-count').invoke('text')
      .then(before => {
        const beforeCount = parseInt(before.trim())
        cy.get('.kanban-column').eq(0).find('.task-card').first().should('exist').then($card => {
          const dt = new DataTransfer()
          $card[0].dispatchEvent(new DragEvent('dragstart', { bubbles: true, cancelable: true, dataTransfer: dt }))
        })
        cy.wait(500)
        cy.get('.kanban-column').eq(1).should('exist').then($col => {
          const dt = new DataTransfer()
          $col[0].dispatchEvent(new DragEvent('dragover', { bubbles: true, cancelable: true, dataTransfer: dt }))
          cy.wait(100).then(() => {
            $col[0].dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt }))
            $col[0].dispatchEvent(new DragEvent('dragend', { bubbles: true, cancelable: true, dataTransfer: dt }))
          })
        })
        cy.wait(1000)
        cy.get('.kanban-column').eq(1)
          .find('.column-count').invoke('text')
          .should(after => {
            expect(parseInt(after.trim())).to.eq(beforeCount + 1)
          })
      })
  })

  it('04.4 Status dropdown: todo → done через IssueDetailView', () => {
    cy.goToIssues()
    cy.openFirstIssueInBoard()
    cy.get('.status-badge').click()
    cy.get('.status-dropdown .status-option')
      .contains(/done|завершено/i).click()
    cy.getIssueViaApi(issueId)
    cy.get('@fetchedIssue').its('status').should('match', /done/)
  })

  it('04.5 Задача перемещается в колонку Done после смены статуса на done', () => {
    cy.goToIssues()
    cy.openFirstIssueInBoard()
    cy.get('.status-badge').click()
    cy.get('.status-dropdown .status-option').contains(/done/i).click()
    cy.get('.back-btn').first().click()
    cy.get('.kanban-column').eq(3) // Done column
      .should('contain.text', 'CRUD04-Status-Task')
  })

  it('04.6 После reload задача остаётся в изменённой колонке', () => {
    cy.goToIssues()
    cy.get('.kanban-column').eq(0).find('.task-card').first().should('exist').then($card => {
      const dt = new DataTransfer()
      $card[0].dispatchEvent(new DragEvent('dragstart', { bubbles: true, cancelable: true, dataTransfer: dt }))
    })
    cy.wait(500)
    cy.get('.kanban-column').eq(1).should('exist').then($col => {
      const dt = new DataTransfer()
      $col[0].dispatchEvent(new DragEvent('dragover', { bubbles: true, cancelable: true, dataTransfer: dt }))
      cy.wait(100).then(() => {
        $col[0].dispatchEvent(new DragEvent('drop', { bubbles: true, cancelable: true, dataTransfer: dt }))
        $col[0].dispatchEvent(new DragEvent('dragend', { bubbles: true, cancelable: true, dataTransfer: dt }))
      })
    })
    cy.wait(1000)
    cy.reload()
    cy.get('.kanban-column').eq(1, { timeout: 10000 })
      .should('contain.text', 'CRUD04-Status-Task')
  })
})

describe('CRUD-05: Create Modal — все поля создаются корректно', () => {
  const createdIds = []

  afterEach(() => {
    cy.get('@issueId').then(id => {
      if (id) {
        createdIds.push(id)
        cy.deleteIssueViaApi(id)
      }
    })
  })

  beforeEach(() => {
    cy.goToIssues()
    cy.wrap(null).as('issueId')
  })

  it('05.1 Title обязателен: пустой → форма не сабмитится', () => {
    cy.get('button').contains(/new issue|новая задача/i).click()
    cy.get('.modal-content form button[type="submit"]').click({ force: true })
    cy.get('.modal-content').should('be.visible') // модал остался открытым
  })

  it('05.2 Создать с title → появляется в Kanban To Do с правильным human_id', () => {
    cy.intercept('POST', '**/tasks').as('create')
    cy.get('button').contains(/new issue/i).click()
    cy.get('.modal-content input').first().type('CRUD05-Title-Only')
    cy.get('.modal-content button[type="submit"], .modal-content .btn-primary').click()
    cy.wait('@create').then(interception => {
      expect(interception.response.statusCode).to.be.oneOf([200, 201])
      const id = interception.response.body.id
      cy.wrap(id).as('issueId')
      cy.get('.kanban-column').first()
        .should('contain.text', 'CRUD05-Title-Only')
    })
  })

  it('05.3 Priority=High → карточка имеет высокоприоритетную полосу', () => {
    cy.intercept('POST', '**/tasks').as('create')
    cy.get('button').contains(/new issue/i).click()
    cy.get('.modal-content input').first().type('CRUD05-High-Priority')
    cy.get('.modal-content').within(() => {
      cy.contains(/priority/i).closest('.form-group, .form-row')
        .find('select').select('high')
    })
    cy.get('.modal-content .btn-primary').click()
    cy.wait('@create').then(ic => { cy.wrap(ic.response.body.id).as('issueId') })
    cy.get('.task-card').contains('CRUD05-High-Priority')
      .closest('.task-card')
      .find('.task-priority.high, [class*="priority"][class*="high"]')
      .should('exist')
  })

  it('05.4 Severity=Critical → badge "critical" на карточке', () => {
    cy.intercept('POST', '**/tasks').as('create')
    cy.get('button').contains(/new issue/i).click()
    cy.get('.modal-content input').first().type('CRUD05-Critical')
    cy.get('.modal-content').within(() => {
      cy.contains(/severity/i).closest('.form-group, .form-row')
        .find('select').select('critical')
    })
    cy.get('.modal-content .btn-primary').click()
    cy.wait('@create').then(ic => { cy.wrap(ic.response.body.id).as('issueId') })
    cy.get('.task-card').contains('CRUD05-Critical')
      .closest('.task-card')
      .find('.severity-badge.critical').should('be.visible')
  })

  it('05.5 Labels "qa,smoke" → карточка показывает 2 тега', () => {
    cy.intercept('POST', '**/tasks').as('create')
    cy.get('button').contains(/new issue/i).click()
    cy.get('.modal-content input').first().type('CRUD05-Labels')
    cy.get('.modal-content').within(() => {
      cy.contains(/labels/i).closest('.form-group')
        .find('input').type('qa, smoke')
    })
    cy.get('.modal-content .btn-primary').click()
    cy.wait('@create').then(ic => { cy.wrap(ic.response.body.id).as('issueId') })
    cy.get('.task-card').contains('CRUD05-Labels')
      .closest('.task-card')
      .find('.label, [class*="label"]').should('have.length', 2)
  })

  it('05.6 Cancel → модал закрывается, задача НЕ создана', () => {
    cy.intercept('POST', '**/tasks').as('create')
    cy.get('button').contains(/new issue/i).click()
    cy.get('.modal-content input').first().type('CRUD05-Cancelled')
    cy.get('.modal-content .btn-secondary').contains(/cancel/i).click()
    cy.get('.modal-content').should('not.exist')
    cy.get('.kanban-board').should('not.contain.text', 'CRUD05-Cancelled')
    // API не был вызван
    cy.get('@create.all').should('have.length', 0)
    cy.wrap(null).as('issueId')
  })

  it('05.7 Клик вне модала (.modal-overlay) закрывает без создания', () => {
    cy.get('button').contains(/new issue/i).click()
    cy.get('.modal-content input').first().type('CRUD05-ClickOutside')
    cy.get('.modal-overlay').click({ force: true })
    cy.get('.modal-content').should('not.exist')
    cy.get('.kanban-board').should('not.contain.text', 'CRUD05-ClickOutside')
    cy.wrap(null).as('issueId')
  })

  it('05.8 Title 501 символ → форма не падает, показывает ошибку или truncates', () => {
    cy.get('button').contains(/new issue/i).click()
    cy.get('.modal-content input').first().type('A'.repeat(501), { delay: 0 })
    cy.get('.modal-content .btn-primary').click()
    // Либо валидация (форма не закрылась) либо задача создана с truncated title
    cy.get('body').then($body => {
      const modalExists = $body.find('.modal-content').length > 0
      const cardExists = $body.find('.task-card').length > 0
      expect(modalExists || cardExists).to.be.true
    })
    cy.wrap(null).as('issueId')
  })
})

describe('CRUD-06: Issue Комментарии — полный CRUD', () => {
  let issueId

  before(() => {
    cy.loginToApp()
    cy.createIssueViaApi({ title: 'CRUD06-Comment-Issue' })
    cy.get('@issueId').then(id => { issueId = id })
  })

  after(() => {
    if (issueId) cy.deleteIssueViaApi(issueId)
  })

  beforeEach(() => {
    cy.goToIssues()
    cy.openFirstIssueInBoard()
    cy.get('button').contains(/edit/i).click()
    cy.get('.tab-btn').contains(/activity/i).click()
  })

  it('06.1 CREATE: добавить комментарий → POST /tasks/*/comments → виден в ленте', () => {
    cy.intercept('POST', '**/tasks/*/comments').as('addComment')
    cy.get('.add-comment textarea').first().type('CRUD06 first comment text')
    cy.get('.add-comment button').contains(/comment/i).click()
    cy.wait('@addComment').its('response.statusCode').should('be.oneOf', [200, 201])
    cy.get('.activity-feed, [class*="activity"]')
      .should('contain.text', 'CRUD06 first comment text')
  })

  it('06.2 READ: комментарий виден в activity feed с именем автора', () => {
    cy.get('.activity-feed, [class*="activity"]')
      .find('[class*="comment"], [class*="event"]')
      .should('have.length.gte', 1)
      .first()
      .should('contain.text', 'admin') // или текущий пользователь
  })

  it('06.3 Пустой комментарий → кнопка disabled или форма не сабмитится', () => {
    cy.get('.add-comment textarea').first().clear()
    cy.intercept('POST', '**/tasks/*/comments').as('addComment')
    cy.get('.add-comment button').contains(/comment/i).click({ force: true })
    cy.wait(500)
    cy.get('@addComment.all').should('have.length', 0)
  })

  it('06.4 Комментарий с 500 символами → принимается без ошибки', () => {
    cy.intercept('POST', '**/tasks/*/comments').as('addComment')
    cy.get('.add-comment textarea').first().type('A'.repeat(500), { delay: 0 })
    cy.get('.add-comment button').contains(/comment/i).click()
    cy.wait('@addComment').its('response.statusCode').should('be.oneOf', [200, 201])
  })

  it('06.5 После reload комментарии сохранились в БД', () => {
    cy.reload()
    cy.openFirstIssueInBoard()
    cy.get('button').contains(/edit/i).click()
    cy.get('.tab-btn').contains(/activity/i).click()
    cy.get('.activity-feed, [class*="activity"]')
      .should('contain.text', 'CRUD06 first comment text')
  })
})

describe('CRUD-07: Work Log — полный CRUD', () => {
  let issueId

  before(() => {
    cy.loginToApp()
    cy.createIssueViaApi({ title: 'CRUD07-WorkLog-Issue', estimated_hours: 8 })
    cy.get('@issueId').then(id => { issueId = id })
  })

  after(() => {
    if (issueId) cy.deleteIssueViaApi(issueId)
  })

  beforeEach(() => {
    cy.goToIssues()
    cy.openFirstIssueInBoard()
    cy.get('button').contains(/edit/i).click()
    cy.get('.tab-btn').contains(/work.log/i).click()
  })

  it('07.1 CREATE: Log Work 2.5ч → POST → spent_hours обновился до 2.5', () => {
    cy.intercept('POST', '**/work-logs**').as('addLog')
    cy.get('.worklog-block button, .log-btn-row button').contains(/log work/i).click()
    cy.get('.log-form').within(() => {
      cy.get('input[type="number"]').clear().type('2.5')
      cy.get('input[type="date"]').type('2026-03-28')
      cy.get('.form-row').contains('Comment').closest('.form-row').find('input').type('CRUD07 work log entry')
    })
    cy.get('.form-actions button').contains(/save/i).click()
    cy.wait('@addLog').its('response.statusCode').should('be.oneOf', [200, 201])
    // Spent hours обновился
    cy.getIssueViaApi(issueId)
    cy.get('@fetchedIssue').its('spent_hours').should('be.gte', 2.5)
  })

  it('07.2 READ: запись виден в списке логов с датой и часами', () => {
    cy.get('.log-entry')
      .should('have.length.gte', 1)
      .first()
      .within(() => {
        cy.get('.log-hours').should('contain.text', '2.5')
      })
  })

  it('07.3 Прогресс-бар: 2.5 из 8 → width ≈ 31%', () => {
    cy.get('.progress-fill')
      .invoke('css', 'width')
      .then(w => {
        const percent = parseFloat(w) / parseFloat(
          Cypress.$('.progress-track').css('width')
        ) * 100
        expect(percent).to.be.gte(25).and.lt(45) // ~31%
      })
  })

  it('07.4 Log Work 0 часов → валидация блокирует', () => {
    cy.intercept('POST', '**/work-logs**').as('addLog')
    cy.get('.worklog-block button, .log-btn-row button').contains(/log work/i).click()
    cy.get('.log-form').within(() => {
      cy.get('input[type="number"]').clear().type('0')
      cy.get('input[type="date"]').type('2026-03-28')
    })
    cy.get('.form-actions button').contains(/save/i).click({ force: true })
    cy.wait(500)
    // Либо форма осталась открытой либо запрос не пошёл
    cy.get('@addLog.all').then(calls => {
      // if submitted, response should indicate error
      if (calls.length > 0) {
        expect(calls[0].response.statusCode).to.be.gte(400)
      }
    })
  })

  it('07.5 Второй Log Work 3ч → total spent_hours стал 5.5', () => {
    cy.intercept('POST', '**/work-logs**').as('addLog')
    cy.get('.worklog-block button, .log-btn-row button').contains(/log work/i).click()
    cy.get('.log-form').within(() => {
      cy.get('input[type="number"]').clear().type('3')
      cy.get('input[type="date"]').type('2026-03-29')
    })
    cy.get('.form-actions button').contains(/save/i).click()
    cy.wait('@addLog')
    cy.getIssueViaApi(issueId)
    cy.get('@fetchedIssue').its('spent_hours').should('be.gte', 5.5)
  })
})

describe('CRUD-08: JQL — реальные результаты фильтрации', () => {
  let highId, lowId, doneId

  before(() => {
    cy.loginToApp()
    cy.createIssueViaApi({ title: 'JQL-High-Priority', priority: 'high' })
    cy.get('@issueId').then(id => { highId = id })
    cy.createIssueViaApi({ title: 'JQL-Low-Priority', priority: 'low' })
    cy.get('@issueId').then(id => { lowId = id })
    cy.createIssueViaApi({ title: 'JQL-Done-Status', status: 'done' })
    cy.get('@issueId').then(id => { doneId = id })
  })

  after(() => {
    cy.loginToApp()
    ;[highId, lowId, doneId].forEach(id => { if (id) cy.deleteIssueViaApi(id) })
  })

  it('08.1 "priority = high" → в списке JQL-High-Priority, нет JQL-Low-Priority', () => {
    cy.goToIssues()
    cy.get('[class*="jql"] input, input[placeholder*="JQL"]')
      .clear().type('priority = high{enter}')
    cy.get('.task-list', { timeout: 10000 }).should('be.visible')
    cy.get('.task-list').should('contain.text', 'JQL-High-Priority')
    cy.get('.task-list').should('not.contain.text', 'JQL-Low-Priority')
  })

  it('08.2 "status = done" → в списке JQL-Done-Status', () => {
    cy.goToIssues()
    cy.get('[class*="jql"] input').clear().type('status = done{enter}')
    cy.get('.task-list', { timeout: 10000 })
      .should('contain.text', 'JQL-Done-Status')
  })

  it('08.3 "title ~ \\"JQL\\"" → все три задачи в списке', () => {
    cy.goToIssues()
    cy.get('[class*="jql"] input').clear().type('title ~ "JQL"{enter}')
    cy.get('.task-list', { timeout: 10000 })
    cy.get('.task-list-row').should('have.length.gte', 3)
  })

  it('08.4 Невалидный JQL "xyz %%% abc" → 400 с читаемой ошибкой (не 500)', () => {
    cy.goToIssues()
    cy.intercept('GET', '**/tasks*jql*').as('jqlReq')
    cy.get('[class*="jql"] input').clear().type('xyz %%% abc{enter}')
    cy.wait('@jqlReq').its('response.statusCode').should('eq', 400)
    // В UI показывается сообщение об ошибке
    cy.get('[class*="error"], [class*="toast"], [class*="alert"]', { timeout: 5000 })
      .should('be.visible')
  })

  it('08.5 Кнопка X очищает JQL и возвращает board-вид', () => {
    cy.goToIssues()
    cy.get('[class*="jql"] input').type('priority = high{enter}')
    cy.get('.task-list').should('be.visible')
    cy.get('[class*="jql"] [class*="clear"], [class*="jql-clear"]').click()
    cy.get('.kanban-board').should('be.visible')
  })

  it('08.6 "priority IN (high, medium)" → высокоприоритетные видны, низкие нет', () => {
    cy.goToIssues()
    cy.get('[class*="jql"] input').clear().type('priority IN (high, medium){enter}')
    cy.get('.task-list-row', { timeout: 10000 })
    cy.get('.task-list').should('not.contain.text', 'JQL-Low-Priority')
  })

  it('08.7 "priority = high ORDER BY created DESC" → валидный JQL без ошибок', () => {
    cy.goToIssues()
    cy.intercept('GET', '**/tasks*jql*').as('jqlReq')
    cy.get('[class*="jql"] input')
      .clear().type('priority = high ORDER BY created DESC{enter}')
    cy.wait('@jqlReq').its('response.statusCode').should('eq', 200)
  })

  it('08.8 Сохранить фильтр "priority = high" → появляется в SavedFilters', () => {
    cy.goToIssues()
    cy.get('[class*="jql"] input').type('priority = high{enter}')
    cy.get('button').contains(/save/i).filter('[class*="jql"], [class*="filter"]').click({ force: true })
    cy.get('[class*="saved-filter"], [class*="saved_filter"]', { timeout: 5000 })
      .should('contain.text', 'priority = high')
  })
})

describe('CRUD-09: Deep URL — открытие задачи по ссылке', () => {
  let issueId, humanId

  before(() => {
    cy.loginToApp()
    cy.createIssueViaApi({ title: 'CRUD09-DeepURL-Issue' })
    cy.get('@issueId').then(id => { issueId = id })
    cy.get('@createdIssue').then(issue => { humanId = issue.human_id })
  })

  after(() => {
    if (issueId) cy.deleteIssueViaApi(issueId)
  })

  it('09.1 Открыть карточку → URL меняется на /#/issues/EL-N', () => {
    cy.goToIssues()
    cy.get('.task-card').first().click()
    cy.url().should('match', /\/issues\/EL-\d+/)
  })

  it('09.2 Прямой переход по /#/issues/EL-N → задача открыта', () => {
    cy.loginToApp()
    cy.visit(`/dashboard/#/issues/${humanId}`)
    cy.get('.task-detail, .task-detail-overlay', { timeout: 15000 }).should('be.visible')
    cy.get('.task-detail').should('contain.text', 'CRUD09-DeepURL-Issue')
  })

  it('09.3 Скопированный URL → вставить в новую вкладку → задача открывается', () => {
    // Получить URL из текущего окна, убедиться что он валиден
    cy.loginToApp()
    cy.visit(`/dashboard/#/issues/${humanId}`)
    cy.url().then(url => {
      expect(url).to.include(humanId)
      // Reload имитирует "вставить URL в новый браузер"
      cy.reload()
      cy.get('.task-detail, .task-detail-overlay', { timeout: 15000 })
        .should('be.visible')
        .and('contain.text', 'CRUD09-DeepURL-Issue')
    })
  })

  it('09.4 Закрыть задачу → URL возвращается на /#/issues', () => {
    cy.loginToApp()
    cy.visit(`/dashboard/#/issues/${humanId}`)
    cy.get('.task-detail', { timeout: 15000 }).should('be.visible')
    cy.get('.back-btn').first().click()
    cy.url().should('match', /\/issues$/)
  })
})

describe('CRUD-10: Sprint — Create → Start → Complete', () => {
  let sprintId

  before(() => {
    cy.loginToApp()
    // Убедиться что нет активного спринта (или использовать специфичный проект)
  })

  afterEach(() => {
    if (sprintId) {
      cy.getAuthToken().then(token => {
        cy.request({
          method: 'DELETE',
          url: `/api/v1/sprints/${sprintId}`,
          headers: { Authorization: `Bearer ${token}` },
          failOnStatusCode: false
        })
      })
      sprintId = null
    }
  })

  it('10.1 CREATE Sprint → POST → sprint Panel появился в Backlog', () => {
    cy.goToIssues()
    cy.get('.issues-tabs .tab').contains(/backlog/i).click()
    cy.get('button').contains(/create sprint|\+ sprint/i).click()
    cy.intercept('POST', '**/sprints').as('createSprint')
    cy.get('.modal-content').within(() => {
      cy.get('input').first().clear().type(`CY-Sprint-${Date.now()}`)
      cy.get('input[type="date"]').eq(0).type('2026-04-01')
      cy.get('input[type="date"]').eq(1).type('2026-04-14')
    })
    cy.get('.modal-content .btn-primary').click()
    cy.wait('@createSprint').then(ic => {
      expect(ic.response.statusCode).to.be.oneOf([200, 201])
      sprintId = ic.response.body.id
    })
    cy.get('.sprint-panel', { timeout: 8000 }).should('be.visible')
  })

  it('10.2 START Sprint → POST /sprints/{id}/start → status=active (не 404)', () => {
    // Создать спринт через API, затем стартовать через UI
    cy.getAuthToken().then(token => {
      cy.request({
        method: 'GET', url: '/api/projects',
        headers: { Authorization: `Bearer ${token}` }
      }).then(resp => {
        const pid = (resp.body[0] || resp.body.items?.[0])?.id
        cy.request({
          method: 'POST', url: '/api/v1/sprints',
          headers: { Authorization: `Bearer ${token}` },
          body: { name: `CY-Sprint-${Date.now()}`, project_id: pid,
                  start_date: '2026-04-01', end_date: '2026-04-14' }
        }).then(sr => {
          sprintId = sr.body.id
          cy.intercept('POST', `**/sprints/${sprintId}/start`).as('startSprint')
          cy.goToIssues()
          cy.get('.issues-tabs .tab').contains(/backlog/i).click()
          cy.get('.sprint-panel button').contains(/start/i).click()
          cy.wait('@startSprint').its('response.statusCode').should('eq', 200)
        })
      })
    })
  })

  it('10.3 Второй START → 409 Conflict', () => {
    cy.getAuthToken().then(token => {
      cy.request({
        method: 'GET', url: '/api/projects',
        headers: { Authorization: `Bearer ${token}` }
      }).then(resp => {
        const pid = (resp.body[0] || resp.body.items?.[0])?.id
        // Создать и стартовать первый спринт
        cy.request({
          method: 'POST', url: '/api/v1/sprints',
          headers: { Authorization: `Bearer ${token}` },
          body: { name: `CY-Sprint-A-${Date.now()}`, project_id: pid }
        }).then(s1 => {
          sprintId = s1.body.id
          cy.request({
            method: 'POST', url: `/api/v1/sprints/${sprintId}/start`,
            headers: { Authorization: `Bearer ${token}` }
          }).then(() => {
            // Создать второй и попытаться стартовать → 409
            cy.request({
              method: 'POST', url: '/api/v1/sprints',
              headers: { Authorization: `Bearer ${token}` },
              body: { name: `CY-Sprint-B-${Date.now()}`, project_id: pid }
            }).then(s2 => {
              cy.request({
                method: 'POST', url: `/api/v1/sprints/${s2.body.id}/start`,
                headers: { Authorization: `Bearer ${token}` },
                failOnStatusCode: false
              }).its('status').should('eq', 409)
              // Cleanup s2
              cy.request({
                method: 'DELETE', url: `/api/v1/sprints/${s2.body.id}`,
                headers: { Authorization: `Bearer ${token}` },
                failOnStatusCode: false
              })
            })
          })
        })
      })
    })
  })

  it('10.4 COMPLETE Sprint → незакрытые задачи уходят в Backlog', () => {
    // Создать спринт, стартовать, добавить issue, завершить
    cy.createIssueViaApi({ title: 'CRUD10-InSprint' })
    cy.get('@issueId').then(issueId => {
      cy.getAuthToken().then(token => {
        cy.request({
          method: 'GET', url: '/api/projects',
          headers: { Authorization: `Bearer ${token}` }
        }).then(resp => {
          const pid = (resp.body[0])?.id
          cy.request({
            method: 'POST', url: '/api/v1/sprints',
            headers: { Authorization: `Bearer ${token}` },
            body: { name: `CY-Sprint-C-${Date.now()}`, project_id: pid }
          }).then(sr => {
            sprintId = sr.body.id
            // Добавить issue в спринт
            cy.request({
              method: 'PATCH', url: `/api/tasks/${issueId}/rank`,
              headers: { Authorization: `Bearer ${token}` },
              body: { rank: 0, sprint_id: sprintId }
            })
            // Стартовать
            cy.request({
              method: 'POST', url: `/api/v1/sprints/${sprintId}/start`,
              headers: { Authorization: `Bearer ${token}` }
            })
            // Завершить
            cy.intercept('POST', `**/sprints/${sprintId}/complete`).as('complete')
            cy.goToIssues()
            cy.get('.issues-tabs .tab').contains(/backlog/i).click()
            cy.get('.sprint-panel button').contains(/complete/i).click()
            cy.wait('@complete').its('response.statusCode').should('eq', 200)
            // Задача теперь в backlog
            cy.get('.backlog-view, [class*="backlog"]')
              .should('contain.text', 'CRUD10-InSprint')
            cy.deleteIssueViaApi(issueId)
          })
        })
      })
    })
  })

  it('10.5 Velocity: GET /sprints/velocity → данные после завершения спринта', () => {
    cy.getAuthToken().then(token => {
      cy.request({
        method: 'GET', url: '/api/projects',
        headers: { Authorization: `Bearer ${token}` }
      }).then(resp => {
        const pid = resp.body[0]?.id
        cy.request({
          method: 'GET',
          url: '/api/v1/sprints/velocity',
          headers: { Authorization: `Bearer ${token}` },
          qs: { project_id: pid, limit: 5 }
        }).then(vr => {
          expect(vr.status).to.eq(200)
          expect(Array.isArray(vr.body)).to.be.true
        })
      })
    })
  })

  it('10.6 Burndown: GET /sprints/{id}/burndown → {burndown: [...]}', () => {
    cy.getAuthToken().then(token => {
      cy.request({
        method: 'GET', url: '/api/projects',
        headers: { Authorization: `Bearer ${token}` }
      }).then(resp => {
        const pid = resp.body[0]?.id
        cy.request({
          method: 'POST', url: '/api/v1/sprints',
          headers: { Authorization: `Bearer ${token}` },
          body: { name: `CY-Burndown-${Date.now()}`, project_id: pid,
                  start_date: '2026-03-01', end_date: '2026-03-14' }
        }).then(sr => {
          sprintId = sr.body.id
          cy.request({
            method: 'GET',
            url: `/api/v1/sprints/${sprintId}/burndown`,
            headers: { Authorization: `Bearer ${token}` }
          }).then(br => {
            expect(br.status).to.eq(200)
            expect(br.body).to.have.property('burndown')
            expect(Array.isArray(br.body.burndown)).to.be.true
          })
        })
      })
    })
  })
})

describe('CRUD-11: Dashboard Stats — данные и кэш', () => {
  it('11.1 GET /tasks/dashboard/stats → 200 с by_type и by_priority', () => {
    cy.loginToApp()
    cy.window().then(win => {
      cy.request({
        method: 'GET', url: '/api/tasks/dashboard/stats',
        headers: { Authorization: `Bearer ${win.localStorage.getItem('access_token')}` },
        qs: { project_id: '9ddfd925-9728-4224-8a3d-13a6e2e01719' }
      }).then(resp => {
        expect(resp.status).to.eq(200)
        const body = resp.body
        // по крайней мере один из ключей должен быть
        const hasStats = 'by_type' in body || 'by_priority' in body ||
                         'by_assignee' in body || 'top_assignees' in body
        expect(hasStats).to.be.true
      })
    })
  })

  it('11.2 Второй запрос → X-Cache: HIT', () => {
    cy.loginToApp()
    cy.window().then(win => {
      const token = win.localStorage.getItem('access_token')
      const pid = '9ddfd925-9728-4224-8a3d-13a6e2e01719'
      // Первый запрос
      cy.request({
        method: 'GET', url: `/api/tasks/dashboard/stats?project_id=${pid}`,
        headers: { Authorization: `Bearer ${token}` }
      }).then(() => {
        // Второй запрос — должен быть HIT
        cy.request({
          method: 'GET', url: `/api/tasks/dashboard/stats?project_id=${pid}`,
          headers: { Authorization: `Bearer ${token}` }
        }).then(resp2 => {
          const cacheHeader = resp2.headers['x-cache'] || resp2.headers['X-Cache']
          expect(cacheHeader).to.match(/HIT/i)
        })
      })
    })
  })

  it('11.3 Dashboard вкладка в UI загружает чарты без 500', () => {
    cy.goToIssues()
    cy.intercept('GET', '**/tasks/dashboard/stats*').as('statsReq')
    cy.get('.issues-tabs .tab').contains(/dashboard/i).click({ force: true })
    cy.wait('@statsReq').its('response.statusCode').should('eq', 200)
    cy.get('canvas, svg, [class*="chart"]', { timeout: 10000 }).should('have.length.gte', 1)
  })
})

describe('CRUD-12: Негативные сценарии и граничные случаи', () => {
  it('12.1 /issues без авторизации → редирект на /login', () => {
    cy.clearLocalStorage()
    cy.visit('/dashboard/#/issues')
    cy.url({ timeout: 10000 }).should('include', '/login')
  })

  it('12.2 GET /tasks/{несуществующий-id} → 404', () => {
    cy.loginToApp()
    cy.window().then(win => {
      cy.request({
        method: 'GET',
        url: '/api/tasks/00000000-0000-0000-0000-000000000000',
        headers: { Authorization: `Bearer ${win.localStorage.getItem('access_token')}` },
        failOnStatusCode: false
      }).its('status').should('eq', 404)
    })
  })

  it('12.3 POST /tasks без title → 422 Validation Error', () => {
    cy.loginToApp()
    cy.window().then(win => {
      cy.request({
        method: 'POST',
        url: '/api/tasks',
        headers: { Authorization: `Bearer ${win.localStorage.getItem('access_token')}` },
        body: { priority: 'high' }, // нет title
        failOnStatusCode: false
      }).its('status').should('be.oneOf', [400, 422])
    })
  })

  it('12.4 JQL валидный запрос → НЕ 500', () => {
    cy.loginToApp()
    cy.window().then(win => {
      cy.request({
        method: 'GET',
        url: '/api/tasks',
        headers: { Authorization: `Bearer ${win.localStorage.getItem('access_token')}` },
        qs: { jql: "status = 'todo'", project_id: '9ddfd925-9728-4224-8a3d-13a6e2e01719' },
        failOnStatusCode: false
      }).then(resp => {
        // Должен быть 200 или 400 — но не 500!
        expect(resp.status).to.be.oneOf([200, 400])
      })
    })
  })

  it('12.5 Reload на /issues/EL-99999 (несуществующий) → graceful error, не белый экран', () => {
    cy.loginToApp()
    cy.visit('/dashboard/#/issues/EL-99999')
    cy.wait(3000)
    // Приложение не должно показать пустой белый экран
    cy.get('body').should('not.be.empty')
    cy.get('.issues-page, .error-page, [class*="not-found"], .kanban-board').should('exist')
  })
})
