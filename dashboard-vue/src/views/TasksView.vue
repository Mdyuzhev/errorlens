<template>
  <div class="tasks-page">
    <div class="page-header">
      <h1>Tasks</h1>
      <button class="btn btn-primary" @click="showCreateModal = true">
        + New Task
      </button>
    </div>

    <!-- JQL Bar -->
    <JQLBar
      ref="jqlBarRef"
      :project-id="currentProjectId"
      @search="onJQLSearch"
      @clear="onJQLClear"
    />

    <!-- Saved Filters -->
    <SavedFilters
      :project-id="currentProjectId"
      :active-j-q-l="jqlStore.currentJQL"
      @apply="onApplyFilter"
    />

    <!-- View Toggle + Type filter tabs -->
    <div class="toolbar-row">
      <div class="type-tabs">
        <button
          class="type-tab"
          :class="{ active: activeTypeFilter === 'all' }"
          @click="filterByType('all')"
        >
          All
        </button>
        <button
          v-for="t in taskTypes"
          :key="t.slug"
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
        <button
          class="toggle-btn"
          :class="{ active: viewMode === 'board' }"
          @click="viewMode = 'board'"
          title="Kanban Board"
        >
          <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
            <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
          </svg>
        </button>
        <button
          class="toggle-btn"
          :class="{ active: viewMode === 'list' }"
          @click="viewMode = 'list'"
          title="List View"
        >
          <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
            <path fill-rule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
    </div>

    <!-- JQL List View -->
    <div v-else-if="viewMode === 'list'" class="task-list" data-testid="task-list">
      <div v-if="!listTasks.length" class="empty-list">
        <p v-if="jqlStore.currentJQL">No tasks match your query</p>
        <p v-else>No tasks found</p>
      </div>
      <div
        v-for="task in listTasks"
        :key="task.id"
        class="task-list-row"
        @click="openTask(task)"
      >
        <div class="row-left">
          <span v-if="task.type" class="type-indicator" :style="{ background: task.type.color }">
            <AppIcon :name="task.type.icon" :size="10" />
          </span>
          <span v-if="task.human_id" class="human-id-badge">{{ task.human_id }}</span>
          <span class="task-title">{{ task.title }}</span>
        </div>
        <div class="row-right">
          <span v-if="task.task_status" class="status-pill" :style="{ background: task.task_status.color }">
            {{ task.task_status.name }}
          </span>
          <span v-else class="status-pill legacy">{{ task.status }}</span>
          <span v-if="task.severity" class="severity-badge" :class="task.severity">{{ task.severity }}</span>
          <span class="priority-dot" :class="task.priority"></span>
          <span v-if="task.assignee_user" class="assignee-pill">
            {{ task.assignee_user.display_name || task.assignee_user.username }}
          </span>
        </div>
      </div>
    </div>

    <!-- Kanban Board -->
    <div v-else class="kanban-board" data-testid="kanban-board">
      <div
        v-for="column in columns"
        :key="column.id"
        class="kanban-column"
        @dragover.prevent
        @drop="onDrop($event, column.id)"
      >
        <div class="column-header">
          <span class="column-title">{{ column.title }}</span>
          <span class="column-count">{{ board[column.id]?.length || 0 }}</span>
        </div>

        <div class="column-content">
          <div
            v-for="task in board[column.id]"
            :key="task.id"
            class="task-card"
            draggable="true"
            @dragstart="onDragStart($event, task)"
            @click="openTask(task)"
          >
            <div class="task-priority" :class="task.priority"></div>
            <div class="card-top">
              <span v-if="task.type" class="type-indicator" :style="{ background: task.type.color }" :title="task.type.name">
                <AppIcon :name="task.type.icon" :size="10" />
              </span>
              <span v-if="task.human_id" class="human-id-badge">{{ task.human_id }}</span>
            </div>
            <h4>{{ task.title }}</h4>
            <div class="task-meta">
              <span v-if="task.assignee_user" class="assignee">
                {{ task.assignee_user.display_name || task.assignee_user.username }}
              </span>
              <span v-else-if="task.assignee" class="assignee">
                {{ task.assignee }}
              </span>
              <span v-if="task.severity" class="severity-badge" :class="task.severity">{{ task.severity }}</span>
              <span v-if="task.due_date" class="due-date" :class="{ overdue: isOverdue(task) }">
                {{ formatDate(task.due_date) }}
              </span>
            </div>
            <div v-if="task.labels?.length" class="task-labels">
              <span v-for="label in task.labels" :key="label" class="label">
                {{ label }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Read-only Task Viewer -->
    <TaskViewer
      v-if="viewerTask"
      :task="viewerTask"
      @close="closeViewer"
      @edit="openEditor"
      @open-task="openTaskById"
    />

    <!-- Fullscreen Task Editor -->
    <TaskDetailView
      v-if="editorTask"
      :task="editorTask"
      @close="closeEditor"
      @updated="refreshTask"
      @open-task="openTaskById"
    />

    <!-- Create Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal-content">
        <button class="modal-close" @click="showCreateModal = false">&times;</button>
        <h2>New Task</h2>

        <form @submit.prevent="saveTask">
          <div class="form-group">
            <label>Title *</label>
            <input v-model="form.title" required placeholder="Task title" />
          </div>

          <div class="form-group">
            <label>Description</label>
            <RichEditor
              v-model="form.descriptionJson"
              placeholder="Task description"
            />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>Type</label>
              <select v-model="form.type_id">
                <option value="">None</option>
                <option v-for="t in taskTypes" :key="t.id" :value="t.id">{{ t.name }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>Priority</label>
              <select v-model="form.priority">
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>Severity</label>
              <select v-model="form.severity">
                <option value="">None</option>
                <option value="critical">Critical</option>
                <option value="major">Major</option>
                <option value="minor">Minor</option>
                <option value="trivial">Trivial</option>
              </select>
            </div>
            <div class="form-group">
              <label>Environment</label>
              <select v-model="form.environment">
                <option value="">None</option>
                <option value="production">Production</option>
                <option value="staging">Staging</option>
                <option value="local">Local</option>
                <option value="all">All</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>Assignee</label>
              <input v-model="form.assignee" placeholder="Username" />
            </div>
            <div class="form-group">
              <label>Due Date</label>
              <input v-model="form.due_date" type="datetime-local" />
            </div>
          </div>

          <div class="form-group">
            <label>Labels (comma-separated)</label>
            <input v-model="labelsInput" placeholder="bug, feature, urgent" />
          </div>

          <div class="form-actions">
            <button type="button" class="btn btn-secondary" @click="showCreateModal = false">Cancel</button>
            <button type="submit" class="btn btn-primary">Create</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, inject } from 'vue'
import { useRoute } from 'vue-router'
import { useTasksStore } from '@/stores/tasks'
import { useJqlStore } from '@/stores/jql'
import { tasksApi, taskSettingsApi, projectsApi } from '@/services/api'
import RichEditor from '@/components/common/RichEditor.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import TaskDetailView from '@/components/tasks/TaskDetailView.vue'
import TaskViewer from '@/components/tasks/TaskViewer.vue'
import JQLBar from '@/components/tasks/JQLBar.vue'
import SavedFilters from '@/components/tasks/SavedFilters.vue'

const route = useRoute()
const store = useTasksStore()
const jqlStore = useJqlStore()

const columns = [
  { id: 'todo', title: 'To Do' },
  { id: 'in_progress', title: 'In Progress' },
  { id: 'review', title: 'Review' },
  { id: 'done', title: 'Done' }
]

const showCreateModal = ref(false)
const viewerTask = ref(null)
const editorTask = ref(null)
const taskTypes = ref([])
const activeTypeFilter = ref('all')
const viewMode = ref('board')
const currentProjectId = ref(null)
const jqlBarRef = ref(null)
const toast = inject('toast', null)
let draggedTask = null

const listTasks = computed(() =>
  jqlStore.currentJQL ? jqlStore.jqlResults : store.tasks
)

const form = ref({
  title: '',
  descriptionJson: null,
  status: 'todo',
  priority: 'medium',
  assignee: '',
  due_date: '',
  type_id: '',
  severity: '',
  environment: '',
})

const labelsInput = ref('')

const loading = computed(() => store.loading)
const board = computed(() => store.board)

function onDragStart(event, task) {
  draggedTask = task
  event.dataTransfer.effectAllowed = 'move'
}

async function onDrop(event, status) {
  if (draggedTask && draggedTask.status !== status) {
    await store.moveTask(draggedTask.id, status)
  }
  draggedTask = null
}

async function openTask(task) {
  try {
    const fullTask = await store.fetchTask(task.id)
    if (fullTask) {
      viewerTask.value = fullTask
    } else {
      showError('Task not found')
    }
  } catch {
    showError('Failed to load task')
  }
}

async function openTaskById(id) {
  try {
    const fullTask = await store.fetchTask(id)
    if (fullTask) {
      viewerTask.value = fullTask
    } else {
      showError('Task not found')
    }
  } catch {
    showError('Failed to load task')
  }
}

function closeViewer() {
  viewerTask.value = null
}

function openEditor() {
  editorTask.value = viewerTask.value
  viewerTask.value = null
}

function closeEditor() {
  editorTask.value = null
}

async function refreshTask() {
  if (editorTask.value) {
    const updated = await store.fetchTask(editorTask.value.id)
    if (updated) editorTask.value = updated
  }
  await store.fetchBoard(activeTypeFilter.value !== 'all' ? { type_slug: activeTypeFilter.value } : {})
}

function showError(msg) {
  if (toast) {
    toast({ type: 'error', message: msg })
  } else if (window.showToast) {
    window.showToast({ type: 'error', message: msg })
  }
}

function resetForm() {
  form.value = {
    title: '',
    descriptionJson: null,
    status: 'todo',
    priority: 'medium',
    assignee: '',
    due_date: '',
    type_id: '',
    severity: '',
    environment: '',
  }
  labelsInput.value = ''
}

async function saveTask() {
  const data = {
    title: form.value.title,
    description: form.value.descriptionJson ? JSON.stringify(form.value.descriptionJson) : null,
    status: form.value.status,
    priority: form.value.priority,
    assignee: form.value.assignee || null,
    labels: labelsInput.value.split(',').map(l => l.trim()).filter(Boolean),
    due_date: form.value.due_date || null,
    type_id: form.value.type_id || null,
    severity: form.value.severity || null,
    environment: form.value.environment || null,
  }

  await store.createTask(data)
  showCreateModal.value = false
  resetForm()
}

function onJQLSearch(jql) {
  viewMode.value = 'list'
}

function onJQLClear() {
  viewMode.value = 'board'
}

watch(viewMode, async (mode) => {
  if (mode === 'list' && !jqlStore.currentJQL && !store.tasks.length) {
    await store.fetchTasks({ project_id: currentProjectId.value })
  }
})

function onApplyFilter(jql) {
  if (jqlBarRef.value) {
    jqlBarRef.value.setJQL(jql)
  }
}

async function filterByType(slug) {
  activeTypeFilter.value = slug
  const params = slug !== 'all' ? { type_slug: slug } : {}
  await store.fetchBoard(params)
}

function formatDate(date) {
  if (!date) return ''
  return new Date(date).toLocaleDateString()
}

function isOverdue(task) {
  return task.due_date && new Date(task.due_date) < new Date() && task.status !== 'done'
}

async function loadTaskTypes() {
  try {
    const projectsRes = await projectsApi.list()
    const projects = projectsRes.data.items || projectsRes.data
    if (projects.length > 0) {
      currentProjectId.value = projects[0].id
      const typesRes = await taskSettingsApi.getTypes(projects[0].id)
      taskTypes.value = typesRes.data.filter(t => t.is_active)
      jqlStore.fetchSavedFilters(projects[0].id)
    }
  } catch { taskTypes.value = [] }
}

async function openFromRoute() {
  const id = route.params.id
  if (id) {
    await openTaskById(id)
  }
}

watch(() => route.params.id, openFromRoute)

onMounted(async () => {
  await Promise.all([
    store.fetchBoard(),
    store.fetchTasks({ project_id: null }),
    loadTaskTypes(),
  ])
  await openFromRoute()
})
</script>

<style scoped>
.toolbar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.view-toggle {
  display: flex;
  gap: 2px;
  background: var(--bg-card);
  border-radius: 8px;
  padding: 2px;
}

.toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 28px;
  border: none;
  background: none;
  color: var(--text-secondary);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}

