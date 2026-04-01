<template>
  <div class="issues-page">
    <div class="page-header">
      <h1>Issues</h1>
      <button class="btn btn-primary" @click="showCreateModal = true">+ New Issue</button>
    </div>

    <!-- JQL Row -->
    <div class="jql-row">
      <JQLBar
        ref="jqlBarRef"
        :project-id="currentProjectId"
        @search="onJQLSearch"
        @clear="onJQLClear"
      />
      <button
        class="jql-filter-toggle"
        :class="{ active: showFilterPanel }"
        @click="showFilterPanel = !showFilterPanel"
      >
        <AppIcon name="filter" :size="14" />
        Filters
        <span v-if="activeFilterCount" class="filter-count-badge">{{ activeFilterCount }}</span>
      </button>
    </div>

    <!-- Filter Panel -->
    <TaskFilterPanel
      v-if="showFilterPanel"
      ref="filterPanelRef"
      :task-types="taskTypes"
      :project-id="currentProjectId"
      @filter-change="onFilterChange"
      @clear="onFilterClear"
    />

    <!-- Saved Filters -->
    <SavedFilters
      :project-id="currentProjectId"
      :active-j-q-l="jqlStore.currentJQL"
      @apply="onApplyFilter"
    />

    <!-- Tab nav -->
    <div class="issues-tabs">
      <button :class="['tab', { active: activeTab === 'board' }]" @click="activeTab = 'board'">Board</button>
      <button :class="['tab', { active: activeTab === 'backlog' }]" @click="activeTab = 'backlog'">Backlog</button>
      <button :class="['tab', { active: activeTab === 'tree' }]" @click="activeTab = 'tree'">Tree</button>
      <button :class="['tab', { active: activeTab === 'gantt' }]" @click="activeTab = 'gantt'">Gantt</button>
      <button :class="['tab', { active: activeTab === 'time' }]" @click="activeTab = 'time'">Time</button>
      <button :class="['tab', { active: activeTab === 'dashboard' }]" @click="activeTab = 'dashboard'">Dashboard</button>
    </div>

    <!-- Board tab content -->
    <template v-if="activeTab === 'board'">
      <!-- Type filter tabs + View toggle -->
      <div class="toolbar-row">
        <div class="type-tabs">
          <button class="type-tab" :class="{ active: activeTypeFilter === 'all' }" @click="filterByType('all')">All</button>
          <button
            v-for="t in taskTypes" :key="t.slug"
            class="type-tab"
            :class="{ active: activeTypeFilter === t.slug }"
            :style="activeTypeFilter === t.slug ? { borderBottomColor: t.color } : {}"
            @click="filterByType(t.slug)"
          >
            <AppIcon :name="t.icon" :size="14" />
            {{ t.name }}
          </button>
        </div>
        <div class="view-toggle">
          <button class="toggle-btn" :class="{ active: viewMode === 'board' }" @click="viewMode = 'board'" title="Kanban Board">
            <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16"><path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" /></svg>
          </button>
          <button class="toggle-btn" :class="{ active: viewMode === 'list' }" @click="viewMode = 'list'" title="List View">
            <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16"><path fill-rule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clip-rule="evenodd" /></svg>
          </button>
        </div>
      </div>

      <div v-if="loading" class="loading"><div class="spinner"></div></div>

      <!-- List View -->
      <div v-else-if="viewMode === 'list'" class="task-list" data-testid="task-list">
        <div v-if="!listTasks.length" class="empty-list">
          <p v-if="jqlStore.currentJQL">No tasks match your query</p>
          <p v-else>No tasks found</p>
        </div>
        <div v-for="task in listTasks" :key="task.id" class="task-list-row" @click="openTask(task)">
          <div class="row-left">
            <span v-if="task.type" class="type-indicator" :style="{ background: task.type.color }">
              <AppIcon :name="task.type.icon" :size="10" />
            </span>
            <span v-if="task.human_id" class="human-id-badge">{{ task.human_id }}</span>
            <span class="task-title">{{ task.title }}</span>
          </div>
          <div class="row-right">
            <span v-if="task.task_status" class="status-pill" :style="{ background: task.task_status.color }">{{ task.task_status.name }}</span>
            <span v-else class="status-pill legacy">{{ task.status }}</span>
            <span v-if="task.severity" class="severity-badge" :class="task.severity">{{ task.severity }}</span>
            <span class="priority-dot" :class="task.priority"></span>
            <span v-if="task.assignee_user" class="assignee-pill">{{ task.assignee_user.display_name || task.assignee_user.username }}</span>
          </div>
        </div>
      </div>

      <!-- Kanban Board -->
      <div v-else class="kanban-board" data-testid="kanban-board">
        <div v-for="column in columns" :key="column.id" class="kanban-column" @dragover.prevent @drop="onDrop($event, column.id)">
          <div class="column-header" :class="{ 'wip-exceeded': isWipExceeded(column.id) }">
            <span class="column-title">{{ column.title }}</span>
            <div class="column-header-right">
              <span class="column-count" :class="{ 'count-exceeded': isWipExceeded(column.id) }">
                {{ board[column.id]?.length || 0 }}
                <span v-if="wipLimits[column.id]" class="wip-limit-badge">
                  / {{ wipLimits[column.id] }}
                </span>
              </span>
              <button
                class="btn-wip-edit"
                :title="wipLimits[column.id] ? `WIP limit: ${wipLimits[column.id]}` : 'Set WIP limit'"
                @click.stop="openWipEditor(column.id)"
              >&#9881;</button>
            </div>
          </div>
          <div class="column-content">
            <div v-for="task in board[column.id]" :key="task.id" class="task-card" draggable="true" @dragstart="onDragStart($event, task)" @click="openTask(task)">
              <div class="task-priority" :class="task.priority"></div>
              <div class="card-top">
                <span v-if="task.type" class="type-indicator" :style="{ background: task.type.color }" :title="task.type.name">
                  <AppIcon :name="task.type.icon" :size="10" />
                </span>
                <span v-if="task.human_id" class="human-id-badge">{{ task.human_id }}</span>
              </div>
              <h4>{{ task.title }}</h4>
              <div class="task-meta">
                <span v-if="task.assignee_user" class="assignee">{{ task.assignee_user.display_name || task.assignee_user.username }}</span>
                <span v-else-if="task.assignee" class="assignee">{{ task.assignee }}</span>
                <span v-if="task.severity" class="severity-badge" :class="task.severity">{{ task.severity }}</span>
                <span v-if="task.due_date" class="due-date" :class="{ overdue: isOverdue(task) }">{{ formatDate(task.due_date) }}</span>
              </div>
              <div v-if="task.labels?.length" class="task-labels">
                <span v-for="label in task.labels" :key="label" class="label">{{ label }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
    <template v-else-if="activeTab === 'backlog'">
      <SprintPanel v-if="activeSprint" :sprint="activeSprint" @complete="handleCompleteSprint" @start="handleStartSprint" />
      <BacklogView :issues="backlog" :sprint="activeSprint" @rank-change="handleRankChange" @add-to-sprint="handleAddToSprint" />
      <div v-if="!activeSprint && !sprints.length" class="no-sprint-hint">
        <button class="btn btn-secondary" @click="showCreateSprintModal = true">+ Create Sprint</button>
      </div>
    </template>
    <IssueTree v-else-if="activeTab === 'tree'" :project-id="currentProjectId" @open-task="openTaskById" />
    <GanttChart v-else-if="activeTab === 'gantt'" :project-id="currentProjectId" @open-task="openTaskById" />
    <TimeReport v-else-if="activeTab === 'time'" :project-id="currentProjectId" />
    <DashboardView v-else-if="activeTab === 'dashboard'" :project-id="currentProjectId" />
    <TaskViewer v-if="viewerTask" :task="viewerTask" @close="closeViewer" @edit="openEditor" @open-task="openTaskById" />
    <IssueDetailView v-if="editorTask" :task="editorTask" @close="closeEditor" @updated="refreshTask" @open-task="openTaskById" />
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal-content">
        <button class="modal-close" @click="showCreateModal = false">&times;</button>
        <h2>New Issue</h2>
        <form @submit.prevent="saveTask">
          <div class="form-group"><label>Title *</label><input v-model="form.title" required placeholder="Issue title" /></div>
          <div class="form-group"><label>Description</label><RichEditor v-model="form.descriptionJson" placeholder="Issue description" /></div>
          <div class="form-row">
            <div class="form-group"><label>Type</label>
              <select v-model="form.type_id"><option value="">None</option><option v-for="t in taskTypes" :key="t.id" :value="t.id">{{ t.name }}</option></select></div>
            <div class="form-group"><label>Priority</label>
              <select v-model="form.priority"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></div>
          </div>
          <div class="form-row">
            <div class="form-group"><label>Severity</label>
              <select v-model="form.severity"><option value="">None</option><option value="critical">Critical</option><option value="major">Major</option><option value="minor">Minor</option><option value="trivial">Trivial</option></select></div>
            <div class="form-group"><label>Environment</label>
              <select v-model="form.environment"><option value="">None</option><option value="production">Production</option><option value="staging">Staging</option><option value="local">Local</option><option value="all">All</option></select></div>
          </div>
          <div class="form-row">
            <div class="form-group"><label>Assignee</label><input v-model="form.assignee" placeholder="Username" /></div>
            <div class="form-group"><label>Due Date</label><input v-model="form.due_date" type="datetime-local" /></div>
          </div>
          <div class="form-group"><label>Labels (comma-separated)</label><input v-model="labelsInput" placeholder="bug, feature, urgent" /></div>
          <div class="form-actions">
            <button type="button" class="btn btn-secondary" @click="showCreateModal = false">Cancel</button>
            <button type="submit" class="btn btn-primary">Create</button>
          </div>
        </form>
      </div>
    </div>
    <div v-if="showCreateSprintModal" class="modal-overlay" @click.self="showCreateSprintModal = false">
      <div class="modal-content">
        <button class="modal-close" @click="showCreateSprintModal = false">&times;</button>
        <h2>New Sprint</h2>
        <form @submit.prevent="createSprint">
          <div class="form-group"><label>Name *</label><input v-model="sprintForm.name" required placeholder="Sprint 1" /></div>
          <div class="form-group"><label>Goal</label><input v-model="sprintForm.goal" placeholder="Sprint goal" /></div>
          <div class="form-row">
            <div class="form-group"><label>Start Date</label><input v-model="sprintForm.start_date" type="date" /></div>
            <div class="form-group"><label>End Date</label><input v-model="sprintForm.end_date" type="date" /></div>
          </div>
          <div class="form-actions">
            <button type="button" class="btn btn-secondary" @click="showCreateSprintModal = false">Cancel</button>
            <button type="submit" class="btn btn-primary">Create</button>
          </div>
        </form>
      </div>
    </div>
    <!-- WIP Limit Editor -->
    <div v-if="showWipEditor" class="wip-modal-overlay" @click.self="showWipEditor = false">
      <div class="wip-modal">
        <h4 class="wip-modal-title">WIP Limit — {{ wipEditorColumn }}</h4>
        <p class="wip-modal-hint">Максимальное число задач в колонке. Оставьте пустым для отключения.</p>
        <input
          v-model="wipEditorValue"
          type="number"
          min="1"
          class="wip-modal-input"
          placeholder="Без лимита"
          @keydown.enter="saveWipLimit(wipEditorColumn, wipEditorValue)"
          @keydown.esc="showWipEditor = false"
        />
        <div class="wip-modal-actions">
          <button class="btn-wip-clear" @click="saveWipLimit(wipEditorColumn, null)">Убрать лимит</button>
          <button class="btn-wip-save" @click="saveWipLimit(wipEditorColumn, wipEditorValue)">Сохранить</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, inject, defineAsyncComponent } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useIssuesStore } from '@/stores/issues'
