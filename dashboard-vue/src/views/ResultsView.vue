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
        <TestRunCard
          v-for="run in runs"
          :key="run.id"
          :run="run"
          :expanded="expandedRuns.includes(run.id)"
          @toggle="toggleRun(run.id)"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
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

function toggleRun(runId) {
  const idx = expandedRuns.value.indexOf(runId)
  if (idx >= 0) {
    expandedRuns.value.splice(idx, 1)
  } else {
    expandedRuns.value.push(runId)
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
