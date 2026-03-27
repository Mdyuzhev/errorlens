<template>
  <div class="qa-dashboard">
    <div v-if="store.dashboardLoading" class="dash-loading">Loading...</div>

    <div v-else-if="!store.dashboard" class="dash-empty">No data</div>

    <div v-else class="dash-grid">
      <!-- Card 1: By Status (Doughnut) -->
      <div class="dash-card">
        <h4 class="card-title">Plans by Status</h4>
        <div class="chart-wrap">
          <canvas ref="chartCanvas"></canvas>
        </div>
        <div v-if="!hasStatusData" class="card-empty">No plans yet</div>
      </div>

      <!-- Card 2: Top Flaky Cases -->
      <div class="dash-card">
        <h4 class="card-title">Top Flaky Cases</h4>
        <div v-if="topFailed.length" class="flaky-list">
          <div v-for="item in topFailed" :key="item.id" class="flaky-row">
            <span class="flaky-name">{{ item.title || item.name }}</span>
            <span class="flaky-count">{{ item.failed_count }}</span>
          </div>
        </div>
        <div v-else class="card-empty">No failed cases</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { Chart, DoughnutController, ArcElement, Tooltip, Legend } from 'chart.js'
import { useQAStore } from '@/stores/qa'

Chart.register(DoughnutController, ArcElement, Tooltip, Legend)

const props = defineProps({
  projectId: { type: String, required: true }
})

const store = useQAStore()
const chartCanvas = ref(null)
let chartInstance = null

const statusColors = {
  draft: '#6b7280',
  ready: '#10b981',
  approved: '#9b7de0',
  needs_work: '#f59e0b'
}

const topFailed = computed(() => store.dashboard?.top_failed || [])

const hasStatusData = computed(() => {
  const s = store.dashboard?.by_status
  if (!s) return false
  return Object.values(s).some(v => v > 0)
})

function getCssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
    || getComputedStyle(document.body).getPropertyValue(name).trim()
}

let themeObserver = null

function buildChart() {
  if (!chartCanvas.value || !store.dashboard?.by_status) return
  destroyChart()

  const data = store.dashboard.by_status
  const labels = Object.keys(data)
  const values = Object.values(data)
  const colors = labels.map(l => statusColors[l] || '#4a4858')

  chartInstance = new Chart(chartCanvas.value, {
    type: 'doughnut',
    data: {
      labels: labels.map(l => l.replace('_', ' ')),
      datasets: [{
        data: values,
        backgroundColor: colors,
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: getCssVar('--text-primary'),
            padding: 12,
            font: { size: 12 }
          }
        },
        tooltip: {
          backgroundColor: getCssVar('--bg-card'),
          titleColor: getCssVar('--text-primary'),
          bodyColor: getCssVar('--text-secondary'),
          borderColor: getCssVar('--border-color'),
          borderWidth: 1
        }
      }
    }
  })
}

function destroyChart() {
  if (chartInstance) {
    chartInstance.destroy()
    chartInstance = null
  }
}

onMounted(async () => {
  await store.fetchDashboard(props.projectId)
  await nextTick()
  buildChart()

  themeObserver = new MutationObserver(() => {
    buildChart()
  })
  themeObserver.observe(document.body, { attributes: true, attributeFilter: ['class'] })
})

watch(() => store.dashboard, async () => {
  await nextTick()
  buildChart()
})

onBeforeUnmount(() => {
  destroyChart()
  if (themeObserver) { themeObserver.disconnect(); themeObserver = null }
})
</script>

<style scoped>
.qa-dashboard {
  padding: 0;
}
.dash-loading,
.dash-empty {
  color: var(--text-secondary);
  text-align: center;
  padding: 32px;
  font-size: 13px;
}
.dash-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.dash-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
}
.card-title {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 16px 0;
}
.chart-wrap {
  height: 220px;
  position: relative;
}
.card-empty {
  color: var(--text-secondary);
  text-align: center;
  padding: 24px;
  font-size: 13px;
}
.flaky-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.flaky-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-radius: 4px;
  border-bottom: 1px solid var(--border-color);
}
.flaky-row:hover {
  background: var(--bg-tertiary);
}
.flaky-name {
  color: var(--text-primary);
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  margin-right: 12px;
}
.flaky-count {
  color: var(--error);
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}
</style>