import { useJqlStore } from '@/stores/jql'
import { taskSettingsApi } from '@/services/api'
import { useCurrentProjectStore } from '@/stores/currentProject'
import RichEditor from '@/components/common/RichEditor.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import IssueDetailView from '@/components/issues/IssueDetailView.vue'
import TaskViewer from '@/components/tasks/TaskViewer.vue'
import JQLBar from '@/components/tasks/JQLBar.vue'
import SavedFilters from '@/components/tasks/SavedFilters.vue'
import TaskFilterPanel from '@/components/tasks/TaskFilterPanel.vue'
import SprintPanel from '@/components/issues/SprintPanel.vue'
import BacklogView from '@/components/issues/BacklogView.vue'

const DashboardView = defineAsyncComponent(() => import('@/components/issues/DashboardView.vue'))
const TimeReport = defineAsyncComponent(() => import('@/components/issues/TimeReport.vue'))
const IssueTree = defineAsyncComponent(() => import('@/components/issues/IssueTree.vue'))
const GanttChart = defineAsyncComponent(() => import('@/components/issues/GanttChart.vue'))

const route = useRoute()
const router = useRouter()
const store = useIssuesStore()
const jqlStore = useJqlStore()
const toast = inject('toast', null)
const currentProjectStore = useCurrentProjectStore()

