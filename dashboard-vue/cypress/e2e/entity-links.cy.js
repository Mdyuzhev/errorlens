// entity-links.cy.js — EL082: Cross-Entity Linking E2E Tests
// Pattern: createViaApi -> action in UI -> verify via API -> cleanup

describe('LINK-01: Unified Entity Search API', () => {
  it('01.1 GET /entities/search?q=EL- -> task results', () => {
    cy.loginToApp()
    cy.getAuthToken().then(token => {
      cy.request({
        method: 'GET',
        url: '/api/entities/search',
        headers: { Authorization: `Bearer ${token}` },
        qs: { q: 'EL-', types: 'task' },
        failOnStatusCode: false
      }).then(resp => {
        expect(resp.status).to.eq(200)
        expect(Array.isArray(resp.body)).to.be.true
        if (resp.body.length > 0) {
          expect(resp.body[0]).to.have.all.keys('id', 'type', 'title')
          expect(resp.body[0].type).to.eq('task')
        }
      })
    })
  })

  it('01.2 GET /entities/search?q=login -> results from multiple types', () => {
    cy.loginToApp()
    cy.getAuthToken().then(token => {
      cy.request({
        method: 'GET',
        url: '/api/entities/search',
        headers: { Authorization: `Bearer ${token}` },
        qs: { q: 'login', types: 'task,testcase,article' },
        failOnStatusCode: false
      }).then(resp => {
        expect(resp.status).to.eq(200)
        expect(Array.isArray(resp.body)).to.be.true
        // Each result has type field
        resp.body.forEach(r => {
          expect(r).to.have.property('type')
          expect(['task', 'testcase', 'article']).to.include(r.type)
        })
      })
    })
  })

  it('01.3 Search without auth -> 401', () => {
    cy.request({
      method: 'GET',
      url: '/api/entities/search',
      qs: { q: 'test' },
      failOnStatusCode: false
    }).its('status').should('eq', 401)
  })

  it('01.4 Preview task -> 200 with correct fields', () => {
    cy.loginToApp()
    cy.createIssueViaApi({ title: 'LINK01-Preview-Issue' })
    cy.get('@issueId').then(issueId => {
      cy.getAuthToken().then(token => {
        cy.request({
          method: 'GET',
          url: `/api/entities/task/${issueId}/preview`,
          headers: { Authorization: `Bearer ${token}` }
        }).then(resp => {
          expect(resp.status).to.eq(200)
          expect(resp.body).to.have.all.keys('id', 'type', 'title', 'status', 'human_id')
          expect(resp.body.type).to.eq('task')
        })
        cy.deleteIssueViaApi(issueId)
      })
    })
  })
})

