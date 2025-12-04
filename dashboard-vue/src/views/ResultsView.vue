<template>
  <div class="results-page">
    <h1>Test Results</h1>

    <!-- Summary Cards -->
    <div class="summary-cards">
      <div class="card total">
        <div class="value">{{ stats.total_tests }}</div>
        <div class="label">Total Tests</div>
      </div>
      <div class="card passed">
        <div class="value">{{ stats.passed }}</div>
        <div class="label">Passed</div>
      </div>
      <div class="card failed">
        <div class="value">{{ stats.failed }}</div>
        <div class="label">Failed</div>
      </div>
      <div class="card skipped">
        <div class="value">{{ stats.skipped }}</div>
        <div class="label">Skipped</div>
      </div>
    </div>

    <!-- Donut Chart -->
    <div class="chart-section">
      <div class="donut-chart">
        <svg viewBox="0 0 100 100">
          <!-- Background circle -->
          <circle
            cx="50" cy="50" r="40"
            fill="none"
            stroke="var(--bg-secondary)"
            stroke-width="12"
          />

          <!-- Passed segment -->
          <circle
            cx="50" cy="50" r="40"
            fill="none"
            stroke="#10b981"
            stroke-width="12"
            :stroke-dasharray="passedDash"
            stroke-dashoffset="0"
            transform="rotate(-90 50 50)"
          />

          <!-- Failed segment -->
          <circle
            cx="50" cy="50" r="40"
            fill="none"
            stroke="#ef4444"
            stroke-width="12"
            :stroke-dasharray="failedDash"
            :stroke-dashoffset="failedOffset"
            transform="rotate(-90 50 50)"
          />

          <!-- Center text -->
          <text x="50" y="45" text-anchor="middle" class="chart-percent">
            {{ stats.pass_rate }}%
          </text>
          <text x="50" y="60" text-anchor="middle" class="chart-label">
            pass rate
          </text>
        </svg>
      </div>

      <!-- Legend -->
      <div class="chart-legend">
        <div class="legend-item">
          <span class="dot passed"></span>
          Passed ({{ stats.passed }})
        </div>
        <div class="legend-item">
          <span class="dot failed"></span>
          Failed ({{ stats.failed }})
        </div>
        <div class="legend-item">
          <span class="dot skipped"></span>
          Skipped ({{ stats.skipped }})
        </div>
      </div>
    </div>

    <!-- Test Runs List -->
    <div class="runs-section">
      <h2>Recent Runs</h2>

      <div v-if="loading" class="loading">
        <div class="spinner"></div>
      </div>

      <div v-else-if="runs.length === 0" class="empty-state">
        <p>No test results yet</p>
        <p class="hint">Run tests from sessions</p>
      </div>

      <div v-else>
        <div v-for="run in runs" :key="run.id" class="run-card">
          <div class="run-header" @click="toggleRun(run.id)">
            <div class="run-status" :class="run.status">
              {{ run.status === 'passed' ? '✓' : '✗' }}
            </div>
            <div class="run-info">
              <div class="run-title">{{ run.test_type }} — {{ formatDate(run.started_at) }}</div>
              <div class="run-stats">
                <span class="passed">{{ run.passed }} passed</span>
                <span class="failed">{{ run.failed }} failed</span>
                <span class="duration">{{ formatDuration(run.duration_ms) }}</span>
              </div>
            </div>
            <div class="expand-icon">
              {{ expandedRuns.includes(run.id) ? '▼' : '▶' }}
            </div>
          </div>

          <!-- Expanded: Test Cases -->
          <div v-if="expandedRuns.includes(run.id) && run.results" class="run-details">
            <div
              v-for="test in run.results"
              :key="test.name"
              class="test-case"
              :class="test.status"
            >
              <div class="test-header" @click="toggleTest(run.id, test.name)">
                <span class="test-status">{{ test.status === 'passed' ? '✓' : '✗' }}</span>
                <span class="test-name">{{ test.name }}</span>
                <span class="test-duration">{{ test.duration || 0 }}ms</span>
              </div>

              <!-- Steps -->
              <div v-if="expandedTests.includes(`${run.id}:${test.name}`)" class="test-steps">
                <div
                  v-for="(step, idx) in (test.steps || [])"
                  :key="idx"
                  class="step"
                  :class="step.status"
                >
                  <span class="step-num">{{ idx + 1 }}</span>
                  <span class="step-action">{{ step.action }}</span>
                  <span class="step-status">{{ step.status === 'passed' ? '✓' : '✗' }}</span>
                </div>

                <!-- Error message if failed -->
                <div v-if="test.error" class="error-message">
                  <pre>{{ test.error }}</pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { testRunsApi } from '@/services/api'

const stats = ref({
  total_tests: 0,
  passed: 0,
  failed: 0,
  skipped: 0,
  pass_rate: 0
})

const runs = ref([])
const loading = ref(true)
const expandedRuns = ref([])
const expandedTests = ref([])

// Chart calculations
const circumference = 2 * Math.PI * 40

const passedDash = computed(() => {
  const percent = stats.value.total_tests > 0
    ? stats.value.passed / stats.value.total_tests
    : 0
  return `${percent * circumference} ${circumference}`
})