const columns = [
  { id: 'todo', title: 'To Do' },
  { id: 'in_progress', title: 'In Progress' },
  { id: 'review', title: 'Review' },
  { id: 'done', title: 'Done' }
]

const activeTab = ref('board')
const showCreateModal = ref(false)
const showCreateSprintModal = ref(false)

// WIP limits
const wipLimits = ref({})
const showWipEditor = ref(false)
const wipEditorColumn = ref(null)
const wipEditorValue = ref('')

function loadWipLimits() {
  if (!currentProjectId.value) return
  try {
    const stored = localStorage.getItem(`errorlens:wip_limits:${currentProjectId.value}`)
    wipLimits.value = stored ? JSON.parse(stored) : {}
  } catch { wipLimits.value = {} }
}

function saveWipLimit(columnId, value) {
  const limit = value === '' || value === null ? null : parseInt(value)
  wipLimits.value = { ...wipLimits.value, [columnId]: limit }
  localStorage.setItem(
    `errorlens:wip_limits:${currentProjectId.value}`,
    JSON.stringify(wipLimits.value)
  )
  showWipEditor.value = false
}

function isWipExceeded(columnId) {
  const limit = wipLimits.value[columnId]
  if (!limit) return false
  return (board.value[columnId]?.length || 0) > limit
}

