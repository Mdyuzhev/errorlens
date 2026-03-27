<template>
  <div class="dashboard-view">
    <div v-if="loading" class="loading-state">Loading dashboard...</div>

    <div v-else-if="data" class="dashboard-grid">
      <!-- By Type -->
      <div class="dash-card">
        <h3>By Type</h3>
        <div v-if="data.by_type?.length" class="bar-chart">
          <div v-for="item in data.by_type" :key="item.name" class="bar-chart-row">
            <span class="bar-chart-label">{{ item.name }}</span>
            <div class="bar-chart-track">
              <div
                class="bar-chart-fill"
                :style="{ width: barWidth(item.count, maxByType) + '%', background: item.color || 'var(--accent)' }"
              ></div>
            </div>
            <span class="bar-chart-count">{{ item.count }}</span>
          </div>
        </div>
        <div v-else class="empty-hint">No data</div>
      </div>

      <!-- By Priority -->
      <div class="dash-card">
        <h3>By Priority</h3>
        <div v-if="data.by_priority?.length" class="bar-chart">
          <div v-for="item in data.by_priority" :key="item.name" class="bar-chart-row">
            <span class="bar-chart-label">{{ item.name }}</span>
            <div class="bar-chart-track">
              <div
                class="bar-chart-fill"
                :style="{ width: barWidth(item.count, maxByPriority) + '%', background: priorityColor(item.name) }"
              ></div>
            </div>
            <span class="bar-chart-count">{{ item.count }}</span>
          </div>
        </div>
        <div v-else class="empty-hint">No data</div>
      </div>

      <!-- Top Assignees -->
      <div class="dash-card">
        <h3>Top Assignees</h3>
        <div v-if="data.by_assignee?.length" class="list-stats">
          <div v-for="item in data.by_assignee" :key="item.name" class="list-stat-row">
            <span class="list-stat-name">{{ item.name || 'Unassigned' }}</span>
            <span class="list-stat-badge">{{ item.count }}</span>
          </div>
        </div>
        <div v-else class="empty-hint">No data</div>
      </div>

      <!-- By Component -->
      <div class="dash-card">
        <h3>By Component</h3>
        <div v-if="data.by_component?.length" class="list-stats">
          <div v-for="item in data.by_component" :key="item.name" class="list-stat-row">
            <span class="list-stat-name">{{ item.name || 'None' }}</span>
            <span class="list-stat-badge">{{ item.count }}</span>
          </div>
        </div>
        <div v-else class="empty-hint">No data</div>
      </div>
    </div>

    <div class="dashboard-row-wide" v-if="data">
      <div class="dash-card">
        <h3>Sprint Burndown — {{ store.activeSprint?.name || 'No active sprint' }}</h3>
        <div class="chart-wrap-lg"><canvas ref="burndownCanvas"></canvas></div>
        <div v-if="!store.burndown.length" class="empty-hint">No active sprint with story points</div>
      </div>
      <div class="dash-card">
        <h3>Velocity (last {{ store.velocity.length }} sprints)</h3>
        <div class="chart-wrap-lg"><canvas ref="velocityCanvas"></canvas></div>
        <div v-if="!store.velocity.length" class="empty-hint">No completed sprints yet</div>
      </div>
    </div>

    <div v-else class="empty-state">No dashboard data available</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useIssuesStore } from '@/stores/issues'
import {
  Chart, LineController, BarController, CategoryScale, LinearScale,
  PointElement, LineElement, BarElement, Filler, Legend, Tooltip,
} from 'chart.js'

Chart.register(
  LineController, BarController, CategoryScale, LinearScale,
  PointElement, LineElement, BarElement, Filler, Legend, Tooltip,
)

const props = defineProps({
  projectId: { type: String, required: true },
})

const store = useIssuesStore()

const loading = computed(() => store.dashboardLoading)
const data = computed(() => store.dashboard)

const maxByType = computed(() => Math.max(...(data.value?.by_type?.map(i => i.count) || [1])))
const maxByPriority = computed(() => Math.max(...(data.value?.by_priority?.map(i => i.count) || [1])))

function barWidth(count, max) {
  if (!max || max === 0) return 0
  return Math.round((count / max) * 100)
}

function priorityColor(name) {
  const map = { high: 'var(--warning)', medium: 'var(--accent)', low: 'var(--text-secondary)', critical: 'var(--error)' }
  return map[name?.toLowerCase()] || 'var(--accent)'
}

function getCssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

/* ---------- Chart refs & instances ---------- */
const burndownCanvas = ref(null)
const velocityCanvas = ref(null)
let burndownChart = null
let velocityChart = null