describe('LINK-02: TestCase -> Issue linking', () => {
  let issueId, tcId

  before(() => {
    cy.loginToApp()
    cy.createIssueViaApi({ title: 'LINK02-Target-Issue' })
    cy.get('@issueId').then(id => { issueId = id })
    cy.createIssueViaApi({ title: 'LINK02-For-TC-Create' })
    cy.get('@issueId').then(id => { tcId = id })
  })

  after(() => {
    cy.loginToApp()
    if (issueId) cy.deleteIssueViaApi(issueId)
  })

  it('02.1 API: PUT /testcases/{id} with linked_issue_ids -> saves', () => {
    cy.loginToApp()
    cy.getAuthToken().then(token => {
      // Create TC
      cy.request({
        method: 'POST',
        url: '/api/testcases',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: { title: 'LINK02-TestCase', priority: 'medium', status: 'draft' }
      }).then(resp => {
        const newTcId = resp.body.id
        // Link to issue
        cy.request({
          method: 'PUT',
          url: `/api/testcases/${newTcId}`,
          headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: { linked_issue_ids: [issueId] }
        }).then(putResp => {
          expect(putResp.status).to.be.oneOf([200, 204])
        })
        // Verify
        cy.request({
          method: 'GET',
          url: `/api/testcases/${newTcId}`,
          headers: { Authorization: `Bearer ${token}` }
        }).then(getResp => {
          expect(getResp.body.linked_issue_ids).to.include(issueId)
        })
        // Cleanup
        cy.request({
          method: 'DELETE',
          url: `/api/testcases/${newTcId}`,
          headers: { Authorization: `Bearer ${token}` },
          failOnStatusCode: false
        })
      })
    })
  })

  it('02.2 UI: QATestCaseViewer Links tab shows Issue human_id', () => {
    cy.loginToApp()
    cy.getAuthToken().then(token => {
      // Create TC with linked issue
      cy.request({
        method: 'POST',
        url: '/api/testcases',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: { title: 'LINK02-WithLinked', priority: 'medium', linked_issue_ids: [issueId] }
      }).then(resp => {
        const newTcId = resp.body.id
        cy.visit('/dashboard/#/qa?tab=tree')
        cy.get('.qa-page', { timeout: 15000 }).should('exist')
        cy.get('.tc-row').contains('LINK02-WithLinked').click({ force: true })
        cy.get('.tcv-overlay, .qa-test-case-viewer', { timeout: 10000 }).should('be.visible')
        cy.get('.tcv-tabs .tcv-tab').contains(/links/i).click()
        // Should show EL-XX, not UUID
        cy.get('.links-section').should('not.contain.text', issueId.slice(0, 8))
        cy.get('.links-section .link-id, .links-section .link-result-id, .link-badge').should('contain.text', 'EL-')
        // Cleanup
        cy.request({
          method: 'DELETE',
          url: `/api/testcases/${newTcId}`,
          headers: { Authorization: `Bearer ${token}` },
          failOnStatusCode: false
        })
      })
    })
  })
})

describe('LINK-03: Issue -> TestCase linking', () => {
  let issueId

  before(() => {
    cy.loginToApp()
    cy.createIssueViaApi({ title: 'LINK03-Issue-ForTC' })
    cy.get('@issueId').then(id => { issueId = id })
  })

  after(() => {
    cy.loginToApp()
    if (issueId) cy.deleteIssueViaApi(issueId)
  })

  it('03.1 API: PUT /tasks/{id} with linked_tc_ids -> 200', () => {
    cy.loginToApp()
    cy.getAuthToken().then(token => {
      cy.request({
        method: 'PUT',
        url: `/api/tasks/${issueId}`,
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: { linked_tc_ids: [] } // empty array -- just test field accepted
      }).its('status').should('eq', 200)
    })
  })

  it('03.2 GET /tasks/{id} -> contains linked_tc_ids and linked_article_ids', () => {
    cy.loginToApp()
    cy.getAuthToken().then(token => {
      cy.request({
        method: 'GET',
        url: `/api/tasks/${issueId}`,
        headers: { Authorization: `Bearer ${token}` }
      }).then(resp => {
        expect(resp.body).to.have.property('linked_tc_ids')
        expect(resp.body).to.have.property('linked_article_ids')
      })
    })
  })

  it('03.3 UI: IssueDetailView sidebar contains Links section', () => {
    cy.goToIssues()
    cy.get('.kanban-board', { timeout: 15000 }).should('exist')
    cy.get('.task-card').contains('LINK03-Issue-ForTC').click({ force: true })
    cy.get('.task-viewer', { timeout: 10000 }).should('be.visible')
    cy.get('.task-viewer button').contains(/edit/i).click({ force: true })
    cy.get('.task-detail-overlay', { timeout: 10000 }).should('exist')
    // Links section should exist in sidebar
    cy.get('.task-sidebar').should('contain.text', /links|связи/i)
  })

  it('03.4 LinkSearch: type TC- -> dropdown not empty (if TCs exist)', () => {
    cy.loginToApp()
    cy.getAuthToken().then(token => {
      // Check if any TCs exist
      cy.request({
        method: 'GET',
        url: '/api/testcases?limit=1',
        headers: { Authorization: `Bearer ${token}` }
      }).then(resp => {
        const items = resp.body.items || resp.body
        if (!items.length) { cy.log('No TCs in DB -- skip'); return }

        cy.goToIssues()
        cy.get('.task-card').contains('LINK03-Issue-ForTC').click({ force: true })
        cy.get('.task-viewer button').contains(/edit/i).click({ force: true })
        cy.get('.task-detail-overlay', { timeout: 10000 }).should('exist')
        cy.get('.link-search-input').first().type('TC-', { force: true })
        cy.get('.link-search-results, .link-search-item', { timeout: 5000 }).should('be.visible')
      })
    })
  })
})

