<template>
  <div class="tasks-page">
    <div class="page-header">
      <h1>Tasks</h1>
      <button class="btn btn-primary" @click="showCreateModal = true">
        + New Task
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
            <h4>
              <span v-if="task.human_id" class="human-id-badge">{{ task.human_id }}</span>
              {{ task.title }}
            </h4>
            <div class="task-meta">
              <span v-if="task.assignee" class="assignee">
                {{ task.assignee }}
              </span>
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

    <!-- Create/Edit Modal -->
    <div v-if="showCreateModal || selectedTask" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <button class="modal-close" @click="closeModal">&times;</button>

        <h2>{{ selectedTask ? 'Edit Task' : 'New Task' }}</h2>

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
              <label>Status</label>
              <select v-model="form.status">
                <option value="todo">To Do</option>
                <option value="in_progress">In Progress</option>
                <option value="review">Review</option>
                <option value="done">Done</option>
              </select>
            </div>

            <div class="form-group">
              <label>Priority</label>
              <select v-model="form.priority">
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
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

          <!-- Backlinks -->
          <div v-if="selectedTask && backlinks.length" class="backlinks-section">
            <label>Mentioned in articles ({{ backlinks.length }}):</label>
            <div v-for="bl in backlinks" :key="bl.article_id" class="backlink-item" @click="goToArticle(bl)">
              <span class="backlink-icon">{'\u{1F4C4}'}</span>
              {{ bl.article_title }}
            </div>
          </div>

          <div class="form-actions">
            <button v-if="selectedTask" type="button" class="btn btn-danger" @click="deleteTask">
              Delete
            </button>
            <button type="button" class="btn btn-secondary" @click="closeModal">Cancel</button>
            <button type="submit" class="btn btn-primary">Save</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useTasksStore } from '@/stores/tasks'
import { entityLinksApi } from '@/services/api'
import RichEditor from '@/components/common/RichEditor.vue'

const store = useTasksStore()

const columns = [
  { id: 'todo', title: 'To Do' },
  { id: 'in_progress', title: 'In Progress' },
  { id: 'review', title: 'Review' },
  { id: 'done', title: 'Done' }
]

const showCreateModal = ref(false)
const selectedTask = ref(null)
const backlinks = ref([])
let draggedTask = null

const form = ref({
  title: '',
  description: '',
  descriptionJson: null,
  status: 'todo',
  priority: 'medium',
  assignee: '',
  due_date: '',
  labels: []
})

function parseContent(raw) {
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw)
    if (parsed && parsed.type === 'doc') return parsed
  } catch {}
  return { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: raw }] }] }
}

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

function openTask(task) {
  selectedTask.value = task
  loadBacklinks(task.id)
  form.value = {
    title: task.title || '',
    description: task.description || '',
    descriptionJson: parseContent(task.description),
    status: task.status || 'todo',
    priority: task.priority || 'medium',
    assignee: task.assignee || '',
    due_date: task.due_date ? task.due_date.slice(0, 16) : ''
  }
  labelsInput.value = task.labels?.join(', ') || ''
}

function closeModal() {
  showCreateModal.value = false
  selectedTask.value = null
  backlinks.value = []
  resetForm()
}

async function loadBacklinks(taskId) {
  try {
    const res = await entityLinksApi.getBacklinks('task', taskId)
    backlinks.value = res.data.items || []
  } catch {
    backlinks.value = []
  }
}

function goToArticle(bl) {
  window.location.href = '/#/articles'
}

function resetForm() {
  form.value = {
    title: '',
    description: '',
    descriptionJson: null,
    status: 'todo',
    priority: 'medium',
    assignee: '',
    due_date: ''
  }
  labelsInput.value = ''
}

async function saveTask() {
  const data = {
    title: form.value.title,
    description: form.value.descriptionJson ? JSON.stringify(form.value.descriptionJson) : form.value.description,
    status: form.value.status,
    priority: form.value.priority,
    assignee: form.value.assignee,
    labels: labelsInput.value.split(',').map(l => l.trim()).filter(Boolean),
    due_date: form.value.due_date || null
  }

  if (selectedTask.value) {
    await store.updateTask(selectedTask.value.id, data)
  } else {
    await store.createTask(data)
  }

  closeModal()
}

async function deleteTask() {
  if (selectedTask.value && confirm('Delete this task?')) {
    await store.deleteTask(selectedTask.value.id)
    closeModal()
  }
}

function formatDate(date) {
  if (!date) return ''
  return new Date(date).toLocaleDateString()
}

function isOverdue(task) {
  return task.due_date && new Date(task.due_date) < new Date() && task.status !== 'done'
}

onMounted(() => {
  store.fetchBoard()
})
</script>

<style scoped>
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
  cursor: grab;
  transition: transform 0.2s, box-shadow 0.2s;
  position: relative;
  border-left: 4px solid transparent;
}

.task-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.task-card:active {
  cursor: grabbing;
}

.task-priority {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  border-radius: 8px 0 0 8px;
}

.task-card:has(.task-priority.urgent) {
  border-left-color: #ef4444;
}

.task-card:has(.task-priority.high) {
  border-left-color: #f59e0b;
}

.task-card:has(.task-priority.medium) {
  border-left-color: #3b82f6;
}

.task-card:has(.task-priority.low) {
  border-left-color: #6b7280;
}

.human-id-badge {
  font-size: 11px;
  font-family: monospace;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.08);
  padding: 1px 6px;
  border-radius: 4px;
  margin-right: 4px;
  vertical-align: middle;
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
  margin-bottom: 8px;
}

.due-date.overdue {
  color: #ef4444;
}

.task-labels {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
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

.form-actions .btn-danger {
  margin-right: auto;
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
  max-width: 500px;
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

.backlinks-section {
  margin-top: 16px;
  padding: 12px;
  background: rgba(99, 102, 241, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(99, 102, 241, 0.15);
}

.backlinks-section label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

.backlink-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.15s;
}

.backlink-item:hover {
  background: rgba(99, 102, 241, 0.1);
}

.backlink-icon {
  font-size: 14px;
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