function chartDefaults() {
  return {
    color: getCssVar('--text-secondary'),
    borderColor: getCssVar('--border-color'),
    gridColor: getCssVar('--bg-tertiary'),
  }
}

function buildBurndown() {
  if (!burndownCanvas.value || !store.burndown.length) return
  const ctx = burndownCanvas.value.getContext('2d')
  if (burndownChart) burndownChart.destroy()
  const c = chartDefaults()
  const labels = store.burndown.map(p => p.date)
  const ideal = store.burndown.map(p => p.ideal)
  const actual = store.burndown.map(p => p.remaining)

  burndownChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Ideal',
          data: ideal,
          borderColor: c.color,
          borderDash: [6, 4],
          pointRadius: 0,
          fill: false,
        },
        {
          label: 'Actual',
          data: actual,
          borderColor: getCssVar('--accent'),
          backgroundColor: getCssVar('--accent-muted'),
          pointRadius: 3,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: c.color } } },
      scales: {
        x: { ticks: { color: c.color }, grid: { color: c.gridColor } },
        y: { beginAtZero: true, ticks: { color: c.color }, grid: { color: c.gridColor } },
      },
    },
  })
}

function buildVelocity() {
  if (!velocityCanvas.value || !store.velocity.length) return
  const ctx = velocityCanvas.value.getContext('2d')
  if (velocityChart) velocityChart.destroy()
  const c = chartDefaults()
  const labels = store.velocity.map(v => v.name)

  velocityChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Committed',
          data: store.velocity.map(v => v.committed),
          backgroundColor: getCssVar('--accent-muted'),
          borderColor: getCssVar('--accent'),
          borderWidth: 1,
        },
        {
          label: 'Completed',
          data: store.velocity.map(v => v.completed),
          backgroundColor: getCssVar('--success'),
          borderColor: getCssVar('--success'),
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: c.color } } },
      scales: {
        x: { ticks: { color: c.color }, grid: { color: c.gridColor } },
        y: { beginAtZero: true, ticks: { color: c.color }, grid: { color: c.gridColor } },
      },
    },
  })
}

/* ---------- Theme observer ---------- */
let themeObserver = null

function setupThemeObserver() {
  themeObserver = new MutationObserver(() => {
    buildBurndown()
    buildVelocity()
  })
  themeObserver.observe(document.body, { attributes: true, attributeFilter: ['class'] })
}

/* ---------- Load ---------- */
async function loadDashboard() {
  if (!props.projectId) return
  await store.fetchDashboard(props.projectId)
  await store.fetchSprints(props.projectId)
  const promises = [store.fetchVelocity(props.projectId)]
  if (store.activeSprint) {
    promises.push(store.fetchBurndown(store.activeSprint.id))
  }
  await Promise.all(promises)
  await nextTick()
  buildBurndown()
  buildVelocity()
}

watch(() => store.burndown, () => { nextTick(() => buildBurndown()) })
watch(() => store.velocity, () => { nextTick(() => buildVelocity()) })

onMounted(() => {
  loadDashboard()
  setupThemeObserver()
})

onBeforeUnmount(() => {
  if (burndownChart) burndownChart.destroy()
  if (velocityChart) velocityChart.destroy()
  if (themeObserver) themeObserver.disconnect()
})

watch(() => props.projectId, loadDashboard)
</script>

<style scoped>
.dashboard-view { padding: 4px 0; }

.loading-state,
.empty-state {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
  font-size: 14px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

@media (max-width: 768px) {
  .dashboard-grid { grid-template-columns: 1fr; }
}

.dash-card {
  background: var(--bg-card);
  border-radius: 12px;
  padding: 16px;
}

.dash-card h3 {
  margin: 0 0 14px 0;
  font-size: 14px;
  color: var(--text-primary);
}

/* Bar chart */
.bar-chart-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.bar-chart-label {
  width: 100px;
  font-size: 13px;
  text-align: right;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-chart-track {
  flex: 1;
  height: 20px;
  background: var(--bg-secondary);
  border-radius: 4px;
  overflow: hidden;
}

.bar-chart-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}

.bar-chart-count {
  width: 30px;
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 600;
}

/* List stats */
.list-stats {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.list-stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid var(--bg-secondary);
  font-size: 13px;
}

.list-stat-row:last-child { border-bottom: none; }

.list-stat-name { color: var(--text-primary); }

.list-stat-badge {
  background: var(--bg-secondary);
  color: var(--text-primary);
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
}

.empty-hint {
  font-size: 12px;
  color: var(--text-secondary);
  font-style: italic;
}

.dashboard-row-wide {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 16px;
}

.chart-wrap-lg {
  height: 260px;
  position: relative;
}

@media (max-width: 768px) {
  .dashboard-row-wide { grid-template-columns: 1fr; }
}
</style>