const failedDash = computed(() => {
  const percent = stats.value.total_tests > 0
    ? stats.value.failed / stats.value.total_tests
    : 0
  return `${percent * circumference} ${circumference}`
})

const failedOffset = computed(() => {
  const passedPercent = stats.value.total_tests > 0
    ? stats.value.passed / stats.value.total_tests
    : 0
  return -passedPercent * circumference
})

function toggleRun(runId) {
  const idx = expandedRuns.value.indexOf(runId)
  if (idx >= 0) {
    expandedRuns.value.splice(idx, 1)
  } else {
    expandedRuns.value.push(runId)
  }
}

function toggleTest(runId, testName) {
  const key = `${runId}:${testName}`
  const idx = expandedTests.value.indexOf(key)
  if (idx >= 0) {
    expandedTests.value.splice(idx, 1)
  } else {
    expandedTests.value.push(key)
  }
}

function formatDate(isoDate) {
  if (!isoDate) return ''
  return new Date(isoDate).toLocaleString('en-US', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatDuration(ms) {
  if (!ms) return '-'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

onMounted(async () => {
  try {
    const [statsRes, runsRes] = await Promise.all([
      testRunsApi.getStats(),
      testRunsApi.list(5)
    ])

    stats.value = statsRes.data
    runs.value = runsRes.data
  } catch (error) {
    console.error('Failed to load test results:', error)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.results-page {
  max-width: 1000px;
  margin: 0 auto;
}

.results-page h1 {
  margin-bottom: 24px;
}

/* Summary Cards */
.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.card {
  background: var(--bg-card);
  padding: 20px;
  border-radius: 12px;
  text-align: center;
}

.card .value {
  font-size: 32px;
  font-weight: 700;
}

.card .label {
  color: var(--text-secondary);
  font-size: 12px;
  margin-top: 4px;
}

.card.passed .value { color: #10b981; }
.card.failed .value { color: #ef4444; }
.card.skipped .value { color: #f59e0b; }

/* Donut Chart */
.chart-section {
  display: flex;
  align-items: center;
  gap: 40px;
  background: var(--bg-card);
  padding: 32px;
  border-radius: 16px;
  margin-bottom: 32px;
}

.donut-chart {
  width: 200px;
  height: 200px;
}

.donut-chart svg {
  width: 100%;
  height: 100%;
}

.chart-percent {
  font-size: 20px;
  font-weight: 700;
  fill: var(--text-primary);
}

.chart-label {
  font-size: 10px;
  fill: var(--text-secondary);
}

.chart-legend {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
}

.legend-item .dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.dot.passed { background: #10b981; }
.dot.failed { background: #ef4444; }
.dot.skipped { background: #f59e0b; }

/* Runs List */
.runs-section h2 {
  margin-bottom: 16px;
}

.run-card {
  background: var(--bg-card);
  border-radius: 12px;
  margin-bottom: 12px;
  overflow: hidden;
}

.run-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  cursor: pointer;
  transition: background 0.2s;
}

.run-header:hover {
  background: var(--bg-secondary);
}

.run-status {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
}

.run-status.passed {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.run-status.failed {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.run-info {
  flex: 1;
}

.run-title {
  font-weight: 600;
  margin-bottom: 4px;
}

.run-stats {
  font-size: 12px;
  color: var(--text-secondary);
  display: flex;
  gap: 12px;
}

.run-stats .passed { color: #10b981; }
.run-stats .failed { color: #ef4444; }

.expand-icon {
  color: var(--text-secondary);
}

/* Test Cases */
.run-details {
  border-top: 1px solid var(--bg-secondary);
  padding: 16px;
}

.test-case {
  margin-bottom: 8px;
  border-radius: 8px;
  overflow: hidden;
}

.test-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-secondary);
  cursor: pointer;
}

.test-status {
  width: 20px;
  text-align: center;
}

.test-case.passed .test-status { color: #10b981; }
.test-case.failed .test-status { color: #ef4444; }

.test-name {
  flex: 1;
  font-family: monospace;
  font-size: 13px;
}

.test-duration {
  color: var(--text-secondary);
  font-size: 12px;
}

/* Steps */
.test-steps {
  padding: 8px 12px 8px 40px;
}

.step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 12px;
  border-left: 2px solid var(--bg-secondary);
  padding-left: 12px;
  margin-left: 8px;
}

.step.passed { border-color: #10b981; }
.step.failed { border-color: #ef4444; }

.step-num {
  color: var(--text-secondary);
  min-width: 20px;
}

.step-action {
  flex: 1;
}

.step-status {
  width: 16px;
}

.step.passed .step-status { color: #10b981; }
.step.failed .step-status { color: #ef4444; }

.error-message {
  margin-top: 8px;
  padding: 12px;
  background: rgba(239, 68, 68, 0.1);
  border-radius: 8px;
  border-left: 3px solid #ef4444;
}

.error-message pre {
  margin: 0;
  font-size: 11px;
  color: #f87171;
  white-space: pre-wrap;
  word-break: break-all;
}

.loading {
  display: flex;
  justify-content: center;
  padding: 40px;
}

@media (max-width: 768px) {
  .summary-cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .chart-section {
    flex-direction: column;
  }
}
</style>
