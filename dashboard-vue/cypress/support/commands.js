// ═══════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════

/**
 * Получить токен из localStorage.
 * Вызывается внутри cy.window().then() контекста.
 */
function getToken(win) {
  return win.localStorage.getItem('access_token')
}

/**
 * Получить project_id первого проекта через API.
 * Сохраняет результат в @projectId alias.
 */
Cypress.Commands.add('getProjectId', () => {
  cy.window().then(win => {
    const token = getToken(win)
    cy.request({
      method: 'GET',
      url: '/api/projects',
      headers: { Authorization: `Bearer ${token}` }
    }).then(resp => {
      const projects = Array.isArray(resp.body)
        ? resp.body
        : (resp.body?.items || [])
      expect(projects.length, 'At least one project must exist').to.be.gt(0)
      cy.wrap(projects[0].id).as('projectId')
    })
  })
})

// ═══════════════════════════════════════════════════════
// AUTH TOKEN HELPER
// ═══════════════════════════════════════════════════════

/**
 * Получить access_token из localStorage текущего окна.
 * Используется в тестах вместо ручного cy.window().then().
 */
Cypress.Commands.add('getAuthToken', () => {
  return cy.window().then(win => {
    const token = win.localStorage.getItem('access_token')
    if (!token) throw new Error('No auth token in localStorage')
    return token
  })
})

// ═══════════════════════════════════════════════════════
// AUTH
// ═══════════════════════════════════════════════════════

/**
 * Авторизация через UI с сохранением сессии через cy.session().
 * Повторно использует сессию если она не протухла.
 */
Cypress.Commands.add('loginToApp', (
  username = 'admin',
  password = 'Misha2026'
) => {
  cy.session(
    [username, password],
    () => {
      cy.visit('/dashboard/#/login')
      cy.get('input[type="text"], input[name="username"]', { timeout: 10000 })
        .clear().type(username)
      cy.get('input[type="password"]', { timeout: 5000 })
        .clear().type(password)
      cy.get('button[type="submit"]').click()
      cy.url({ timeout: 10000 }).should('not.include', '/login')
      cy.window().then(win => {
        expect(win.localStorage.getItem('access_token')).to.exist
      })
    },
    {
      validate() {
        cy.window().then(win => {
          const token = win.localStorage.getItem('access_token')
          if (!token) throw new Error('No access token — re-login required')
        })
      }
    }
  )
})

// ═══════════════════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════════════════

Cypress.Commands.add('goToIssues', () => {
  cy.loginToApp()
  cy.visit('/dashboard/#/issues')
  cy.get('.issues-page', { timeout: 15000 }).should('exist')
  // Дать время kanban загрузиться
  cy.get('.kanban-board, .issues-tabs', { timeout: 10000 }).should('exist')
})

Cypress.Commands.add('goToArticles', () => {
  cy.loginToApp()
  cy.visit('/dashboard/#/articles')
  cy.get('.articles-page', { timeout: 15000 }).should('exist')
})

// ═══════════════════════════════════════════════════════
// ISSUES API COMMANDS
// ═══════════════════════════════════════════════════════

/**
 * Создать задачу через API.
 * Автоматически получает project_id если не передан.
 * Сохраняет id в @issueId.
 * Возвращает полный объект задачи.
 */
Cypress.Commands.add('createIssueViaApi', (overrides = {}) => {
  cy.window().then(win => {
    const token = getToken(win)
    cy.request({
      method: 'GET',
      url: '/api/projects',
      headers: { Authorization: `Bearer ${token}` }
    }).then(projResp => {
      const projects = Array.isArray(projResp.body)
        ? projResp.body
        : (projResp.body?.items || [])
      const projectId = projects[0]?.id

      cy.request({
        method: 'POST',
        url: '/api/tasks',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: {
          title: `CY-Issue-${Date.now()}`,
          priority: 'medium',
          status: 'todo',
          project_id: projectId,
          ...overrides
        }
      }).then(resp => {
        // Backend возвращает 200 для create (не 201)
        expect(resp.status).to.be.oneOf([200, 201])
        const id = resp.body.id
        cy.wrap(id).as('issueId')
        cy.wrap(resp.body).as('createdIssue')
      })
    })
  })
})

/**
 * Удалить задачу через API. failOnStatusCode: false — тихо игнорирует 404.
 */
Cypress.Commands.add('deleteIssueViaApi', (id) => {
  if (!id) return
  cy.window().then(win => {
    const token = getToken(win)
    cy.request({
      method: 'DELETE',
      url: `/api/tasks/${id}`,
      headers: { Authorization: `Bearer ${token}` },
      failOnStatusCode: false
    })
  })
})

/**
 * Получить задачу через API по id.
 * Возвращает полный объект (со всеми полями).
 */
