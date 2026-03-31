// test-plans.cy.js — EL088 E2E Tests for Test Plans
// 10 describes, 35+ tests
// Pattern: createViaApi → action → verify → cleanup

const PID = '9ddfd925-9728-4224-8a3d-13a6e2e01719'

function apiHeaders() {
  return {
    Authorization: `Bearer ${Cypress.env('access_token')}`,
    'Content-Type': 'application/json',
  }
}

// ═══════════════════════════════════════════════════════
// TP-01: Happy Path (8 tests)
// ═══════════════════════════════════════════════════════

describe('TP-01: Happy Path — полный цикл прогона', () => {
  let planId, tc1Id, tc2Id, runId

  before(() => {
    cy.loginToApp()
    cy.createTestPlanViaApi('CY-HappyPath-Plan')
    cy.get('@planId').then(id => { planId = id })

    cy.createTestCaseViaApi({ title: 'CY-TC-HP-1', steps: JSON.stringify([{ action: 'Open page', expected: 'Page loads' }]) })
    cy.get('@testCaseId').then(id => { tc1Id = id })

    cy.createTestCaseViaApi({ title: 'CY-TC-HP-2', steps: JSON.stringify([{ action: 'Click btn', expected: 'Action done' }]) })
    cy.get('@testCaseId').then(id => {
      tc2Id = id
      cy.addCaseToPlanViaApi(planId, tc1Id)
      cy.addCaseToPlanViaApi(planId, tc2Id)
      cy.startTestPlanRunViaApi(planId, 'CY-Run-HP')
    })
    cy.get('@runId').then(id => { runId = id })
  })

  after(() => {
    if (planId) cy.deleteTestPlanViaApi(planId)
    if (tc1Id) cy.deleteTestCaseViaApi(tc1Id)
    if (tc2Id) cy.deleteTestCaseViaApi(tc2Id)
  })

  it('01.1 GET /runs/{id} → 200, results.length=2, total=2', () => {
    cy.request({
      method: 'GET',
      url: `/api/v1/test-plans/runs/${runId}`,
      headers: apiHeaders(),
    }).then(resp => {
      expect(resp.status).to.eq(200)
      expect(resp.body.results).to.have.length(2)
      expect(resp.body.total).to.eq(2)
    })
  })

  it('01.2 [REGRESSION B01] PUT results → 200, NOT 500', () => {
    cy.request({
      method: 'PUT',
      url: `/api/v1/test-plans/runs/${runId}/results/${tc1Id}`,
      headers: apiHeaders(),
      body: { status: 'passed' },
    }).then(resp => {
      expect(resp.status).to.eq(200)
      expect(resp.body.counters).to.exist
      expect(resp.body.counters.passed).to.eq(1)
    })
  })

  it('01.3 PUT results tc2 failed → counters.failed=1', () => {
    cy.request({
      method: 'PUT',
      url: `/api/v1/test-plans/runs/${runId}/results/${tc2Id}`,
      headers: apiHeaders(),
      body: { status: 'failed' },
    }).then(resp => {
      expect(resp.status).to.eq(200)
      expect(resp.body.counters.failed).to.eq(1)
    })
  })

  it('01.4 GET /runs/{id} → passed=1, failed=1', () => {
    cy.request({
      method: 'GET',
      url: `/api/v1/test-plans/runs/${runId}`,
      headers: apiHeaders(),
    }).then(resp => {
      expect(resp.body.passed).to.eq(1)
      expect(resp.body.failed).to.eq(1)
    })
  })

  it('01.5 Overwrite tc2 failed→passed → counters.passed=2, failed=0', () => {
    cy.request({
      method: 'PUT',
      url: `/api/v1/test-plans/runs/${runId}/results/${tc2Id}`,
      headers: apiHeaders(),
      body: { status: 'passed' },
    }).then(resp => {
      expect(resp.status).to.eq(200)
      expect(resp.body.counters.passed).to.eq(2)
      expect(resp.body.counters.failed).to.eq(0)
    })
  })

  it('01.6 POST /finish → 200, status=completed', () => {
    cy.request({
      method: 'POST',
      url: `/api/v1/test-plans/runs/${runId}/finish`,
      headers: apiHeaders(),
    }).then(resp => {
      expect(resp.status).to.eq(200)
      expect(resp.body.status).to.eq('completed')
    })
  })

  it('01.7 GET /runs/{id} → status=completed, passed=2', () => {
    cy.request({
      method: 'GET',
      url: `/api/v1/test-plans/runs/${runId}`,
      headers: apiHeaders(),
    }).then(resp => {
      expect(resp.body.status).to.eq('completed')
      expect(resp.body.passed).to.eq(2)
    })
  })

  it('01.8 UI: visit run page → overlay exists, 2 cases visible', () => {
    cy.visit(`/dashboard/#/test-plans/runs/${runId}`)
    cy.get('.run-view-overlay', { timeout: 10000 }).should('exist')
    cy.get('.case-item', { timeout: 10000 }).should('have.length', 2)
  })
})

