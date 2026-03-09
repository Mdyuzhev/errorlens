<template>
  <div class="tasks-page">
    <div class="page-header">
      <h1>Tasks</h1>
      <button class="btn btn-primary" @click="showCreateModal = true">
        + New Task
      </button>
    </div>

    <!-- Type filter tabs -->
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

    <!-- Kanban Board -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
    </div>

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

    <!-- Fullscreen Task Detail -->
    <TaskDetailView
      v-if="selectedTask"
      :task="selectedTask"
      @close="closeTask"
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
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useTasksStore } from '@/stores/tasks'
import { tasksApi, taskSettingsApi, projectsApi } from '@/services/api'
import RichEditor from '@/components/common/RichEditor.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import TaskDetailView from '@/components/tasks/TaskDetailView.vue'

const route = useRoute()
const store = useTasksStore()

const columns = [
  { id: 'todo', title: 'To Do' },
  { id: 'in_progress', title: 'In Progress' },
  { id: 'review', title: 'Review' },
  { id: 'done', title: 'Done' }
]

const showCreateModal = ref(false)
const selectedTask = ref(null)
const taskTypes = ref([])
const activeTypeFilter = ref('all')
let draggedTask = null

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
  const fullTask = await store.fetchTask(task.id)
  if (fullTask) {
    selectedTask.value = fullTask
  }
}

async function openTaskById(id) {
  const fullTask = await store.fetchTask(id)
  if (fullTask) {
    selectedTask.value = fullTask
  }
}

function closeTask() {
  selectedTask.value = null
}

async function refreshTask() {
  if (selectedTask.value) {
    const updated = await store.fetchTask(selectedTask.value.id)
    if (updated) selectedTask.value = updated
  }
  await store.fetchBoard(activeTypeFilter.value !== 'all' ? { type_slug: activeTypeFilter.value } : {})
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
      const typesRes = await taskSettingsApi.getTypes(projects[0].id)
      taskTypes.value = typesRes.data.filter(t => t.is_active)
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
  await store.fetchBoard()
  await loadTaskTypes()
  await openFromRoute()
})
</script>

<style scoped>
.type-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
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
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
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
