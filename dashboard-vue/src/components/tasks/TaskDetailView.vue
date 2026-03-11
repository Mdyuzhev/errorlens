<template>
  <div class="task-detail-overlay" @keydown.esc="$emit('close')">
    <div class="task-detail">
      <!-- Header -->
      <div class="task-header">
        <button class="back-btn" @click="$emit('close')" title="Close">
          <AppIcon name="arrow-left" :size="18" />
        </button>
        <div class="header-info">
          <div class="header-badges">
            <span v-if="task.type" class="type-badge" :style="{ background: task.type.color }">
              <AppIcon :name="task.type.icon" :size="12" />
              {{ task.type.name }}
            </span>
            <span v-if="task.human_id" class="human-id">{{ task.human_id }}</span>
            <span class="status-badge" :class="task.status" @click="showStatusDropdown = !showStatusDropdown">
              {{ task.task_status?.name || task.status }}
            </span>
            <!-- Status dropdown -->
            <div v-if="showStatusDropdown && allowedTransitions.length" class="status-dropdown">
              <button
                v-for="s in allowedTransitions"
                :key="s.id"
                class="status-option"
                :style="{ borderLeftColor: s.color }"
                @click="changeStatus(s)"
              >
                {{ s.name }}
              </button>
            </div>
          </div>
          <div class="header-actions">
            <button v-if="!editing" class="btn btn-sm" @click="editing = true">Edit</button>
            <button v-if="editing" class="btn btn-sm btn-primary" @click="saveTask">Save</button>
            <button v-if="editing" class="btn btn-sm" @click="cancelEdit">Cancel</button>
            <button class="btn btn-sm btn-danger" @click="confirmDelete">Delete</button>
          </div>
        </div>
      </div>

      <div class="task-body">
        <!-- Left: Main content -->
        <div class="task-main">
          <!-- Title -->
          <div v-if="editing" class="edit-title">
            <input v-model="editForm.title" class="title-input" placeholder="Task title" />
          </div>
          <h1 v-else class="task-title" @click="editing = true">{{ task.title }}</h1>

          <!-- Description -->
          <div class="description-section">
            <h3>Description</h3>
            <RichEditor
              v-if="editing"
              v-model="editForm.descriptionJson"
              placeholder="Add description..."
            />
            <div v-else-if="task.description" class="description-content" @click="editing = true">
              <RichEditor :modelValue="parseContent(task.description)" :editable="false" :showToolbar="false" />
            </div>
            <div v-else class="empty-description" @click="editing = true">
              Click to add description...
            </div>
          </div>

          <!-- Activity Feed -->
          <TaskActivityFeed
            :taskId="task.id"
            :activity="activity"
            @comment-added="loadActivity"
          />
        </div>

        <!-- Right: Sidebar -->
        <div class="task-sidebar">
          <!-- Details -->
          <div class="sidebar-section">
            <h4>Details</h4>
            <div class="detail-row">
              <label>Priority</label>
              <select v-if="editing" v-model="editForm.priority">
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
              <span v-else class="priority-badge" :class="task.priority">{{ task.priority }}</span>
            </div>
            <div class="detail-row">
              <label>Severity</label>
              <select v-if="editing" v-model="editForm.severity">
                <option value="">None</option>
                <option value="critical">Critical</option>
                <option value="major">Major</option>
                <option value="minor">Minor</option>
                <option value="trivial">Trivial</option>
              </select>
              <span v-else>{{ task.severity || '-' }}</span>
            </div>
            <div class="detail-row">
              <label>Environment</label>
              <select v-if="editing" v-model="editForm.environment">
                <option value="">None</option>
                <option value="production">Production</option>
                <option value="staging">Staging</option>
                <option value="local">Local</option>
                <option value="all">All</option>
              </select>
              <span v-else>{{ task.environment || '-' }}</span>
            </div>
          </div>

          <!-- People -->
          <div class="sidebar-section">
            <h4>People</h4>
            <div class="detail-row">
              <label>Reporter</label>
              <span>{{ task.reporter?.display_name || task.reporter?.username || '-' }}</span>
            </div>
            <div class="detail-row">
              <label>Assignee</label>
              <input v-if="editing" v-model="editForm.assignee" placeholder="Username" />
              <span v-else>{{ task.assignee_user?.display_name || task.assignee_user?.username || task.assignee || '-' }}</span>
            </div>
            <div class="detail-row">
              <label>Due Date</label>
              <input v-if="editing" v-model="editForm.due_date" type="datetime-local" />
              <span v-else :class="{ overdue: isOverdue }">{{ formatDate(task.due_date) || '-' }}</span>
            </div>
          </div>

          <!-- Time Tracking -->
          <div class="sidebar-section">
            <h4>Time</h4>
            <div class="detail-row">
              <label>Estimated</label>
              <input v-if="editing" v-model.number="editForm.estimated_hours" type="number" step="0.5" min="0" />
              <span v-else>{{ task.estimated_hours ? task.estimated_hours + 'h' : '-' }}</span>
            </div>
            <div class="detail-row">
              <label>Spent</label>
              <input v-if="editing" v-model.number="editForm.spent_hours" type="number" step="0.5" min="0" />
              <span v-else>{{ task.spent_hours ? task.spent_hours + 'h' : '-' }}</span>
            </div>
          </div>

          <!-- Relations -->
          <div class="sidebar-section">
            <h4>
              Relations
              <button class="btn-icon" @click="showAddRelation = true" title="Add relation">+</button>
            </h4>
            <div v-if="relations.length" class="relations-list">
              <div v-for="r in relations" :key="r.id" class="relation-item">
                <span class="relation-type">{{ formatRelationType(r.relation_type) }}</span>
                <span class="relation-target" @click="$emit('open-task', r.target_task_id)">
                  <span v-if="r.target_task?.human_id" class="rel-id">{{ r.target_task.human_id }}</span>
                  {{ r.target_task?.title || r.target_task_id }}
                </span>
                <button class="btn-icon-sm" @click="removeRelation(r.id)" title="Remove">&times;</button>
              </div>
            </div>
            <div v-else class="empty-hint">No relations</div>
          </div>

          <!-- Children -->
          <div v-if="task.children?.length" class="sidebar-section">
            <h4>Subtasks</h4>
            <div v-for="child in task.children" :key="child.id" class="child-item" @click="$emit('open-task', child.id)">
              <span class="child-status" :class="child.status"></span>
              <span v-if="child.human_id" class="child-id">{{ child.human_id }}</span>
              {{ child.title }}
            </div>
          </div>

          <!-- Labels -->
          <div v-if="task.labels?.length || editing" class="sidebar-section">
            <h4>Labels</h4>
            <input v-if="editing" v-model="editForm.labelsInput" placeholder="Comma-separated labels" />
            <div v-else class="labels-list">
              <span v-for="l in task.labels" :key="l" class="label-tag">{{ l }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Add Relation Modal -->
    <div v-if="showAddRelation" class="modal-overlay" @click.self="showAddRelation = false">
      <div class="modal-sm">
        <h3>Add Relation</h3>
        <div class="form-group">
          <label>Type</label>
          <select v-model="newRelation.relation_type">
            <option value="blocks">Blocks</option>
            <option value="blocked_by">Blocked by</option>
            <option value="duplicates">Duplicates</option>
            <option value="relates_to">Related to</option>
          </select>
        </div>
        <div class="form-group">
          <label>Task ID or Human ID</label>
          <input v-model="newRelation.target_task_id" placeholder="Task ID" />
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showAddRelation = false">Cancel</button>
          <button class="btn btn-primary" @click="addRelation">Add</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useTasksStore } from '@/stores/tasks'