// ═══════════════════════════════════════════════════════
// TP-02: Idempotent add_cases (3 tests)
// ═══════════════════════════════════════════════════════

describe('TP-02: Идемпотентность add_cases', () => {
  let planId, tcId, tc2Id

  before(() => {
    cy.loginToApp()
    cy.createTestPlanViaApi('CY-Idempotent-Plan')
    cy.get('@planId').then(id => { planId = id })
    cy.createTestCaseViaApi({ title: 'CY-TC-Idem-1' })
    cy.get('@testCaseId').then(id => {
      tcId = id
      cy.addCaseToPlanViaApi(planId, tcId)
    })
    cy.createTestCaseViaApi({ title: 'CY-TC-Idem-2' })
    cy.get('@testCaseId').then(id => { tc2Id = id })
  })

  after(() => {
    if (planId) cy.deleteTestPlanViaApi(planId)
    if (tcId) cy.deleteTestCaseViaApi(tcId)
    if (tc2Id) cy.deleteTestCaseViaApi(tc2Id)
  })

  it('02.1 [FIX B02] Duplicate add → NOT 400', () => {
    cy.request({
      method: 'POST',
      url: `/api/v1/test-plans/${planId}/cases`,
      headers: apiHeaders(),
      body: { testcase_ids: [tcId] },
      failOnStatusCode: false,
    }).then(resp => {
      expect(resp.status).to.not.eq(400)
      expect(resp.body.skipped).to.eq(1)
    })
  })

  it('02.2 GET plan → cases contains exactly 1 instance', () => {
    cy.request({
      method: 'GET',
      url: `/api/v1/test-plans/${planId}`,
      headers: apiHeaders(),
    }).then(resp => {
      expect(resp.body.cases_count).to.eq(1)
    })
  })

  it('02.3 Bulk add [existing, new, new] → added=1, skipped=1', () => {
    cy.request({
      method: 'POST',
      url: `/api/v1/test-plans/${planId}/cases`,
      headers: apiHeaders(),
      body: { testcase_ids: [tcId, tc2Id] },
    }).then(resp => {
      expect(resp.body.added).to.eq(1)
      expect(resp.body.skipped).to.eq(1)
    })
  })
})

// ═══════════════════════════════════════════════════════
// TP-03: Partial run (3 tests)
// ═══════════════════════════════════════════════════════

describe('TP-03: Частичное прохождение', () => {
  let planId, tc1Id, tc2Id, tc3Id, runId

  before(() => {
    cy.loginToApp()
    cy.createTestPlanViaApi('CY-Partial-Plan')
    cy.get('@planId').then(id => { planId = id })

    cy.createTestCaseViaApi({ title: 'CY-TC-Part-1' })
    cy.get('@testCaseId').then(id => { tc1Id = id })
    cy.createTestCaseViaApi({ title: 'CY-TC-Part-2' })
    cy.get('@testCaseId').then(id => { tc2Id = id })
    cy.createTestCaseViaApi({ title: 'CY-TC-Part-3' })
    cy.get('@testCaseId').then(id => {
      tc3Id = id
      cy.addCaseToPlanViaApi(planId, tc1Id)
      cy.addCaseToPlanViaApi(planId, tc2Id)
      cy.addCaseToPlanViaApi(planId, tc3Id)
      cy.startTestPlanRunViaApi(planId, 'CY-Run-Partial')
    })
    cy.get('@runId').then(id => {
      runId = id
      cy.recordResultViaApi(runId, tc1Id, 'passed')
      cy.recordResultViaApi(runId, tc2Id, 'failed')
    })
  })

  after(() => {
    if (planId) cy.deleteTestPlanViaApi(planId)
    if (tc1Id) cy.deleteTestCaseViaApi(tc1Id)
    if (tc2Id) cy.deleteTestCaseViaApi(tc2Id)
    if (tc3Id) cy.deleteTestCaseViaApi(tc3Id)
  })

  it('03.1 GET /runs/{id} → total=3, one case without status', () => {
    cy.request({
      method: 'GET',
      url: `/api/v1/test-plans/runs/${runId}`,
      headers: apiHeaders(),
    }).then(resp => {
      expect(resp.body.total).to.eq(3)
      const untested = resp.body.results.filter(r => r.status === null)
      expect(untested).to.have.length(1)
    })
  })

  it('03.2 finishRun → 200 (partial run can finish)', () => {
    cy.request({
      method: 'POST',
      url: `/api/v1/test-plans/runs/${runId}/finish`,
      headers: apiHeaders(),
    }).then(resp => {
      expect(resp.status).to.eq(200)
    })
  })

  it('03.3 UI: untested case stripe visible', () => {
    cy.visit(`/dashboard/#/test-plans/runs/${runId}`)
    cy.get('.run-view-overlay', { timeout: 10000 }).should('exist')
    cy.get('.case-item-stripe.none', { timeout: 5000 }).should('exist')
  })
})

