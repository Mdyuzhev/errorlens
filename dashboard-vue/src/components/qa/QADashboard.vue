<template>
  <div class="qa-dashboard">
    <!-- Toolbar -->
    <div class="dash-toolbar">
      <h3 class="dash-title">QA Dashboard</h3>
      <button class="btn btn-sm btn-accent" @click="showPicker = !showPicker">
        + Добавить виджет
      </button>
      <div v-if="showPicker" ref="pickerRef" class="widget-picker">
        <div
          v-for="w in availableWidgets"
          :key="w.id"
          class="widget-picker-item"
          @click="addWidget(w.id)"
        >
          <span class="widget-picker-icon">{{ w.icon }}</span>
          <span class="widget-picker-label">{{ w.label }}</span>
        </div>
        <div v-if="!availableWidgets.length" class="widget-picker-empty">
          Все виджеты добавлены
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="store.dashboardLoading" class="dash-loading">
      <div class="spinner"></div>
      <span>Загрузка...</span>
    </div>

    <!-- Widget grid -->
    <div v-else-if="activeWidgetDefs.length" class="dash-grid">
      <div
        v-for="w in activeWidgetDefs"
        :key="w.id"
        class="dash-card"
        :class="{ 'dash-card--wide': w.wide }"
      >
        <div class="dash-card-header">
          <span class="dash-card-icon">{{ w.icon }}</span>
          <h4 class="dash-card-title">{{ w.label }}</h4>
          <button class="btn-remove-widget" @click="removeWidget(w.id)" title="Убрать виджет">&times;</button>
        </div>
        <component :is="getWidgetComponent(w)" :dashboard="store.dashboard" :widget="w" />
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="dash-empty">
      <p>Нет активных виджетов</p>
      <p class="dash-empty-hint">Нажмите "+ Добавить виджет" чтобы настроить панель</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick, defineComponent, h } from 'vue'
import {
  Chart, DoughnutController, ArcElement, LineController, LineElement, PointElement,
  LinearScale, CategoryScale, BarController, BarElement, Tooltip, Legend
} from 'chart.js'
import { useQAStore } from '@/stores/qa'

Chart.register(
  DoughnutController, ArcElement, LineController, LineElement, PointElement,
  LinearScale, CategoryScale, BarController, BarElement, Tooltip, Legend
)

const props = defineProps({
  projectId: { type: String, required: true }
})

const store = useQAStore()
const showPicker = ref(false)
const pickerRef = ref(null)

// ── Widget catalog ──────────────────────────────────────────
const WIDGET_CATALOG = [
  { id: 'tc_summary',    label: 'Test Cases Summary', icon: '📊', type: 'kpi',      wide: true },
  { id: 'tc_by_status',  label: 'Cases by Status',    icon: '🟢', type: 'doughnut', wide: false },
  { id: 'tc_by_priority',label: 'Cases by Priority',  icon: '🔺', type: 'bar',      wide: false },
  { id: 'tc_automation', label: 'Automation Coverage', icon: '🤖', type: 'doughnut', wide: false },
  { id: 'trend',         label: 'Trend: Pass/Fail',   icon: '📈', type: 'line',     wide: true,  requires_runs: true },
  { id: 'top_failed',    label: 'Top Failed Cases',   icon: '💥', type: 'table',    wide: false, requires_runs: true },
  { id: 'coverage',      label: 'Coverage by Folder', icon: '📁', type: 'bar',      wide: false, requires_runs: true },
  { id: 'plans_status',  label: 'Plans by Status',    icon: '📋', type: 'doughnut', wide: false },
]

const DEFAULT_WIDGETS = ['tc_summary', 'tc_by_status', 'tc_by_priority', 'tc_automation']

const storageKey = computed(() => `errorlens:qa_dashboard:${props.projectId}`)

const activeIds = ref([])

function loadActiveIds() {
  try {
    const raw = localStorage.getItem(storageKey.value)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed) && parsed.length) {
        activeIds.value = parsed.filter(id => WIDGET_CATALOG.some(w => w.id === id))
        return
      }
    }
  } catch { /* ignore */ }
  activeIds.value = [...DEFAULT_WIDGETS]
}

function saveActiveIds() {
  localStorage.setItem(storageKey.value, JSON.stringify(activeIds.value))
}