function openWipEditor(columnId) {
  wipEditorColumn.value = columnId
  wipEditorValue.value = wipLimits.value[columnId] ?? ''
  showWipEditor.value = true
}
const viewerTask = ref(null)
const editorTask = ref(null)
const taskTypes = ref([])
const activeTypeFilter = ref('all')
const viewMode = ref('board')
const currentProjectId = computed(() => currentProjectStore.currentProjectId)
const jqlBarRef = ref(null)
const showFilterPanel = ref(false)
const filterPanelRef = ref(null)
const activeFilterCount = ref(0)
let draggedTask = null

const listTasks = computed(() => jqlStore.currentJQL ? jqlStore.jqlResults : store.tasks)
const loading = computed(() => store.loading)
const board = computed(() => store.board)
const backlog = computed(() => store.backlog)
const sprints = computed(() => store.sprints)
const activeSprint = computed(() => store.activeSprint)

const form = ref({ title: '', descriptionJson: null, status: 'todo', priority: 'medium', assignee: '', due_date: '', type_id: '', severity: '', environment: '' })
const labelsInput = ref('')
const sprintForm = ref({ name: '', goal: '', start_date: '', end_date: '' })

function onDragStart(event, task) { draggedTask = task; event.dataTransfer.effectAllowed = 'move' }
async function onDrop(event, status) {
  if (draggedTask && draggedTask.status !== status) await store.moveTask(draggedTask.id, status)
  draggedTask = null
}

async function openTask(task) {
  try {
    const full = await store.fetchTask(task.id)
    if (full) {
      viewerTask.value = full
      const urlId = full.human_id || full.id
      if (route.params.id !== urlId) {
        router.push({ name: 'issue', params: { id: urlId } })
      }
    } else {
      showError('Task not found')
    }
  } catch { showError('Failed to load task') }
}

async function openTaskById(id) {
  try {
    const full = await store.fetchTask(id)
    if (full) {
      viewerTask.value = full
      const urlId = full.human_id || full.id
      if (route.params.id !== urlId) {
        router.push({ name: 'issue', params: { id: urlId } })
      }
    } else {
      showError('Task not found')
    }
  } catch { showError('Failed to load task') }
}

function closeViewer() {
  viewerTask.value = null
  if (route.params.id) router.push({ name: 'issues' })
}
function openEditor() { editorTask.value = viewerTask.value; viewerTask.value = null }
function closeEditor() {
  editorTask.value = null
  if (route.params.id) router.push({ name: 'issues' })
}

async function refreshTask() {
  if (editorTask.value) {
    const updated = await store.fetchTask(editorTask.value.id)
    if (updated) editorTask.value = updated
  }
  await store.fetchBoard(activeTypeFilter.value !== 'all' ? { project_id: currentProjectId.value, type_slug: activeTypeFilter.value } : { project_id: currentProjectId.value })
}