// ═══════════════════════════════════════════════════════
// TP-04: Result in completed run (3 tests)
// ═══════════════════════════════════════════════════════

describe('TP-04: Результат в завершённый прогон', () => {
  let planId, tcId, runId

  before(() => {
    cy.loginToApp()
    cy.createTestPlanViaApi('CY-Completed-Plan')
    cy.get('@planId').then(id => { planId = id })
    cy.createTestCaseViaApi({ title: 'CY-TC-Completed' })
    cy.get('@testCaseId').then(id => {
      tcId = id
      cy.addCaseToPlanViaApi(planId, tcId)
      cy.startTestPlanRunViaApi(planId, 'CY-Run-Completed')
    })
    cy.get('@runId').then(id => {
      runId = id
      cy.recordResultViaApi(runId, tcId, 'passed')
      cy.finishRunViaApi(runId)
    })
  })

  after(() => {
    if (planId) cy.deleteTestPlanViaApi(planId)
    if (tcId) cy.deleteTestCaseViaApi(tcId)
  })

  it('04.1 PUT results → 400 with detail containing "completed"', () => {
    cy.request({
      method: 'PUT',
      url: `/api/v1/test-plans/runs/${runId}/results/${tcId}`,
      headers: apiHeaders(),
      body: { status: 'failed' },
      failOnStatusCode: false,
    }).then(resp => {
      expect(resp.status).to.eq(400)
      expect(resp.body.detail).to.include('completed')
    })
  })

  it('04.2 POST /finish → 400', () => {
    cy.request({
      method: 'POST',
      url: `/api/v1/test-plans/runs/${runId}/finish`,
      headers: apiHeaders(),
      failOnStatusCode: false,
    }).then(resp => {
      expect(resp.status).to.eq(400)
    })
  })

  it('04.3 UI: save-result-btn not present, no btn-finish', () => {
    cy.visit(`/dashboard/#/test-plans/runs/${runId}`)
    cy.get('.run-view-overlay', { timeout: 10000 }).should('exist')
    cy.get('[data-testid="save-result-btn"]').should('not.exist')
    cy.get('.btn-finish').should('not.exist')
  })
})

// ═══════════════════════════════════════════════════════
// TP-05: Empty plan (3 tests)
// ═══════════════════════════════════════════════════════

describe('TP-05: Пустой план', () => {
  let planId, runId

  before(() => {
    cy.loginToApp()
    cy.createTestPlanViaApi('CY-Empty-Plan')
    cy.get('@planId').then(id => {
      planId = id
      cy.startTestPlanRunViaApi(planId, 'CY-Run-Empty')
    })
    cy.get('@runId').then(id => { runId = id })
  })

  after(() => {
    if (planId) cy.deleteTestPlanViaApi(planId)
  })

  it('05.1 GET /runs/{id} → total=0, results=[]', () => {
    cy.request({
      method: 'GET',
      url: `/api/v1/test-plans/runs/${runId}`,
      headers: apiHeaders(),
    }).then(resp => {
      expect(resp.body.total).to.eq(0)
      expect(resp.body.results).to.have.length(0)
    })
  })

  it('05.2 [FIX B03] POST /finish → 400 (no test cases)', () => {
    cy.request({
      method: 'POST',
      url: `/api/v1/test-plans/runs/${runId}/finish`,
      headers: apiHeaders(),
      failOnStatusCode: false,
    }).then(resp => {
      expect(resp.status).to.eq(400)
    })
  })

  it('05.3 UI: btn-finish disabled, empty-state visible', () => {
    cy.visit(`/dashboard/#/test-plans/runs/${runId}`)
    cy.get('.run-view-overlay', { timeout: 10000 }).should('exist')
    cy.get('.btn-finish').should('be.disabled')
    cy.get('.empty-state', { timeout: 5000 }).should('exist')
  })
})