const activeWidgetDefs = computed(() =>
  activeIds.value.map(id => WIDGET_CATALOG.find(w => w.id === id)).filter(Boolean)
)

const availableWidgets = computed(() =>
  WIDGET_CATALOG.filter(w => !activeIds.value.includes(w.id))
)

function addWidget(id) {
  if (!activeIds.value.includes(id)) {
    activeIds.value.push(id)
    saveActiveIds()
  }
  showPicker.value = false
}

function removeWidget(id) {
  activeIds.value = activeIds.value.filter(x => x !== id)
  saveActiveIds()
}

// ── Helpers ─────────────────────────────────────────────────
function getCssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
    || getComputedStyle(document.body).getPropertyValue(name).trim()
}

function tooltipStyle() {
  return {
    backgroundColor: getCssVar('--bg-card'),
    titleColor: getCssVar('--text-primary'),
    bodyColor: getCssVar('--text-secondary'),
    borderColor: getCssVar('--border-color'),
    borderWidth: 1
  }
}

function legendStyle() {
  return {
    position: 'bottom',
    labels: { color: getCssVar('--text-primary'), padding: 12, font: { size: 12 } }
  }
}

// ── Chart builders ──────────────────────────────────────────
function buildStatusChart(canvas, dashboard) {
  if (!dashboard?.by_status) return null
  const data = dashboard.by_status
  const labels = Object.keys(data)
  const values = Object.values(data)
  const colorMap = { ready: '--success', needs_work: '--warning', draft: '--accent-hover', review: '--accent' }
  const colors = labels.map(l => getCssVar(colorMap[l] || '--text-secondary'))
  return new Chart(canvas, {
    type: 'doughnut',
    data: { labels: labels.map(l => l.replace('_', ' ')), datasets: [{ data: values, backgroundColor: colors, borderWidth: 0 }] },
    options: { responsive: true, maintainAspectRatio: false, cutout: '65%', plugins: { legend: legendStyle(), tooltip: tooltipStyle() } }
  })
}

function buildPriorityChart(canvas, dashboard) {
  if (!dashboard?.by_priority) return null
  const data = dashboard.by_priority
  const labels = Object.keys(data)
  const values = Object.values(data)
  const colorMap = { critical: '--error', high: '#f97316', medium: '--warning', low: '--text-secondary' }
  const colors = labels.map(l => {
    const v = colorMap[l]
    return v?.startsWith('--') ? getCssVar(v) : (v || getCssVar('--accent'))
  })
  return new Chart(canvas, {
    type: 'bar',
    data: { labels, datasets: [{ label: 'Cases', data: values, backgroundColor: colors, borderRadius: 4 }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: tooltipStyle() },
      scales: {
        x: { ticks: { color: getCssVar('--text-secondary') }, grid: { display: false } },
        y: { ticks: { color: getCssVar('--text-secondary') }, grid: { color: getCssVar('--border-color') } }
      }
    }
  })
}

function buildAutomationChart(canvas, dashboard) {
  if (!dashboard?.by_automation) return null
  const data = dashboard.by_automation
  const labels = Object.keys(data)
  const values = Object.values(data)
  const colorMap = { Automated: '--success', automated: '--success', Manual: '--accent', manual: '--accent' }
  const colors = labels.map(l => getCssVar(colorMap[l] || '--text-secondary'))
  return new Chart(canvas, {
    type: 'doughnut',
    data: { labels, datasets: [{ data: values, backgroundColor: colors, borderWidth: 0 }] },
    options: { responsive: true, maintainAspectRatio: false, cutout: '65%', plugins: { legend: legendStyle(), tooltip: tooltipStyle() } }
  })
}

function buildTrendChart(canvas, dashboard) {
  if (!dashboard?.trend?.length) return null
  const trend = dashboard.trend
  return new Chart(canvas, {
    type: 'line',
    data: {
      labels: trend.map(p => p.date || p.label || ''),
      datasets: [
        { label: 'Passed', data: trend.map(p => p.passed || 0), borderColor: getCssVar('--success'), backgroundColor: 'transparent', tension: 0.3, pointRadius: 4 },
        { label: 'Failed', data: trend.map(p => p.failed || 0), borderColor: getCssVar('--error'), backgroundColor: 'transparent', tension: 0.3, pointRadius: 4 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: getCssVar('--text-primary'), font: { size: 12 } } }, tooltip: tooltipStyle() },
      scales: {
        x: { ticks: { color: getCssVar('--text-secondary') }, grid: { color: getCssVar('--border-color') } },
        y: { ticks: { color: getCssVar('--text-secondary') }, grid: { color: getCssVar('--border-color') } }
      }
    }
  })
}