import { tasksApi } from '@/services/api'
import RichEditor from '@/components/common/RichEditor.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import TaskActivityFeed from './TaskActivityFeed.vue'

const props = defineProps({
  task: { type: Object, required: true },
})

const emit = defineEmits(['close', 'updated', 'open-task'])

const store = useTasksStore()
const editing = ref(false)
const showStatusDropdown = ref(false)
const showAddRelation = ref(false)
const allowedTransitions = ref([])
const activity = ref([])
const relations = ref([])

const editForm = ref({})
const newRelation = ref({ relation_type: 'relates_to', target_task_id: '' })

function initEditForm() {
  editForm.value = {
    title: props.task.title,
    descriptionJson: parseContent(props.task.description),
    priority: props.task.priority,
    severity: props.task.severity || '',
    environment: props.task.environment || '',
    assignee: props.task.assignee || '',
    due_date: props.task.due_date ? props.task.due_date.slice(0, 16) : '',
    estimated_hours: props.task.estimated_hours || '',
    spent_hours: props.task.spent_hours || '',
    labelsInput: props.task.labels?.join(', ') || '',
  }
}

function parseContent(raw) {
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw)
    if (parsed?.type === 'doc') return parsed
  } catch {}
  return { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: raw }] }] }
}

const isOverdue = computed(() =>
  props.task.due_date && new Date(props.task.due_date) < new Date() && props.task.status !== 'done'
)

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString()
}