// ═══════════════════════════════════════════════════════
// TP-06: Status filtering in UI (5 tests)
// ═══════════════════════════════════════════════════════

describe('TP-06: Фильтрация статусов в UI', () => {
  let planId, tc1Id, tc2Id, tc3Id, runId

  before(() => {
    cy.loginToApp()
    cy.createTestPlanViaApi('CY-Filter-Plan')
    cy.get('@planId').then(id => { planId = id })

    cy.createTestCaseViaApi({ title: 'CY-TC-Filter-Pass' })
    cy.get('@testCaseId').then(id => { tc1Id = id })
    cy.createTestCaseViaApi({ title: 'CY-TC-Filter-Fail' })
    cy.get('@testCaseId').then(id => { tc2Id = id })
    cy.createTestCaseViaApi({ title: 'CY-TC-Filter-None' })
    cy.get('@testCaseId').then(id => {
      tc3Id = id
      cy.addCaseToPlanViaApi(planId, tc1Id)
      cy.addCaseToPlanViaApi(planId, tc2Id)
      cy.addCaseToPlanViaApi(planId, tc3Id)
      cy.startTestPlanRunViaApi(planId, 'CY-Run-Filter')
    })
    cy.get('@runId').then(id => {
      runId = id
      cy.recordResultViaApi(runId, tc1Id, 'passed')
      cy.recordResultViaApi(runId, tc2Id, 'failed')
    })
  })

  after(() => {
    if (planId) cy.deleteTestPlanViaApi(planId)
    if (tc1Id) cy.deleteTestCaseViaApi(tc1Id)
    if (tc2Id) cy.deleteTestCaseViaApi(tc2Id)
    if (tc3Id) cy.deleteTestCaseViaApi(tc3Id)
  })

  it('06.1 Filter "all" → 3 cases', () => {
    cy.visit(`/dashboard/#/test-plans/runs/${runId}`)
    cy.get('.run-view-overlay', { timeout: 10000 }).should('exist')
    cy.get('.filter-select').select('all')
    cy.get('.case-item').should('have.length', 3)
  })

  it('06.2 Filter "passed" → 1 case', () => {
    cy.get('.filter-select').select('passed')
    cy.get('.case-item').should('have.length', 1)
    cy.get('.case-item').should('contain.text', 'CY-TC-Filter-Pass')
  })

  it('06.3 Filter "failed" → 1 case', () => {
    cy.get('.filter-select').select('failed')
    cy.get('.case-item').should('have.length', 1)
  })

  it('06.4 Filter "untested" → 1 case', () => {
    cy.get('.filter-select').select('untested')
    cy.get('.case-item').should('have.length', 1)
  })

  it('06.5 Filter "all" again → counters show correct values', () => {
    cy.get('.filter-select').select('all')
    cy.get('.counter-item.passed').should('contain.text', '1')
    cy.get('.counter-item.failed').should('contain.text', '1')
  })
})

// ═══════════════════════════════════════════════════════
// TP-07: Run history (3 tests)
// ═══════════════════════════════════════════════════════