function buildCoverageChart(canvas, dashboard) {
  if (!dashboard?.coverage || !Object.keys(dashboard.coverage).length) return null
  const labels = Object.keys(dashboard.coverage)
  const values = Object.values(dashboard.coverage)
  return new Chart(canvas, {
    type: 'bar',
    data: { labels, datasets: [{ label: '% covered', data: values, backgroundColor: getCssVar('--accent-muted'), borderColor: getCssVar('--accent'), borderWidth: 1, borderRadius: 4 }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { ...tooltipStyle(), callbacks: { label: ctx => `${ctx.raw}%` } } },
      scales: {
        x: { ticks: { color: getCssVar('--text-secondary') }, grid: { display: false } },
        y: { min: 0, max: 100, ticks: { color: getCssVar('--text-secondary'), callback: v => `${v}%` }, grid: { color: getCssVar('--border-color') } }
      }
    }
  })
}

function buildPlansChart(canvas, dashboard) {
  if (!dashboard?.plans_by_status) return null
  const data = dashboard.plans_by_status
  const labels = Object.keys(data)
  const values = Object.values(data)
  const colorMap = { active: '--success', ready: '--success', approved: '--accent', archived: '--text-secondary', needs_work: '--warning', draft: '--accent-hover' }
  const colors = labels.map(l => getCssVar(colorMap[l] || '--accent'))
  return new Chart(canvas, {
    type: 'doughnut',
    data: { labels: labels.map(l => l.replace('_', ' ')), datasets: [{ data: values, backgroundColor: colors, borderWidth: 0 }] },
    options: { responsive: true, maintainAspectRatio: false, cutout: '65%', plugins: { legend: legendStyle(), tooltip: tooltipStyle() } }
  })
}

// ── Inline widget components ────────────────────────────────
const TcSummaryWidget = defineComponent({
  props: { dashboard: Object },
  setup(props) {
    return () => {
      const d = props.dashboard
      if (!d) return h('div', { class: 'widget-empty' }, 'Нет данных')
      const total = d.total_cases ?? 0
      const ready = total ? Math.round(((d.by_status?.ready || 0) / total) * 100) : 0
      const needsWork = total ? Math.round(((d.by_status?.needs_work || 0) / total) * 100) : 0
      return h('div', { class: 'kpi-grid' }, [
        h('div', { class: 'kpi-card' }, [h('div', { class: 'kpi-value' }, `${total}`), h('div', { class: 'kpi-label' }, 'Total cases')]),
        h('div', { class: 'kpi-card' }, [h('div', { class: 'kpi-value kpi-value--success' }, `${ready}%`), h('div', { class: 'kpi-label' }, 'Ready')]),
        h('div', { class: 'kpi-card' }, [h('div', { class: 'kpi-value kpi-value--warning' }, `${needsWork}%`), h('div', { class: 'kpi-label' }, 'Needs work')]),
      ])
    }
  }
})

function makeChartWidget(builderFn) {
  return defineComponent({
    props: { dashboard: Object, widget: Object },
    setup(props) {
      const canvasRef = ref(null)
      let chart = null
      let observer = null

      function rebuild() {
        if (chart) { chart.destroy(); chart = null }
        if (canvasRef.value && props.dashboard) {
          chart = builderFn(canvasRef.value, props.dashboard)
        }
      }

      onMounted(() => {
        nextTick(rebuild)
        observer = new MutationObserver(rebuild)
        observer.observe(document.body, { attributes: true, attributeFilter: ['class'] })
      })

      watch(() => props.dashboard, () => nextTick(rebuild))

      onBeforeUnmount(() => {
        if (chart) { chart.destroy(); chart = null }
        if (observer) { observer.disconnect(); observer = null }
      })

      return () => {
        if (props.widget?.requires_runs && !hasRunsData(props.dashboard, props.widget.id)) {
          return h(RunsRequiredWidget, { dashboard: props.dashboard, widget: props.widget })
        }
        return h('div', { class: 'chart-wrap' }, [h('canvas', { ref: canvasRef })])
      }
    }
  })
}

