<template>
  <div class="qa-dashboard">
    <div v-if="store.dashboardLoading" class="dash-loading">Loading...</div>

    <div v-else-if="!store.dashboard" class="dash-empty">
      <p>Нет данных для отображения</p>
      <p class="dash-empty-hint">Запустите первый тест-план чтобы увидеть метрики</p>
    </div>

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

      <!-- Card 3: Trend passed/failed -->
      <div class="dash-card dash-card-wide">
        <h4 class="card-title">Trend: Passed / Failed</h4>
        <div class="chart-wrap" v-if="hasTrendData">
          <canvas ref="trendCanvas"></canvas>
        </div>
        <div v-else class="card-empty">Недостаточно прогонов</div>
      </div>

      <!-- Card 4: Coverage by folder -->
      <div class="dash-card">
        <h4 class="card-title">Coverage by Folder</h4>
        <div class="chart-wrap" v-if="hasCoverageData">
          <canvas ref="coverageCanvas"></canvas>
        </div>
        <div v-else class="card-empty">Нет данных по папкам</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import {
  Chart,
  DoughnutController, ArcElement,
  LineController, LineElement, PointElement, LinearScale, CategoryScale,
  BarController, BarElement,
  Tooltip, Legend
} from 'chart.js'
import { useQAStore } from '@/stores/qa'

Chart.register(
  DoughnutController, ArcElement,
  LineController, LineElement, PointElement, LinearScale, CategoryScale,
  BarController, BarElement,
  Tooltip, Legend
)

const props = defineProps({
  projectId: { type: String, required: true }
})

const store = useQAStore()
const chartCanvas = ref(null)
const trendCanvas = ref(null)
const coverageCanvas = ref(null)
let chartInstance = null
let trendChart = null
let coverageChart = null

const topFailed = computed(() => store.dashboard?.top_failed || [])

const hasStatusData = computed(() => {
  const s = store.dashboard?.plans_by_status
  if (!s) return false
  return Object.values(s).some(v => v > 0)
})

const hasTrendData = computed(() => {
  const t = store.dashboard?.trend
  return t && t.length > 0
})

const hasCoverageData = computed(() => {
  const c = store.dashboard?.coverage
  return c && Object.keys(c).length > 0
})

function getCssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
    || getComputedStyle(document.body).getPropertyValue(name).trim()
}

function getStatusColors(labels) {
  return labels.map(label => {
    switch (label) {
      case 'active':
      case 'ready':      return getCssVar('--success')
      case 'approved':   return getCssVar('--accent')
      case 'archived':   return getCssVar('--text-secondary')
      case 'needs_work': return getCssVar('--warning')
      case 'draft':
      default:           return getCssVar('--accent-hover') || getCssVar('--accent')
    }
  })
}

let themeObserver = null

function buildChart() {
  if (!chartCanvas.value || !store.dashboard?.plans_by_status) return
  destroyChart()

  const data = store.dashboard.plans_by_status
  const labels = Object.keys(data)
  const values = Object.values(data)
  const colors = getStatusColors(labels)

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

function buildTrendChart() {
  if (!trendCanvas.value || !hasTrendData.value) return
  if (trendChart) { trendChart.destroy(); trendChart = null }

  const trend = store.dashboard.trend
  const labels = trend.map(p => p.date || p.label || '')
  const passed = trend.map(p => p.passed || 0)
  const failed = trend.map(p => p.failed || 0)

  trendChart = new Chart(trendCanvas.value, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Passed',
          data: passed,
          borderColor: getCssVar('--success'),
          backgroundColor: 'transparent',
          tension: 0.3,
          pointRadius: 4,
        },
        {
          label: 'Failed',
          data: failed,
          borderColor: getCssVar('--error'),
          backgroundColor: 'transparent',
          tension: 0.3,
          pointRadius: 4,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: getCssVar('--text-primary'), font: { size: 12 } } },
        tooltip: {
          backgroundColor: getCssVar('--bg-card'),
          titleColor: getCssVar('--text-primary'),
          bodyColor: getCssVar('--text-secondary'),
          borderColor: getCssVar('--border-color'),
          borderWidth: 1
        }
      },
      scales: {
        x: { ticks: { color: getCssVar('--text-secondary') }, grid: { color: getCssVar('--border-color') } },
        y: { ticks: { color: getCssVar('--text-secondary') }, grid: { color: getCssVar('--border-color') } }
      }
    }
  })
}

function buildCoverageChart() {
  if (!coverageCanvas.value || !hasCoverageData.value) return
  if (coverageChart) { coverageChart.destroy(); coverageChart = null }

  const coverage = store.dashboard.coverage
  const labels = Object.keys(coverage)
  const values = Object.values(coverage)

  coverageChart = new Chart(coverageCanvas.value, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: '% covered',
        data: values,
        backgroundColor: getCssVar('--accent-muted'),
        borderColor: getCssVar('--accent'),
        borderWidth: 1,
        borderRadius: 4,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: getCssVar('--bg-card'),
          titleColor: getCssVar('--text-primary'),
          bodyColor: getCssVar('--text-secondary'),
          borderColor: getCssVar('--border-color'),
          borderWidth: 1,
          callbacks: { label: ctx => `${ctx.raw}%` }
        }
      },
      scales: {
        x: { ticks: { color: getCssVar('--text-secondary') }, grid: { display: false } },
        y: {
          min: 0, max: 100,
          ticks: { color: getCssVar('--text-secondary'), callback: v => `${v}%` },
          grid: { color: getCssVar('--border-color') }
        }
      }
    }
  })
}

onMounted(async () => {
  await store.fetchDashboard(props.projectId)
  await nextTick()
  buildChart()
  buildTrendChart()
  buildCoverageChart()

  themeObserver = new MutationObserver(() => {
    buildChart()
    buildTrendChart()
    buildCoverageChart()
  })
  themeObserver.observe(document.body, { attributes: true, attributeFilter: ['class'] })
})

watch(() => store.dashboard, async () => {
  await nextTick()
  buildChart()
  buildTrendChart()
  buildCoverageChart()
})

onBeforeUnmount(() => {
  destroyChart()
  if (trendChart) { trendChart.destroy(); trendChart = null }
  if (coverageChart) { coverageChart.destroy(); coverageChart = null }
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
.dash-empty-hint {
  font-size: 12px;
  margin-top: 4px;
  opacity: 0.7;
}
.dash-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto auto;
  gap: 16px;
}
.dash-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
}
.dash-card-wide {
  grid-column: span 2;
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