describe('TP-07: История прогонов', () => {
  let planId, tcId, run1Id, run2Id

  before(() => {
    cy.loginToApp()
    cy.createTestPlanViaApi('CY-History-Plan')
    cy.get('@planId').then(id => { planId = id })
    cy.createTestCaseViaApi({ title: 'CY-TC-History' })
    cy.get('@testCaseId').then(id => {
      tcId = id
      cy.addCaseToPlanViaApi(planId, tcId)
      // Run 1 — complete
      cy.startTestPlanRunViaApi(planId, 'CY-Run-History-1')
    })
    cy.get('@runId').then(id => {
      run1Id = id
      cy.recordResultViaApi(run1Id, tcId, 'passed')
      cy.finishRunViaApi(run1Id)
      // Run 2 — in progress
      cy.startTestPlanRunViaApi(planId, 'CY-Run-History-2')
    })
    cy.get('@runId').then(id => { run2Id = id })
  })

  after(() => {
    if (planId) cy.deleteTestPlanViaApi(planId)
    if (tcId) cy.deleteTestCaseViaApi(tcId)
  })

  it('07.1 GET /{planId}/runs → 2 runs', () => {
    cy.request({
      method: 'GET',
      url: `/api/v1/test-plans/${planId}/runs`,
      headers: apiHeaders(),
    }).then(resp => {
      expect(resp.body).to.have.length(2)
    })
  })

  it('07.2 GET /project/{pid}/runs → both runIds present', () => {
    cy.request({
      method: 'GET',
      url: `/api/v1/test-plans/project/${PID}/runs`,
      headers: apiHeaders(),
    }).then(resp => {
      const ids = resp.body.map(r => r.id)
      expect(ids).to.include(run1Id)
      expect(ids).to.include(run2Id)
    })
  })

  it('07.3 GET /test-plans → plan with runs_count=2', () => {
    cy.request({
      method: 'GET',
      url: `/api/v1/test-plans?project_id=${PID}`,
      headers: apiHeaders(),
    }).then(resp => {
      const plan = resp.body.find(p => p.id === planId)
      expect(plan).to.exist
      expect(plan.runs_count).to.eq(2)
    })
  })
})

// ═══════════════════════════════════════════════════════
// TP-08: Delete plan (3 tests)
// ═══════════════════════════════════════════════════════

describe('TP-08: Удаление плана', () => {
  let planId, tcId, runId

  before(() => {
    cy.loginToApp()
    cy.createTestPlanViaApi('CY-Delete-Plan')
    cy.get('@planId').then(id => { planId = id })
    cy.createTestCaseViaApi({ title: 'CY-TC-Delete' })
    cy.get('@testCaseId').then(id => {
      tcId = id
      cy.addCaseToPlanViaApi(planId, tcId)
      cy.startTestPlanRunViaApi(planId, 'CY-Run-Delete')
    })
    cy.get('@runId').then(id => { runId = id })
  })

  after(() => {
    if (tcId) cy.deleteTestCaseViaApi(tcId)
  })

  it('08.1 DELETE /test-plans/{id} → 204', () => {
    cy.request({
      method: 'DELETE',
      url: `/api/v1/test-plans/${planId}`,
      headers: apiHeaders(),
    }).then(resp => {
      expect(resp.status).to.eq(204)
    })
  })

  it('08.2 GET /runs/{runId} → 404 (cascade)', () => {
    cy.request({
      method: 'GET',
      url: `/api/v1/test-plans/runs/${runId}`,
      headers: apiHeaders(),
      failOnStatusCode: false,
    }).then(resp => {
      expect(resp.status).to.eq(404)
    })
  })

  it('08.3 GET /test-plans/{id} → 404', () => {
    cy.request({
      method: 'GET',
      url: `/api/v1/test-plans/${planId}`,
      headers: apiHeaders(),
      failOnStatusCode: false,
    }).then(resp => {
      expect(resp.status).to.eq(404)
    })
  })
})

// ═══════════════════════════════════════════════════════
// TP-09: API Edge Cases (6 tests)
// ═══════════════════════════════════════════════════════