function showError(msg) {
  if (toast) toast(msg, 'error')
  else if (window.showToast) window.showToast(msg, 'error')
}

function resetForm() {
  form.value = { title: '', descriptionJson: null, status: 'todo', priority: 'medium', assignee: '', due_date: '', type_id: '', severity: '', environment: '' }
  labelsInput.value = ''
}

async function saveTask() {
  const data = {
    title: form.value.title,
    description: form.value.descriptionJson ? JSON.stringify(form.value.descriptionJson) : null,
    status: form.value.status, priority: form.value.priority,
    assignee: form.value.assignee || null,
    labels: labelsInput.value.split(',').map(l => l.trim()).filter(Boolean),
    due_date: form.value.due_date || null, type_id: form.value.type_id || null,
    severity: form.value.severity || null, environment: form.value.environment || null,
  }
  await store.createTask(data)
  showCreateModal.value = false
  resetForm()
}

function onFilterChange({ jql, filters }) {
  let count = 0
  for (const key of ['status', 'priority', 'type', 'severity', 'assignee', 'label']) count += filters[key]?.length || 0
  if (filters.dueAfter) count++
  if (filters.dueBefore) count++
  activeFilterCount.value = count
  if (jql && jqlBarRef.value) jqlBarRef.value.setJQL(jql)
  if (jql) viewMode.value = 'list'
}

function onFilterClear() { activeFilterCount.value = 0; jqlStore.clearJQL(); viewMode.value = 'board' }
function onJQLSearch() { viewMode.value = 'list' }
function onJQLClear() { filterPanelRef.value?.clearFilters(); activeFilterCount.value = 0; viewMode.value = 'board' }
function onApplyFilter(jql) { if (jqlBarRef.value) jqlBarRef.value.setJQL(jql) }

watch(viewMode, async (mode) => {
  if (mode === 'list' && !jqlStore.currentJQL && !store.tasks.length) {
    await store.fetchTasks({ project_id: currentProjectId.value })
  }
})

async function filterByType(slug) {
  activeTypeFilter.value = slug

  const boardParams = { project_id: currentProjectId.value }
  const taskParams = { project_id: currentProjectId.value }

  if (slug !== 'all') {
    boardParams.type_slug = slug
    const typeObj = taskTypes.value.find(t => t.slug === slug)
    if (typeObj) taskParams.type_id = typeObj.id
  }

  await Promise.all([
    store.fetchBoard(boardParams),
    store.fetchTasks(taskParams),
  ])
}

function formatDate(date) { return date ? new Date(date).toLocaleDateString() : '' }
function isOverdue(task) { return task.due_date && new Date(task.due_date) < new Date() && task.status !== 'done' }

async function handleRankChange(fromIndex, toIndex) {
  const items = [...store.backlog]
  const [moved] = items.splice(fromIndex, 1)
  items.splice(toIndex, 0, moved)
  const newRank = toIndex * 1000
  await store.updateRank(moved.id, newRank)
}

async function handleAddToSprint(issueId, sprintId) {
  await store.updateRank(issueId, 0, sprintId)
  await store.fetchBacklog({ project_id: currentProjectId.value })
}

async function handleStartSprint(sprintId) { await store.startSprint(sprintId, currentProjectId.value) }
async function handleCompleteSprint(sprintId) { await store.completeSprint(sprintId, null, currentProjectId.value) }

async function createSprint() {
  await store.createSprint({ ...sprintForm.value, project_id: currentProjectId.value })
  showCreateSprintModal.value = false
  sprintForm.value = { name: '', goal: '', start_date: '', end_date: '' }
}

async function loadTaskTypes() {
  try {
    if (!currentProjectId.value) return
    const typesRes = await taskSettingsApi.getTypes(currentProjectId.value)
    taskTypes.value = typesRes.data.filter(t => t.is_active)
    jqlStore.fetchSavedFilters(currentProjectId.value)
  } catch { taskTypes.value = [] }
}

async function openFromRoute() {
  const id = route.params.id
  if (!id) return

  try {
    let task = await store.fetchTask(id)

    if (!task && id.includes('-') && id.length < 36) {
      const allTasks = [...(store.tasks || []),
                        ...Object.values(store.board || {}).flat()]
      const found = allTasks.find(t => t.human_id === id)
      if (found) task = await store.fetchTask(found.id)
    }

    if (task) viewerTask.value = task
  } catch (e) {
    console.warn('Task not found for route param:', id)
  }
}

