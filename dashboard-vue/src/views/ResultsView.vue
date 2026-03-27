<template>
  <div class="results-page">
    <h1>Test Results</h1>

    <StatsSummary :stats="stats" />

    <DonutChart :stats="stats" />

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
        <!-- Live running launch (if any) -->
        <TestRunCard
          v-for="run in runs"
          :key="run.id"
          :run="run"
          :expanded="expandedRuns.includes(run.id)"
          :live="liveRuns[run.id]"
          @toggle="toggleRun(run.id)"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { testRunsApi } from '@/services/api'
import StatsSummary from '@/components/results/StatsSummary.vue'
import DonutChart from '@/components/results/DonutChart.vue'
import TestRunCard from '@/components/results/TestRunCard.vue'

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
const liveRuns = reactive({})
let pollInterval = null

async function toggleRun(runId) {
  const idx = expandedRuns.value.indexOf(runId)
  if (idx >= 0) {
    expandedRuns.value.splice(idx, 1)
  } else {
    const run = runs.value.find(r => r.id === runId)
    if (run && !run.results) {
      try {
        const res = await testRunsApi.get(runId)
        Object.assign(run, res.data)
      } catch (err) {
        console.error('Failed to load run details:', err)
      }
    }
    // Connect WS for running launches
    if (run && run.status === 'running') {
      connectLiveWs(run)
    }
    expandedRuns.value.push(runId)
  }
}

function connectLiveWs(run) {
  const wsUrl = (import.meta.env.VITE_API_URL || window.location.origin).replace('http', 'ws')
  const ws = new WebSocket(`${wsUrl}/ws/launches/${run.id}`)

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'launch_batch') {
      if (data.tests) {
        run.results = [...(run.results || []), ...data.tests]
      }
      run.passed = data.passed || 0
      run.failed = data.failed || 0
      run.skipped = data.skipped || 0
      run.total_tests = data.total || run.total_tests
      liveRuns[run.id] = true
    } else if (data.type === 'launch_completed') {
      run.status = data.status || 'passed'
      run.passed = data.passed || run.passed
      run.failed = data.failed || run.failed
      run.skipped = data.skipped || run.skipped
      run.duration_ms = data.duration_ms || run.duration_ms
      delete liveRuns[run.id]
      ws.close()
    }
  }

  ws.onclose = () => { delete liveRuns[run.id] }
}

async function refreshRuns() {
  try {
    const runsRes = await testRunsApi.list(5)
    const newRuns = runsRes.data
    // Merge: keep expanded run details, add new runs
    for (const nr of newRuns) {
      const existing = runs.value.find(r => r.id === nr.id)
      if (existing) {
        // Update status/counts but keep results if loaded
        existing.status = nr.status
        existing.passed = nr.passed
        existing.failed = nr.failed
        existing.skipped = nr.skipped
        existing.total_tests = nr.total_tests
        existing.duration_ms = nr.duration_ms
      } else {
        runs.value.unshift(nr)
      }
    }
    // Trim to latest 10
    if (runs.value.length > 10) runs.value.length = 10
  } catch (err) {
    // silent
  }
}

onMounted(async () => {
  try {
    const [statsRes, runsRes] = await Promise.all([
      testRunsApi.getStats(),
      testRunsApi.list(5)
    ])

    stats.value = statsRes.data
    runs.value = runsRes.data

    // Auto-connect WS for running launches
    for (const run of runs.value) {
      if (run.status === 'running') {
        connectLiveWs(run)
      }
    }
  } catch (error) {
    console.error('Failed to load test results:', error)
  } finally {
    loading.value = false
  }

  // Poll for new launches every 10s
  pollInterval = setInterval(refreshRuns, 10000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
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

.runs-section h2 {
  margin-bottom: 16px;
}

.loading {
  display: flex;
  justify-content: center;
  padding: 40px;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}

.empty-state .hint {
  font-size: 14px;
  margin-top: 8px;
}
</style>
