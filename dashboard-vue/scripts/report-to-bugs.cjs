#!/usr/bin/env node
/**
 * EL072 Bug Reporter
 * Читает mochawesome JSON-отчёты и заводит баги через ErrorLens API.
 *
 * Usage:
 *   node scripts/report-to-bugs.js <base_url> <report1.json> [report2.json...]
 *
 * Env vars:
 *   EL_USERNAME  — логин (default: admin)
 *   EL_PASSWORD  — пароль (default: Misha2026)
 *   EL_PROJECT   — project_id (default: 9ddfd925-9728-4224-8a3d-13a6e2e01719)
 */

const fs = require('fs')
const https = require('https')
const http = require('http')

const BASE_URL   = process.argv[2] || 'http://192.168.1.74:3000'
const REPORT_FILES = process.argv.slice(3).filter(f => fs.existsSync(f))

const EL_USERNAME = process.env.EL_USERNAME || 'admin'
const EL_PASSWORD = process.env.EL_PASSWORD || 'Misha2026'
const EL_PROJECT  = process.env.EL_PROJECT  || '9ddfd925-9728-4224-8a3d-13a6e2e01719'

// ─── HTTP helpers ─────────────────────────────────────────────────────────────

function request(options, body = null) {
  return new Promise((resolve, reject) => {
    const lib = options.protocol === 'https:' ? https : http
    const req = lib.request(options, res => {
      let data = ''
      res.on('data', chunk => { data += chunk })
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(data) }) }
        catch { resolve({ status: res.statusCode, body: data }) }
      })
    })
    req.on('error', reject)
    if (body) req.write(JSON.stringify(body))
    req.end()
  })
}

async function apiRequest(method, path, body = null, token = null) {
  const url = new URL(BASE_URL + path)
  const options = {
    protocol: url.protocol,
    hostname: url.hostname,
    port: url.port || (url.protocol === 'https:' ? 443 : 80),
    path: url.pathname + url.search,
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    }
  }
  return request(options, body)
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

async function login() {
  console.log(`Logging in as ${EL_USERNAME}...`)
  const resp = await apiRequest('POST', '/api/auth/login', {
    username: EL_USERNAME,
    password: EL_PASSWORD
  })
  if (resp.status !== 200) {
    throw new Error(`Login failed: ${resp.status} ${JSON.stringify(resp.body)}`)
  }
  return resp.body.access_token
}

// ─── Get task type ids ─────────────────────────────────────────────────────────

async function getBugTypeId(token) {
  const resp = await apiRequest('GET', `/api/task-settings/types?project_id=${EL_PROJECT}`, null, token)
  if (!resp.body || !Array.isArray(resp.body)) return null
  const bug = resp.body.find(t => t.slug === 'bug')
  return bug?.id || null
}

// ─── Parse mochawesome JSON ───────────────────────────────────────────────────

function extractFailures(reportFile) {
  const raw = fs.readFileSync(reportFile, 'utf8')
  const report = JSON.parse(raw)
  const failures = []

  function walkSuite(suite, parentTitle = '') {
    const suiteTitle = parentTitle
      ? `${parentTitle} > ${suite.title}`
      : suite.title

    // Direct tests in this suite
    for (const test of (suite.tests || [])) {
      if (test.state === 'failed' || test.fail === true) {
        failures.push({
          suite: suiteTitle,
          title: test.title,
          fullTitle: `${suiteTitle} > ${test.title}`,
          error: test.err?.message || test.err?.estack || 'Unknown error',
          stack: test.err?.stack || test.err?.estack || '',
          duration: test.duration || 0,
        })
      }
    }

    // Recurse into child suites
    for (const child of (suite.suites || [])) {
      walkSuite(child, suiteTitle)
    }
  }

  // mochawesome has results[].suites structure
  const results = report.results || []
  for (const result of results) {
    for (const suite of (result.suites || [])) {
      walkSuite(suite)
    }
  }

  return failures
}

// ─── Determine severity from test title and error ────────────────────────────

function determineSeverity(failure) {
  const title = (failure.fullTitle + ' ' + failure.error).toLowerCase()

  if (title.includes('500') || title.includes('internal server error')) {
    return 'critical'
  }
  if (title.includes('404') || title.includes('not found') && title.includes('url')) {
    return 'critical'
  }
  if (title.includes('crud-01') || title.includes('lifecycle') || title.includes('delete')) {
    return 'high'
  }
  if (title.includes('deep url') || title.includes('type filter') || title.includes('jql')) {
    return 'high'
  }
  if (title.includes('crud') || title.includes('save') || title.includes('create')) {
    return 'high'
  }
  if (title.includes('ui') || title.includes('toc') || title.includes('breadcrumb')) {
    return 'medium'
  }
  return 'medium'
}