Cypress.Commands.add('getIssueViaApi', (id) => {
  cy.window().then(win => {
    const token = getToken(win)
    cy.request({
      method: 'GET',
      url: `/api/tasks/${id}`,
      headers: { Authorization: `Bearer ${token}` }
    }).then(resp => {
      expect(resp.status).to.eq(200)
      cy.wrap(resp.body).as('fetchedIssue')
    })
  })
})

/**
 * Обновить задачу через API.
 */
Cypress.Commands.add('updateIssueViaApi', (id, data) => {
  cy.window().then(win => {
    const token = getToken(win)
    cy.request({
      method: 'PUT',
      url: `/api/tasks/${id}`,
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: data
    }).then(resp => {
      expect(resp.status).to.be.oneOf([200, 204])
    })
  })
})

/**
 * Открыть первую задачу на Kanban доске.
 * Ждёт появления карточек и кликает первую.
 */
Cypress.Commands.add('openFirstIssueInBoard', () => {
  cy.get('.task-card', { timeout: 15000 })
    .should('have.length.gte', 1)
    .first().click()
  cy.get('.task-detail, .task-detail-overlay', { timeout: 10000 })
    .should('be.visible')
})

/**
 * Открыть задачу по human_id (например EL-42).
 * После EL071 URL обновляется при открытии задачи.
 */
Cypress.Commands.add('openIssueByHumanId', (humanId) => {
  cy.visit(`/dashboard/#/issues/${humanId}`)
  cy.get('.task-detail, .task-detail-overlay', { timeout: 15000 })
    .should('be.visible')
  cy.contains(humanId, { timeout: 5000 }).should('exist')
})

// ═══════════════════════════════════════════════════════
// ARTICLES API COMMANDS
// ═══════════════════════════════════════════════════════

/**
 * Создать статью через API.
 * Сохраняет id в @articleId, полный объект в @createdArticle.
 */
Cypress.Commands.add('createArticleViaApi', (overrides = {}) => {
  cy.window().then(win => {
    const token = getToken(win)
    cy.request({
      method: 'POST',
      url: '/api/articles',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: {
        title: `CY-Article-${Date.now()}`,
        content: JSON.stringify({ version: 'grid-1', rows: [] }),
        status: 'draft',
        ...overrides
      }
    }).then(resp => {
      expect(resp.status).to.be.oneOf([200, 201])
      cy.wrap(resp.body.id).as('articleId')
      cy.wrap(resp.body).as('createdArticle')
    })
  })
})

/**
 * Удалить статью через API.
 */
Cypress.Commands.add('deleteArticleViaApi', (id) => {
  if (!id) return
  cy.window().then(win => {
    const token = getToken(win)
    cy.request({
      method: 'DELETE',
      url: `/api/articles/${id}`,
      headers: { Authorization: `Bearer ${token}` },
      failOnStatusCode: false
    })
  })
})

/**
 * Получить статью через API по id.
 */
Cypress.Commands.add('getArticleViaApi', (id) => {
  cy.window().then(win => {
    const token = getToken(win)
    cy.request({
      method: 'GET',
      url: `/api/articles/${id}`,
      headers: { Authorization: `Bearer ${token}` }
    }).then(resp => {
      expect(resp.status).to.eq(200)
      cy.wrap(resp.body).as('fetchedArticle')
    })
  })
})

/**
 * Обновить статью через API.
 */
Cypress.Commands.add('updateArticleViaApi', (id, data) => {
  cy.window().then(win => {
    const token = getToken(win)
    cy.request({
      method: 'PUT',
      url: `/api/articles/${id}`,
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: data
    }).then(resp => {
      expect(resp.status).to.be.oneOf([200, 204])
    })
  })
})

/**
 * Создать папку статей через API.
 * Сохраняет id в @folderId.
 */
Cypress.Commands.add('createFolderViaApi', (name = `CY-Folder-${Date.now()}`, parentId = null) => {
  cy.window().then(win => {
    const token = getToken(win)
    cy.request({
      method: 'POST',
      url: '/api/articles/folders',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: {
        name,
        ...(parentId ? { parent_id: parentId } : {})
      }
    }).then(resp => {
      expect(resp.status).to.be.oneOf([200, 201])
      cy.wrap(resp.body.id).as('folderId')
      cy.wrap(resp.body).as('createdFolder')
    })
  })
})

/**
 * Удалить папку статей через API.
 */
Cypress.Commands.add('deleteFolderViaApi', (id) => {
  if (!id) return
  cy.window().then(win => {
    const token = getToken(win)
    cy.request({
      method: 'DELETE',
      url: `/api/articles/folders/${id}`,
      headers: { Authorization: `Bearer ${token}` },
      failOnStatusCode: false
    })
  })
})

/**
 * Открыть первую статью в списке.
 */
Cypress.Commands.add('openFirstArticle', () => {
  cy.get('.article-row', { timeout: 10000 })
    .should('have.length.gte', 1)
    .first().click()
  cy.get('.article-viewer', { timeout: 10000 }).should('be.visible')
})