watch(() => route.params.id, openFromRoute)
watch(activeTab, async (tab) => {
  if (tab === 'backlog' && currentProjectId.value) {
    await Promise.all([
      store.fetchBacklog({ project_id: currentProjectId.value }),
      store.fetchSprints(currentProjectId.value),
    ])
  }
  if (tab === 'tree' && currentProjectId.value) {
    store.fetchTree?.(currentProjectId.value)
  }
  if (tab === 'gantt' && currentProjectId.value) {
    await store.fetchSprints(currentProjectId.value)
  }
  if (tab === 'time' && currentProjectId.value) {
    store.fetchProjectWorkLogs?.(currentProjectId.value)
  }
  if (tab === 'dashboard' && currentProjectId.value) {
    store.fetchDashboard(currentProjectId.value)
  }
})

watch(currentProjectId, () => { loadWipLimits() })

watch(
  () => currentProjectStore.currentProjectId,
  async (newId, oldId) => {
    if (!newId || newId === oldId) return
    taskTypes.value = []
    activeTypeFilter.value = 'all'
    await loadTaskTypes()
    loadWipLimits()
    await Promise.all([
      store.fetchBoard({ project_id: newId }),
      store.fetchTasks({ project_id: newId }),
    ])
  }
)

onMounted(async () => {
  if (!currentProjectStore.currentProjectId) {
    await currentProjectStore.init()
  }
  await loadTaskTypes()
  loadWipLimits()
  await Promise.all([
    store.fetchBoard({ project_id: currentProjectId.value }),
    store.fetchTasks({ project_id: currentProjectId.value }),
  ])
  await openFromRoute()
})
</script>