// ─── Create bug in ErrorLens ──────────────────────────────────────────────────

async function createBug(failure, token, bugTypeId) {
  const severity = determineSeverity(failure)
  const priority = severity === 'critical' ? 'high'
    : severity === 'high' ? 'high'
    : 'medium'

  // Обрезать stack до первых 500 символов
  const errorDetail = failure.error.slice(0, 300)
  const stackDetail = failure.stack
    ? '\n\nStack:\n' + failure.stack.split('\n').slice(0, 5).join('\n')
    : ''

  const description =
    `**Cypress Test Failed:** ${failure.fullTitle}\n\n` +
    `**Error:** ${errorDetail}${stackDetail}\n\n` +
    `**Test Duration:** ${failure.duration}ms\n\n` +
    `**Expected:** Test should pass without assertion errors\n` +
    `**Actual:** ${errorDetail}\n\n` +
    `**Source:** EL072 CRUD Test Suite`

  const body = {
    title: `[E2E] ${failure.suite}: ${failure.title}`,
    description,
    type_id: bugTypeId,
    priority,
    severity,
    status: 'todo',
    project_id: EL_PROJECT,
    labels: ['el072', 'e2e-failure', 'cypress'],
    environment: 'staging',
  }

  const resp = await apiRequest('POST', '/api/tasks', body, token)

  if (resp.status === 200 || resp.status === 201) {
    return resp.body
  } else {
    console.warn(`  Failed to create bug: ${resp.status} ${JSON.stringify(resp.body).slice(0, 200)}`)
    return null
  }
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  if (REPORT_FILES.length === 0) {
    console.log('No report files found. Run tests first:')
    console.log('  npm run test:issues')
    console.log('  npm run test:articles')
    process.exit(1)
  }

  let token, bugTypeId
  try {
    token = await login()
    bugTypeId = await getBugTypeId(token)
    console.log(`Bug type ID: ${bugTypeId || 'not found — using null'}`)
  } catch (err) {
    console.error(`Auth failed: ${err.message}`)
    process.exit(1)
  }

  // Собрать все провалы
  const allFailures = []
  for (const file of REPORT_FILES) {
    console.log(`\nParsing: ${file}`)
    try {
      const failures = extractFailures(file)
      console.log(`  Found ${failures.length} failures`)
      allFailures.push(...failures)
    } catch (err) {
      console.warn(`  Could not parse ${file}: ${err.message}`)
    }
  }

  if (allFailures.length === 0) {
    console.log('\nNo failures found — no bugs to file!')
    return
  }

  console.log(`\n=== Filing ${allFailures.length} bugs in ErrorLens ===`)

  // Дедупликация по fullTitle — не создавать дубли
  const seen = new Set()
  let created = 0
  let skipped = 0

  for (const failure of allFailures) {
    if (seen.has(failure.fullTitle)) {
      skipped++
      continue
    }
    seen.add(failure.fullTitle)

    process.stdout.write(`  [${created + 1}/${allFailures.length}] ${failure.title.slice(0, 60)}...`)
    const bug = await createBug(failure, token, bugTypeId)
    if (bug) {
      console.log(` ${bug.human_id}`)
      created++
    } else {
      console.log(` failed`)
    }

    // Небольшая пауза чтобы не перегружать API
    await new Promise(r => setTimeout(r, 200))
  }

  console.log(`\n=== Bug Filing Complete ===`)
  console.log(`  Created : ${created}`)
  console.log(`  Skipped : ${skipped}`)
  console.log(`  Total   : ${allFailures.length}`)
  console.log(`\nView bugs: ${BASE_URL}/dashboard/#/issues`)

  // Записать итоговый отчёт
  const reportSummary = {
    run_date: new Date().toISOString(),
    base_url: BASE_URL,
    total_failures: allFailures.length,
    bugs_created: created,
    bugs_skipped: skipped,
    failures: allFailures.map(f => ({
      suite: f.suite,
      title: f.title,
      severity: determineSeverity(f),
      error: f.error.slice(0, 200),
    }))
  }

  const summaryFile = `cypress/reports/bug-report-${new Date().toISOString().replace(/[:.]/g, '-')}.json`
  fs.writeFileSync(summaryFile, JSON.stringify(reportSummary, null, 2))
  console.log(`\nSummary saved: ${summaryFile}`)
}

main().catch(err => {
  console.error('Fatal error:', err.message)
  process.exit(1)
})