function formatRelationType(type) {
  const map = { blocks: 'Blocks', blocked_by: 'Blocked by', duplicates: 'Duplicates', duplicated_by: 'Duplicated by', relates_to: 'Related to' }
  return map[type] || type
}

async function loadTransitions() {
  try {
    const res = await tasksApi.getAllowedTransitions(props.task.id)
    allowedTransitions.value = res.data
  } catch { allowedTransitions.value = [] }
}

async function loadActivity() {
  try {
    const res = await tasksApi.getActivity(props.task.id, { limit: 50 })
    activity.value = res.data
  } catch { activity.value = [] }
}

async function loadRelations() {
  try {
    const res = await tasksApi.getRelations(props.task.id)
    relations.value = res.data
  } catch { relations.value = [] }
}

async function changeStatus(s) {
  showStatusDropdown.value = false
  if (s.id) {
    await tasksApi.moveStatus(props.task.id, s.id)
  } else {
    await store.moveTask(props.task.id, s.slug)
  }
  emit('updated')
  await loadTransitions()
  await loadActivity()
}

async function saveTask() {
  const data = {
    title: editForm.value.title,
    description: editForm.value.descriptionJson ? JSON.stringify(editForm.value.descriptionJson) : null,
    priority: editForm.value.priority,
    severity: editForm.value.severity || null,
    environment: editForm.value.environment || null,
    assignee: editForm.value.assignee || null,
    due_date: editForm.value.due_date || null,
    estimated_hours: editForm.value.estimated_hours || null,
    spent_hours: editForm.value.spent_hours || null,
    labels: editForm.value.labelsInput.split(',').map(l => l.trim()).filter(Boolean),
  }
  await store.updateTask(props.task.id, data)
  editing.value = false
  emit('updated')
}

function cancelEdit() {
  editing.value = false
  initEditForm()
}

async function confirmDelete() {
  if (confirm('Delete this task?')) {
    await store.deleteTask(props.task.id)
    emit('close')
  }
}

async function addRelation() {
  await store.createRelation(props.task.id, newRelation.value)
  showAddRelation.value = false
  newRelation.value = { relation_type: 'relates_to', target_task_id: '' }
  await loadRelations()
}

async function removeRelation(relationId) {
  await store.deleteRelation(props.task.id, relationId)
  await loadRelations()
}

onMounted(() => {
  initEditForm()
  loadTransitions()
  loadActivity()
  loadRelations()
})

watch(() => props.task.id, () => {
  initEditForm()
  loadTransitions()
  loadActivity()
  loadRelations()
})
</script>

<style scoped>
.task-detail-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: var(--bg-primary);
  overflow-y: auto;
}

.task-detail {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.task-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--bg-secondary);
}

.back-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
}

.back-btn:hover { background: var(--bg-secondary); }

.header-info {
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-badges {
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
}

.type-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  color: white;
}

.human-id {
  font-family: monospace;
  font-size: 14px;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  padding: 4px 8px;
  border-radius: 4px;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  background: var(--bg-secondary);
}