describe('TP-09: API Edge Cases', () => {
  let planId, tcId, runId

  before(() => {
    cy.loginToApp()
    cy.createTestPlanViaApi('CY-Edge-Plan')
    cy.get('@planId').then(id => { planId = id })
    cy.createTestCaseViaApi({ title: 'CY-TC-Edge' })
    cy.get('@testCaseId').then(id => {
      tcId = id
      cy.addCaseToPlanViaApi(planId, tcId)
      cy.startTestPlanRunViaApi(planId, 'CY-Run-Edge')
    })
    cy.get('@runId').then(id => { runId = id })
  })

  after(() => {
    if (planId) cy.deleteTestPlanViaApi(planId)
    if (tcId) cy.deleteTestCaseViaApi(tcId)
  })

  it('09.1 PUT results nonexistent run → 404', () => {
    cy.request({
      method: 'PUT',
      url: `/api/v1/test-plans/runs/00000000-0000-0000-0000-000000000000/results/${tcId}`,
      headers: apiHeaders(),
      body: { status: 'passed' },
      failOnStatusCode: false,
    }).then(resp => {
      expect(resp.status).to.eq(404)
    })
  })

  it('09.2 PUT results alien testcase → 404', () => {
    cy.request({
      method: 'PUT',
      url: `/api/v1/test-plans/runs/${runId}/results/00000000-0000-0000-0000-000000000000`,
      headers: apiHeaders(),
      body: { status: 'passed' },
      failOnStatusCode: false,
    }).then(resp => {
      expect(resp.status).to.eq(404)
    })
  })

  it('09.3 PUT results invalid status → 400', () => {
    cy.request({
      method: 'PUT',
      url: `/api/v1/test-plans/runs/${runId}/results/${tcId}`,
      headers: apiHeaders(),
      body: { status: 'invalid_status' },
      failOnStatusCode: false,
    }).then(resp => {
      expect(resp.status).to.eq(400)
    })
  })

  it('09.4 POST runs nonexistent plan → 404', () => {
    cy.request({
      method: 'POST',
      url: `/api/v1/test-plans/00000000-0000-0000-0000-000000000000/runs`,
      headers: apiHeaders(),
      body: { name: 'CY-Ghost-Run' },
      failOnStatusCode: false,
    }).then(resp => {
      expect(resp.status).to.eq(404)
    })
  })

  it('09.5 POST cases empty array → 200', () => {
    cy.request({
      method: 'POST',
      url: `/api/v1/test-plans/${planId}/cases`,
      headers: apiHeaders(),
      body: { testcase_ids: [] },
      failOnStatusCode: false,
    }).then(resp => {
      expect(resp.status).to.eq(200)
      expect(resp.body.added).to.eq(0)
    })
  })

  it('09.6 GET /runs without auth → 401', () => {
    cy.request({
      method: 'GET',
      url: `/api/v1/test-plans/runs/${runId}`,
      failOnStatusCode: false,
    }).then(resp => {
      expect(resp.status).to.be.oneOf([401, 403])
    })
  })
})

// ═══════════════════════════════════════════════════════
// TP-10: UI Flow — полное прохождение (7 tests)
// ═══════════════════════════════════════════════════════

describe('TP-10: UI Flow — полное прохождение', () => {
  let planId, tcId, runId

  before(() => {
    cy.loginToApp()
    cy.createTestCaseViaApi({
      title: 'CY-TC-UIFlow',
      steps: JSON.stringify([
        { action: 'Open login page', expected: 'Login form visible' },
        { action: 'Enter credentials', expected: 'Fields populated' },
      ])
    })
    cy.get('@testCaseId').then(id => { tcId = id })
    cy.createTestPlanViaApi('CY-UIFlow-Plan')
    cy.get('@planId').then(id => {
      planId = id
      cy.addCaseToPlanViaApi(planId, tcId)
      cy.startTestPlanRunViaApi(planId, 'CY-Run-UIFlow')
    })
    cy.get('@runId').then(id => { runId = id })
  })

  after(() => {
    if (planId) cy.deleteTestPlanViaApi(planId)
    if (tcId) cy.deleteTestCaseViaApi(tcId)
  })

  it('10.1 Visit run → case items visible', () => {
    cy.visit(`/dashboard/#/test-plans/runs/${runId}`)
    cy.get('.case-item', { timeout: 10000 }).should('have.length', 1)
  })

  it('10.2 Click case → steps table visible with 2 rows', () => {
    cy.get('.case-item').first().click()
    cy.get('.steps-table', { timeout: 5000 }).should('exist')
    cy.get('.steps-table tbody tr').should('have.length', 2)
  })

  it('10.3 Click "Passed" → button active, Save enabled', () => {
    cy.get('.result-btn.passed').click()
    cy.get('.result-btn.passed').should('have.class', 'active')
    cy.get('[data-testid="save-result-btn"]').should('not.be.disabled')
  })

  it('10.4 Click "Save Result" → intercept PUT → 200, stripe.passed', () => {
    cy.intercept('PUT', '**/results/*').as('saveResult')
    cy.get('[data-testid="save-result-btn"]').click()
    cy.wait('@saveResult').its('response.statusCode').should('eq', 200)
    cy.get('.case-item-stripe.passed', { timeout: 5000 }).should('exist')
  })

  it('10.5 Reload → counter shows 1 passed', () => {
    cy.reload()
    cy.get('.run-view-overlay', { timeout: 10000 }).should('exist')
    cy.get('.counter-item.passed').should('contain.text', '1')
  })

  it('10.6 Click "Finish Run" → confirm → status completed', () => {
    cy.on('window:confirm', () => true)
    cy.get('.btn-finish').click()
    cy.get('.row-status.completed', { timeout: 5000 }).should('exist')
  })

  it('10.7 Click "Back" → URL does not contain /runs/', () => {
    cy.get('.btn-back').click()
    cy.url().should('not.include', '/runs/')
  })
})