describe('LINK-04: Article -> Issue + TestCase linking', () => {
  let articleId

  before(() => {
    cy.loginToApp()
    cy.createArticleViaApi({ title: 'LINK04-Article-ForLinks' })
    cy.get('@articleId').then(id => { articleId = id })
  })

  after(() => {
    cy.loginToApp()
    if (articleId) cy.deleteArticleViaApi(articleId)
  })

  it('04.1 ArticleViewer contains related materials section', () => {
    cy.goToArticles()
    cy.get('.article-row').contains('LINK04-Article-ForLinks').click({ force: true })
    cy.get('.article-viewer', { timeout: 10000 }).should('be.visible')
    cy.get('.viewer-links-section, [class*="links-section"]', { timeout: 5000 }).should('exist')
  })

  it('04.2 Links search in Article: type EL- -> results appear', () => {
    cy.goToArticles()
    cy.get('.article-row').contains('LINK04-Article-ForLinks').click({ force: true })
    cy.get('.article-viewer', { timeout: 10000 }).should('be.visible')
    cy.get('.viewer-links-section .link-search-input, [class*="links"] .link-search-input')
      .first()
      .type('EL-', { force: true })
    cy.get('.link-search-results', { timeout: 5000 }).should('be.visible')
  })

  it('04.3 API: PUT /articles/{id} with linked_issue_ids -> 200', () => {
    cy.loginToApp()
    cy.getAuthToken().then(token => {
      cy.createIssueViaApi({ title: 'LINK04-Link-Target' })
      cy.get('@issueId').then(issueIdForLink => {
        cy.request({
          method: 'PUT',
          url: `/api/articles/${articleId}`,
          headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: { linked_issue_ids: [issueIdForLink] }
        }).its('status').should('eq', 200)
        cy.deleteIssueViaApi(issueIdForLink)
      })
    })
  })
})

describe('LINK-05: Navigation between entities', () => {
  let issueId, issueHumanId

  before(() => {
    cy.loginToApp()
    cy.createIssueViaApi({ title: 'LINK05-Nav-Issue' })
    cy.get('@issueId').then(id => { issueId = id })
    cy.get('@createdIssue').then(issue => { issueHumanId = issue.human_id })
  })

  after(() => {
    cy.loginToApp()
    if (issueId) cy.deleteIssueViaApi(issueId)
  })

  it('05.1 Unified search by human_id EL-N -> finds specific task', () => {
    cy.loginToApp()
    cy.getAuthToken().then(token => {
      cy.request({
        method: 'GET',
        url: '/api/entities/search',
        headers: { Authorization: `Bearer ${token}` },
        qs: { q: issueHumanId, types: 'task' }
      }).then(resp => {
        expect(resp.status).to.eq(200)
        const found = resp.body.find(r => r.id === issueId || r.human_id === issueHumanId)
        expect(found).to.exist
      })
    })
  })

  it('05.2 /entities/task/{id}/preview -> correct data', () => {
    cy.loginToApp()
    cy.getAuthToken().then(token => {
      cy.request({
        method: 'GET',
        url: `/api/entities/task/${issueId}/preview`,
        headers: { Authorization: `Bearer ${token}` }
      }).then(resp => {
        expect(resp.status).to.eq(200)
        expect(resp.body.id).to.eq(issueId)
        expect(resp.body.title).to.eq('LINK05-Nav-Issue')
        expect(resp.body.human_id).to.eq(issueHumanId)
      })
    })
  })

  it('05.3 /entities/task/{id}/preview for non-existent -> 404', () => {
    cy.loginToApp()
    cy.getAuthToken().then(token => {
      cy.request({
        method: 'GET',
        url: '/api/entities/task/00000000-0000-0000-0000-000000000000/preview',
        headers: { Authorization: `Bearer ${token}` },
        failOnStatusCode: false
      }).its('status').should('eq', 404)
    })
  })
})