.toggle-btn.active {
  background: var(--accent);
  color: white;
}

.toggle-btn:hover:not(.active) { background: var(--bg-secondary); }

/* Task List View */
.task-list {
  background: var(--bg-card);
  border-radius: 12px;
  overflow: hidden;
}

.empty-list {
  padding: 40px;
  text-align: center;
  color: var(--text-secondary);
}

.task-list-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--bg-secondary);
  cursor: pointer;
  transition: background 0.15s;
}

.task-list-row:hover { background: var(--bg-secondary); }
.task-list-row:last-child { border-bottom: none; }

.row-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.task-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}

.row-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.status-pill {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
  color: white;
}

.status-pill.legacy {
  background: var(--text-secondary);
}

.priority-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.priority-dot.high { background: #f59e0b; }
.priority-dot.medium { background: #3b82f6; }
.priority-dot.low { background: #6b7280; }

.assignee-pill {
  font-size: 12px;
  color: var(--text-secondary);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.type-tabs {
  display: flex;
  gap: 4px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.type-tab {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  border: none;
  border-bottom: 2px solid transparent;
  background: none;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.type-tab:hover { color: var(--text-primary); }
.type-tab.active {
  color: var(--text-primary);
  border-bottom-color: var(--accent);
}

.kanban-board {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  min-height: 70vh;
}

.kanban-column {
  background: var(--bg-card);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
}

.column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--bg-secondary);
}

.column-title {
  font-weight: 600;
  font-size: 14px;
}

.column-count {
  background: var(--bg-secondary);
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}

.column-content {
  flex: 1;
  overflow-y: auto;
}

.task-card {
  background: var(--bg-secondary);
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  position: relative;
  border-left: 4px solid transparent;
}

.task-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-dropdown);
}

.task-priority {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  border-radius: 8px 0 0 8px;
}

.task-card:has(.task-priority.high) { border-left-color: #f59e0b; }
.task-card:has(.task-priority.medium) { border-left-color: #3b82f6; }
.task-card:has(.task-priority.low) { border-left-color: #6b7280; }

.card-top {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.type-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 4px;
  color: white;
}

.human-id-badge {
  font-size: 11px;
  font-family: monospace;
  color: var(--text-secondary);
  background: var(--bg-primary);
  padding: 1px 6px;
  border-radius: 4px;
}

.task-card h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 500;
}

.task-meta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.severity-badge {
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
}

.severity-badge.critical { background: rgba(239,68,68,0.15); color: #ef4444; }
.severity-badge.major { background: rgba(245,158,11,0.15); color: #f59e0b; }
.severity-badge.minor { background: rgba(59,130,246,0.15); color: #3b82f6; }
.severity-badge.trivial { background: rgba(107,114,128,0.15); color: #6b7280; }

.due-date.overdue { color: #ef4444; }

.task-labels {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.label {
  background: var(--accent);
  color: white;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  color: var(--text-secondary);
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
}

.form-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--bg-secondary);
}

.loading {
  display: flex;
  justify-content: center;
  padding: 60px;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: var(--bg-card);
  border-radius: 16px;
  padding: 24px;
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
}

.modal-close {
  position: absolute;
  top: 16px;
  right: 16px;
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 24px;
  cursor: pointer;
}

@media (max-width: 1024px) {
  .kanban-board {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .kanban-board {
    grid-template-columns: 1fr;
  }
}
</style>