<style scoped>
.issues-tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border-color); margin-bottom: 16px; }
.tab { padding: 10px 20px; border: none; background: none; color: var(--text-secondary); font-size: 14px; font-weight: 500; cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.2s; }
.tab:hover { color: var(--text-primary); }
.tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.no-sprint-hint { text-align: center; padding: 40px; color: var(--text-secondary); }
.jql-row { display: flex; align-items: flex-start; gap: 8px; margin-bottom: 8px; }
.jql-row :deep(.jql-bar) { flex: 1; margin-bottom: 0; }
.jql-filter-toggle { display: flex; align-items: center; gap: 6px; padding: 8px 12px; border: 1px solid var(--bg-secondary); border-radius: 8px; background: var(--bg-card); color: var(--text-secondary); font-size: 13px; cursor: pointer; white-space: nowrap; transition: all 0.2s; flex-shrink: 0; }
.jql-filter-toggle:hover { border-color: var(--accent); color: var(--text-primary); }
.jql-filter-toggle.active { border-color: var(--accent); color: var(--accent); background: var(--accent-muted); }
.filter-count-badge { background: var(--accent); color: white; font-size: 10px; font-weight: 700; padding: 1px 5px; border-radius: 10px; margin-left: 2px; }
.toolbar-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.view-toggle { display: flex; gap: 2px; background: var(--bg-card); border-radius: 8px; padding: 2px; }
.toggle-btn { display: flex; align-items: center; justify-content: center; width: 32px; height: 28px; border: none; background: none; color: var(--text-secondary); border-radius: 6px; cursor: pointer; transition: all 0.15s; }
.toggle-btn.active { background: var(--accent); color: white; }
.toggle-btn:hover:not(.active) { background: var(--bg-secondary); }
.task-list { background: var(--bg-card); border-radius: 12px; overflow: hidden; }
.empty-list { padding: 40px; text-align: center; color: var(--text-secondary); }
.task-list-row { display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; border-bottom: 1px solid var(--bg-secondary); cursor: pointer; transition: background 0.15s; }
.task-list-row:hover { background: var(--bg-secondary); }
.task-list-row:last-child { border-bottom: none; }
.row-left { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; }
.task-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }
.row-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.status-pill { padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 500; color: white; }
.status-pill.legacy { background: var(--text-secondary); }
.priority-dot { width: 8px; height: 8px; border-radius: 50%; }
.priority-dot.high { background: #f59e0b; }
.priority-dot.medium { background: #3b82f6; }
.priority-dot.low { background: #6b7280; }
.assignee-pill { font-size: 12px; color: var(--text-secondary); max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.type-tabs { display: flex; gap: 4px; overflow-x: auto; padding-bottom: 2px; }
.type-tab { display: flex; align-items: center; gap: 4px; padding: 8px 16px; border: none; border-bottom: 2px solid transparent; background: none; color: var(--text-secondary); font-size: 13px; font-weight: 500; cursor: pointer; white-space: nowrap; transition: all 0.2s; }
.type-tab:hover { color: var(--text-primary); }
.type-tab.active { color: var(--text-primary); border-bottom-color: var(--accent); }
.kanban-board { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; min-height: 70vh; }
.kanban-column { background: var(--bg-card); border-radius: 12px; padding: 16px; display: flex; flex-direction: column; }
.column-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--bg-secondary); }
.column-title { font-weight: 600; font-size: 14px; }
.column-count { background: var(--bg-secondary); padding: 2px 8px; border-radius: 12px; font-size: 12px; color: var(--text-secondary); }
.column-content { flex: 1; overflow-y: auto; }
.task-card { background: var(--bg-secondary); padding: 12px; border-radius: 8px; margin-bottom: 8px; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; position: relative; border-left: 4px solid transparent; }
.task-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-dropdown); }
.task-priority { position: absolute; left: 0; top: 0; bottom: 0; width: 4px; border-radius: 8px 0 0 8px; }
.task-card:has(.task-priority.high) { border-left-color: #f59e0b; }
.task-card:has(.task-priority.medium) { border-left-color: #3b82f6; }
.task-card:has(.task-priority.low) { border-left-color: #6b7280; }
.card-top { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.type-indicator { display: flex; align-items: center; justify-content: center; width: 18px; height: 18px; border-radius: 4px; color: white; }
.human-id-badge { font-size: 11px; font-family: monospace; color: var(--text-secondary); background: var(--bg-primary); padding: 1px 6px; border-radius: 4px; }
.task-card h4 { margin: 0 0 8px 0; font-size: 14px; font-weight: 500; }
.task-meta { display: flex; gap: 8px; font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; flex-wrap: wrap; }
.severity-badge { padding: 1px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; }
.severity-badge.critical { background: rgba(239,68,68,0.15); color: #ef4444; }
.severity-badge.major { background: rgba(245,158,11,0.15); color: #f59e0b; }
.severity-badge.minor { background: rgba(59,130,246,0.15); color: #3b82f6; }
.severity-badge.trivial { background: rgba(107,114,128,0.15); color: #6b7280; }
.due-date.overdue { color: #ef4444; }
.task-labels { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
.label { background: var(--accent); color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 6px; font-size: 14px; color: var(--text-secondary); }
.form-group input, .form-group select, .form-group textarea { width: 100%; }
.form-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--bg-secondary); }
.loading { display: flex; justify-content: center; padding: 60px; }
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.7); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 20px; }
.modal-content { background: var(--bg-card); border-radius: 16px; padding: 24px; max-width: 600px; width: 100%; max-height: 90vh; overflow-y: auto; position: relative; }
.modal-close { position: absolute; top: 16px; right: 16px; background: none; border: none; color: var(--text-secondary); font-size: 24px; cursor: pointer; }
/* WIP exceeded states */
.wip-exceeded .column-title { color: var(--error); }
.count-exceeded { color: var(--error) !important; font-weight: 700; }

.column-header-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.wip-limit-badge {
  font-size: 11px;
  opacity: 0.7;
}

.btn-wip-edit {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  opacity: 0;
  transition: opacity 0.15s;
}
.column-header:hover .btn-wip-edit { opacity: 1; }
.btn-wip-edit:hover { color: var(--text-primary); background: var(--bg-secondary); }

/* WIP Modal */
.wip-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 500;
}

.wip-modal {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 20px;
  width: 320px;
}

.wip-modal-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: var(--text-primary);
  text-transform: capitalize;
}

.wip-modal-hint {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0 0 14px 0;
}

.wip-modal-input {
  width: 100%;
  padding: 8px 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
  margin-bottom: 14px;
}
.wip-modal-input:focus { border-color: var(--accent); }

.wip-modal-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.btn-wip-clear {
  padding: 6px 12px;
  background: none;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
}
.btn-wip-clear:hover { color: var(--error); border-color: var(--error); }

.btn-wip-save {
  padding: 6px 14px;
  background: var(--accent);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}
.btn-wip-save:hover { opacity: 0.85; }

@media (max-width: 1024px) { .kanban-board { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px) { .kanban-board { grid-template-columns: 1fr; } }
</style>