.status-badge.todo { color: #6b7280; }
.status-badge.in_progress { color: #3b82f6; }
.status-badge.review { color: #f59e0b; }
.status-badge.done { color: #10b981; }

.status-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 4px;
  background: var(--bg-card);
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  z-index: 10;
  min-width: 160px;
  overflow: hidden;
}

.status-option {
  display: block;
  width: 100%;
  padding: 10px 14px;
  border: none;
  border-left: 3px solid transparent;
  background: none;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  text-align: left;
}

.status-option:hover { background: var(--bg-secondary); }

.header-actions {
  display: flex;
  gap: 8px;
}

.task-body {
  display: flex;
  gap: 24px;
}

.task-main {
  flex: 1;
  min-width: 0;
}

.task-title {
  font-size: 24px;
  margin: 0 0 20px 0;
  cursor: pointer;
}

.title-input {
  width: 100%;
  font-size: 24px;
  font-weight: bold;
  padding: 8px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-primary);
  margin-bottom: 20px;
}

.description-section {
  margin-bottom: 24px;
}

.description-section h3 {
  font-size: 16px;
  margin: 0 0 12px 0;
}

.description-content {
  cursor: pointer;
  min-height: 60px;
}

.empty-description {
  padding: 20px;
  border: 1px dashed var(--border-color);
  border-radius: 8px;
  color: var(--text-secondary);
  cursor: pointer;
  text-align: center;
}

.task-sidebar {
  width: 320px;
  flex-shrink: 0;
}

.sidebar-section {
  background: var(--bg-card);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.sidebar-section h4 {
  margin: 0 0 12px 0;
  font-size: 13px;
  text-transform: uppercase;
  color: var(--text-secondary);
  letter-spacing: 0.5px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--bg-secondary);
  font-size: 13px;
}

.detail-row:last-child { border-bottom: none; }

.detail-row label {
  color: var(--text-secondary);
  font-size: 12px;
}

.detail-row select,
.detail-row input {
  max-width: 160px;
  font-size: 13px;
}

.priority-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.priority-badge.high { background: rgba(245,158,11,0.15); color: #f59e0b; }
.priority-badge.medium { background: rgba(59,130,246,0.15); color: #3b82f6; }
.priority-badge.low { background: rgba(107,114,128,0.15); color: #6b7280; }

.overdue { color: #ef4444; }

.relations-list { display: flex; flex-direction: column; gap: 6px; }

.relation-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 6px 8px;
  border-radius: 6px;
  background: var(--bg-secondary);
}

.relation-type {
  font-size: 10px;
  text-transform: uppercase;
  color: var(--text-secondary);
  font-weight: 600;
  min-width: 70px;
}

.relation-target {
  flex: 1;
  cursor: pointer;
  color: var(--accent);
}

.rel-id {
  font-family: monospace;
  margin-right: 4px;
}

.btn-icon-sm {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 14px;
  padding: 2px 4px;
}

.btn-icon {
  background: none;
  border: none;
  color: var(--accent);
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
}

.child-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 0;
  font-size: 13px;
  cursor: pointer;
  border-bottom: 1px solid var(--bg-secondary);
}

.child-item:last-child { border-bottom: none; }
.child-item:hover { color: var(--accent); }

.child-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #6b7280;
}

.child-status.in_progress { background: #3b82f6; }
.child-status.review { background: #f59e0b; }
.child-status.done { background: #10b981; }

.child-id {
  font-family: monospace;
  font-size: 11px;
  color: var(--text-secondary);
}

.labels-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.label-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  background: var(--accent);
  color: white;
}

.empty-hint {
  font-size: 12px;
  color: var(--text-secondary);
  font-style: italic;
}

.btn-sm {
  padding: 6px 14px;
  font-size: 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.btn-sm:hover { opacity: 0.9; }
.btn-sm.btn-primary { background: var(--accent); color: white; }
.btn-sm.btn-danger { background: #ef4444; color: white; }

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.modal-sm {
  background: var(--bg-card);
  border-radius: 12px;
  padding: 24px;
  max-width: 400px;
  width: 100%;
}

.modal-sm h3 { margin: 0 0 16px 0; }

.form-group {
  margin-bottom: 12px;
}

.form-group label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}

@media (max-width: 768px) {
  .task-body {
    flex-direction: column;
  }
  .task-sidebar {
    width: 100%;
  }
}
</style>
