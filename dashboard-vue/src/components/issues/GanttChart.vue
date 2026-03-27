<template>
  <div class="gantt-root">
    <div v-if="ganttLoading" class="gantt-loading">Loading Gantt...</div>
    <div v-else-if="!validSprints.length" class="gantt-empty">No sprints with dates.</div>
    <div v-else class="gantt-container">
      <!-- Left labels -->
      <div class="gantt-labels">
        <div class="gantt-header-spacer"></div>
        <template v-for="s in validSprints" :key="s.id">
          <div class="gantt-row-label gantt-sprint-label">{{ s.name }}</div>
          <div v-for="issue in (store.sprintIssues[s.id] || [])" :key="issue.id"
               class="gantt-row-label gantt-issue-label" @click="$emit('open-task', issue.id)">
            <span class="gantt-human-id">{{ issue.human_id }}</span>
            <span class="gantt-issue-name">{{ issue.title }}</span>
          </div>
        </template>
      </div>
      <!-- Right SVG -->
      <div class="gantt-timeline">
        <svg :width="svgWidth" :height="svgHeight">
          <!-- Header bg -->
          <rect x="0" y="0" :width="svgWidth" height="36" class="gantt-header-bg" />
          <!-- Day labels -->
          <text v-for="(day, i) in dayLabels" :key="'dl'+i"
                :x="i * DAY_WIDTH + DAY_WIDTH/2" y="22"
                class="gantt-day-label" :class="{ 'gantt-today-label': day.isToday }">{{ day.label }}</text>
          <!-- Weekend shading -->
          <template v-for="(day, i) in dayLabels" :key="'wk'+i">
            <rect v-if="day.isWeekend" :x="i * DAY_WIDTH" y="36" :width="DAY_WIDTH"
                  :height="svgHeight - 36" class="gantt-weekend" />
          </template>
          <!-- Today line -->
          <line v-if="todayX !== null" :x1="todayX" :x2="todayX" y1="0" :y2="svgHeight"
                class="gantt-today-line" />
          <!-- Sprint + issue bars -->
          <template v-for="s in validSprints" :key="'sb'+s.id">
            <rect :x="dateToX(s.start_date)" :y="rowY(s.id, 'sprint') + 8"
                  :width="Math.max(dateRangeWidth(s.start_date, s.end_date), DAY_WIDTH)"
                  height="20" rx="4" class="gantt-sprint-bar" />
            <text :x="dateToX(s.start_date) + 6" :y="rowY(s.id, 'sprint') + 22"
                  class="gantt-sprint-bar-label">{{ s.name }}</text>
            <rect v-for="issue in (store.sprintIssues[s.id] || [])" :key="'ib'+issue.id"
                  :x="issueBarX(issue, s)" :y="rowY(s.id, 'issue', issue.id) + 6"
                  :width="issueBarWidth(issue, s)" height="18" rx="3"
                  :class="['gantt-issue-bar', 'priority-' + issue.priority]"
                  @click="$emit('open-task', issue.id)" />
          </template>
          <!-- Row dividers -->
          <line v-for="(y, i) in rowDividers" :key="'div'+i"
                x1="0" :x2="svgWidth" :y1="y" :y2="y" class="gantt-divider" />
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useIssuesStore } from '@/stores/issues'

const props = defineProps({
  projectId: { type: String, required: true },
})

defineEmits(['open-task'])

const store = useIssuesStore()

const DAY_WIDTH = 32
const ROW_HEIGHT_SPRINT = 36
const ROW_HEIGHT_ISSUE = 28
const HEADER_HEIGHT = 36

const ganttLoading = ref(false)

const validSprints = computed(() => {
  return store.sprints
    .filter(s => s.start_date && s.end_date)
    .sort((a, b) => new Date(a.start_date) - new Date(b.start_date))
})

const minDate = computed(() => {
  if (!validSprints.value.length) return new Date()
  const dates = validSprints.value.map(s => new Date(s.start_date))
  const min = new Date(Math.min(...dates))
  min.setDate(min.getDate() - 1)
  return min
})

const maxDate = computed(() => {
  if (!validSprints.value.length) return new Date()
  const dates = validSprints.value.map(s => new Date(s.end_date))
  const max = new Date(Math.max(...dates))
  max.setDate(max.getDate() + 1)
  return max
})

const totalDays = computed(() => {
  return Math.ceil((maxDate.value - minDate.value) / (1000 * 60 * 60 * 24)) + 1
})

const dayLabels = computed(() => {
  const labels = []
  const d = new Date(minDate.value)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  for (let i = 0; i < totalDays.value; i++) {
    const dayOfWeek = d.getDay()
    const cur = new Date(d)
    cur.setHours(0, 0, 0, 0)
    labels.push({
      label: `${d.getDate()}`,
      isWeekend: dayOfWeek === 0 || dayOfWeek === 6,
      isToday: cur.getTime() === today.getTime(),
    })
    d.setDate(d.getDate() + 1)
  }
  return labels
})

const svgWidth = computed(() => totalDays.value * DAY_WIDTH)

// Build row layout: sprint rows + issue rows under each sprint
const rowLayout = computed(() => {
  const rows = []
  for (const s of validSprints.value) {
    rows.push({ type: 'sprint', sprintId: s.id })
    const issues = store.sprintIssues[s.id] || []
    for (const issue of issues) {
      rows.push({ type: 'issue', sprintId: s.id, issueId: issue.id })
    }
  }
  return rows
})