function hasRunsData(dashboard, widgetId) {
  if (!dashboard) return false
  switch (widgetId) {
    case 'trend': return dashboard.trend?.length > 0
    case 'top_failed': return dashboard.top_failed?.length > 0
    case 'coverage': return dashboard.coverage && Object.keys(dashboard.coverage).length > 0
    default: return true
  }
}

const TopFailedWidget = defineComponent({
  props: { dashboard: Object, widget: Object },
  setup(props) {
    return () => {
      if (props.widget?.requires_runs && !hasRunsData(props.dashboard, 'top_failed')) {
        return h(RunsRequiredWidget)
      }
      const items = props.dashboard?.top_failed || []
      if (!items.length) return h('div', { class: 'widget-empty' }, 'Нет нестабильных кейсов')
      return h('div', { class: 'flaky-list' }, items.map(item =>
        h('div', { class: 'flaky-row', key: item.id }, [
          h('span', { class: 'flaky-name' }, item.title || item.name),
          h('span', { class: 'flaky-count' }, `${item.failed_count}`)
        ])
      ))
    }
  }
})

const RunsRequiredWidget = defineComponent({
  setup() {
    return () => h('div', { class: 'widget-empty' }, 'Нужны прогоны тестов для отображения данных')
  }
})

const chartWidgets = {
  tc_by_status: makeChartWidget(buildStatusChart),
  tc_by_priority: makeChartWidget(buildPriorityChart),
  tc_automation: makeChartWidget(buildAutomationChart),
  trend: makeChartWidget(buildTrendChart),
  coverage: makeChartWidget(buildCoverageChart),
  plans_status: makeChartWidget(buildPlansChart),
}

function getWidgetComponent(w) {
  if (w.id === 'tc_summary') return TcSummaryWidget
  if (w.id === 'top_failed') return TopFailedWidget
  return chartWidgets[w.id] || RunsRequiredWidget
}

// ── Lifecycle ───────────────────────────────────────────────
function onClickOutside(e) {
  if (showPicker.value && pickerRef.value && !pickerRef.value.contains(e.target)) {
    showPicker.value = false
  }
}

watch(() => props.projectId, async (newId) => {
  if (!newId) return
  loadActiveIds()
  await store.fetchDashboard(newId)
})

onMounted(async () => {
  loadActiveIds()
  await store.fetchDashboard(props.projectId)
  document.addEventListener('mousedown', onClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onClickOutside)
})
</script>

<style scoped>
.qa-dashboard {
  padding: 0;
}

.dash-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  position: relative;
}

.dash-title {
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  flex: 1;
}

.widget-picker {
  position: absolute;
  top: 100%;
  right: 0;
  z-index: 100;
  width: 320px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: var(--shadow-dropdown);
  padding: 8px 0;
  max-height: 320px;
  overflow-y: auto;
}

.widget-picker-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  cursor: pointer;
  color: var(--text-primary);
  font-size: 13px;
  transition: background 0.15s;
}

.widget-picker-item:hover {
  background: var(--bg-tertiary);
}

.widget-picker-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.widget-picker-label {
  flex: 1;
}

.widget-picker-empty {
  padding: 16px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
}

.dash-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--text-secondary);
  padding: 48px;
  font-size: 13px;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.dash-empty {
  color: var(--text-secondary);
  text-align: center;
  padding: 48px;
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
  gap: 16px;
}

.dash-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
  position: relative;
}

.dash-card--wide {
  grid-column: span 2;
}

.dash-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.dash-card-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.dash-card-title {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 600;
  margin: 0;
  flex: 1;
}

.btn-remove-widget {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
  opacity: 0;
  transition: opacity 0.15s, color 0.15s;
}

.dash-card:hover .btn-remove-widget {
  opacity: 1;
}

.btn-remove-widget:hover {
  color: var(--error);
}

.chart-wrap {
  height: 220px;
  position: relative;
}

.kpi-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px;
}

.kpi-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}

.kpi-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.kpi-value--success {
  color: var(--success);
}

.kpi-value--warning {
  color: var(--warning);
}

.kpi-label {
  font-size: 12px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.widget-empty {
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