const svgHeight = computed(() => {
  let h = HEADER_HEIGHT
  for (const row of rowLayout.value) {
    h += row.type === 'sprint' ? ROW_HEIGHT_SPRINT : ROW_HEIGHT_ISSUE
  }
  return h
})

const rowDividers = computed(() => {
  const dividers = []
  let y = HEADER_HEIGHT
  for (const row of rowLayout.value) {
    y += row.type === 'sprint' ? ROW_HEIGHT_SPRINT : ROW_HEIGHT_ISSUE
    dividers.push(y)
  }
  return dividers
})

const todayX = computed(() => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const x = dateToX(today)
  return (x >= 0 && x <= svgWidth.value) ? x : null
})

function dateToX(date) {
  const d = typeof date === 'string' ? new Date(date) : date
  const diff = (d - minDate.value) / (1000 * 60 * 60 * 24)
  return diff * DAY_WIDTH
}

function dateRangeWidth(startDate, endDate) {
  const s = typeof startDate === 'string' ? new Date(startDate) : startDate
  const e = typeof endDate === 'string' ? new Date(endDate) : endDate
  const days = (e - s) / (1000 * 60 * 60 * 24)
  return Math.max(days * DAY_WIDTH, DAY_WIDTH)
}

function rowY(sprintId, type, issueId = null) {
  let y = HEADER_HEIGHT
  for (const row of rowLayout.value) {
    if (type === 'sprint' && row.type === 'sprint' && row.sprintId === sprintId) return y
    if (type === 'issue' && row.type === 'issue' && row.sprintId === sprintId && row.issueId === issueId) return y
    y += row.type === 'sprint' ? ROW_HEIGHT_SPRINT : ROW_HEIGHT_ISSUE
  }
  return y
}

function issueBarX(issue, sprint) {
  const start = issue.start_date || sprint.start_date
  return dateToX(start)
}

function issueBarWidth(issue, sprint) {
  const start = issue.start_date || sprint.start_date
  const end = issue.due_date || sprint.end_date
  return dateRangeWidth(start, end)
}

async function loadGanttData() {
  ganttLoading.value = true
  try {
    if (!store.sprints.length) {
      await store.fetchSprints(props.projectId)
    }
    const promises = validSprints.value.map(s => store.fetchSprintIssues(s.id))
    await Promise.all(promises)
  } catch (e) {
    console.error('Gantt load error:', e)
  } finally {
    ganttLoading.value = false
  }
}

onMounted(() => {
  loadGanttData()
})

watch(() => props.projectId, () => {
  loadGanttData()
})
</script>

<style scoped>
.gantt-root { overflow: hidden; }
.gantt-loading, .gantt-empty { text-align: center; padding: 40px; color: var(--text-secondary); }
.gantt-container { display: flex; background: var(--bg-card); border-radius: 12px; overflow: hidden; }
.gantt-labels { width: 240px; flex-shrink: 0; border-right: 1px solid var(--border-color); background: var(--bg-card); position: sticky; left: 0; z-index: 3; }
.gantt-header-spacer { height: 36px; background: var(--bg-secondary); border-bottom: 1px solid var(--border-color); }
.gantt-row-label { display: flex; align-items: center; gap: 6px; padding: 0 12px; font-size: 12px; overflow: hidden; border-bottom: 1px solid var(--border-color); }
.gantt-sprint-label { height: 36px; font-weight: 600; color: var(--text-primary); background: var(--bg-secondary); }
.gantt-issue-label { height: 28px; cursor: pointer; color: var(--text-secondary); }
.gantt-issue-label:hover { background: var(--bg-secondary); }
.gantt-human-id { font-size: 10px; font-family: monospace; color: var(--accent); flex-shrink: 0; }
.gantt-issue-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gantt-timeline { overflow-x: auto; flex: 1; }
.gantt-header-bg { fill: var(--bg-secondary); }
.gantt-day-label { font-size: 11px; fill: var(--text-secondary); text-anchor: middle; }
.gantt-today-label { fill: var(--accent); font-weight: 600; }
.gantt-weekend { fill: var(--bg-secondary); opacity: 0.5; }
.gantt-today-line { stroke: var(--error); stroke-width: 1.5; stroke-dasharray: 4 2; opacity: 0.8; }
.gantt-divider { stroke: var(--border-color); stroke-width: 1; }
.gantt-sprint-bar { fill: var(--accent-subtle); stroke: var(--accent); stroke-width: 1; }
.gantt-sprint-bar-label { font-size: 11px; fill: var(--accent); font-weight: 600; }
.gantt-issue-bar { cursor: pointer; }
.gantt-issue-bar.priority-high { fill: #f59e0b; opacity: 0.85; }
.gantt-issue-bar.priority-medium { fill: #3b82f6; opacity: 0.85; }
.gantt-issue-bar.priority-low { fill: var(--text-secondary); opacity: 0.6; }
.gantt-issue-bar.priority-critical { fill: var(--error); opacity: 0.9; }
.gantt-issue-bar:hover { opacity: 1; filter: brightness(1.1); }
</style>
