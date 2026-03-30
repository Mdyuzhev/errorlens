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
            <button v-if="!editing" class="btn-sm" @click="editing = true">Edit</button>
            <button v-if="editing" class="btn-sm btn-primary" @click="saveTask">Save</button>
            <button v-if="editing" class="btn-sm" @click="cancelEdit">Cancel</button>
            <button class="btn-sm btn-danger" @click="confirmDelete">Delete</button>
          </div>
        </div>
      </div>

      <!-- Tabs -->
      <div class="tab-bar">
        <button
          v-for="t in tabs"
          :key="t.key"
          class="tab-btn"
          :class="{ active: activeTab === t.key }"
          @click="activeTab = t.key"
        >{{ t.label }}</button>
      </div>

      <div class="task-body">
        <!-- Left: Main content -->
        <div class="task-main">
          <!-- Title -->
          <div v-if="editing" class="edit-title">
            <input v-model="editForm.title" class="title-input" placeholder="Task title" />
          </div>
          <h1 v-else class="task-title" @click="editing = true">{{ task.title }}</h1>

          <!-- Tab: Details -->
          <template v-if="activeTab === 'details'">
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

            <!-- Attachments -->
            <AttachmentsBlock :issueId="task.id" :attachments="task.attachments || []" />
          </template>

          <!-- Tab: Activity -->
          <template v-if="activeTab === 'activity'">
            <TaskActivityFeed
              :taskId="task.id"
              :activity="activity"
              @comment-added="loadActivity"
            />
          </template>

          <!-- Tab: Work Log -->
          <template v-if="activeTab === 'worklog'">
            <WorkLogBlock
              :issueId="task.id"
              :estimated="task.estimated_hours"
              :spent="task.spent_hours"
              :logs="workLogs"
            />
          </template>
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
              <label>Component</label>
              <select v-if="editing" v-model="editForm.component_id">
                <option value="">None</option>
                <option v-for="c in components" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
              <span v-else>{{ task.component?.name || '-' }}</span>
            </div>
            <div class="detail-row">
              <label>Story Points</label>
              <input v-if="editing" v-model.number="editForm.story_points" type="number" min="0" step="1" />
              <span v-else>{{ task.story_points ?? '-' }}</span>
            </div>
            <div v-if="task.sprint" class="detail-row">
              <label>Sprint</label>
              <span class="sprint-badge">{{ task.sprint.name }}</span>
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

          <!-- Time -->
          <div class="sidebar-section">
            <h4>Time</h4>
            <div class="detail-row">
              <label>Estimated</label>
              <input v-if="editing" v-model.number="editForm.estimated_hours" type="number" step="0.5" min="0" />
              <span v-else>{{ task.estimated_hours ? task.estimated_hours + 'h' : '-' }}</span>
            </div>
            <div class="detail-row">
              <label>Spent</label>
              <span>{{ task.spent_hours ? task.spent_hours + 'h' : '-' }}</span>
            </div>
          </div>

          <!-- Custom Fields -->
          <div v-if="customFields.length" class="sidebar-section">
            <h4>Custom Fields</h4>
            <div v-for="field in customFields" :key="field.id" class="detail-row">
              <label>{{ field.name }}</label>
              <input
                v-if="editing"
                v-model="editCustomValues[field.id]"
                :type="field.field_type === 'number' ? 'number' : 'text'"
                :placeholder="field.name"
              />
              <span v-else>{{ customValues[field.id] ?? '-' }}</span>
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

          <!-- Linked Test Cases -->
          <div
            v-if="linkedTestCases.length > 0 || linkedTestCasesLoading"
            class="sidebar-section"
          >
            <h4>Test Cases</h4>
            <div v-if="linkedTestCasesLoading" class="empty-hint">Loading...</div>
            <div v-else class="linked-cases-list">
              <div
                v-for="tc in linkedTestCases"
                :key="tc.id"
                class="linked-case-item"
                style="cursor: pointer"
                @click="openTestCase(tc)"
                :title="'Open ' + (tc.human_id || tc.title)"
              >
                <span v-if="tc.human_id" class="linked-case-id">{{ tc.human_id }}</span>
                <span class="linked-case-title">{{ tc.title || tc.id?.slice(0,8) }}</span>
                <span
                  class="linked-case-status"
                  :class="'tc-status-' + (tc.status || 'draft').toLowerCase()"
                >{{ tc.status || 'Draft' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useIssuesStore } from '@/stores/issues'
import AttachmentsBlock from './AttachmentsBlock.vue'
import WorkLogBlock from './WorkLogBlock.vue'
import TaskActivityFeed from '@/components/tasks/TaskActivityFeed.vue'
import RichEditor from '@/components/common/RichEditor.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import { customFieldsApi, tasksApi, testCasesApi } from '@/services/api'

const props = defineProps({
  task: { type: Object, required: true },
})

const emit = defineEmits(['close', 'updated', 'open-task'])

const router = useRouter()
const store = useIssuesStore()
const editing = ref(false)
const activeTab = ref('details')
const showStatusDropdown = ref(false)
const allowedTransitions = ref([])
const activity = ref([])
const workLogs = ref([])
const components = ref([])
const customFields = ref([])
const customValues = ref({})
const editCustomValues = ref({})
const linkedTestCases = ref([])
const linkedTestCasesLoading = ref(false)

const tabs = [
  { key: 'details', label: 'Details' },
  { key: 'activity', label: 'Activity' },
  { key: 'worklog', label: 'Work Log' },
]

const editForm = ref({})

function initEditForm() {
  editForm.value = {
    title: props.task.title,
    descriptionJson: parseContent(props.task.description),
    priority: props.task.priority,
    severity: props.task.severity || '',
    component_id: props.task.component?.id || '',
    story_points: props.task.story_points ?? '',
    assignee: props.task.assignee || '',
    due_date: props.task.due_date ? props.task.due_date.slice(0, 16) : '',
    estimated_hours: props.task.estimated_hours || '',
    labelsInput: props.task.labels?.join(', ') || '',
  }
  editCustomValues.value = { ...customValues.value }
}

function parseContent(raw) {
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw)
    if (parsed?.type === 'doc') return parsed
  } catch { /* ignore */ }
  return { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: raw }] }] }
}

const isOverdue = computed(() =>
  props.task.due_date && new Date(props.task.due_date) < new Date() && props.task.status !== 'done'
)

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString()
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

async function loadWorkLogs() {
  try {
    await store.fetchWorkLogs(props.task.id)
    workLogs.value = store.workLogs[props.task.id] || []
  } catch { workLogs.value = [] }
}

async function loadComponents() {
  if (props.task.project_id) {
    await store.fetchComponents(props.task.project_id)
    components.value = store.components
  }
}

async function loadCustomFields() {
  try {
    const res = await customFieldsApi.listFields(props.task.project_id, props.task.type_id)
    customFields.value = res.data || []
    const valRes = await customFieldsApi.getValues(props.task.id)
    const vals = {}
    for (const v of (valRes.data || [])) {
      vals[v.field_id] = v.value
    }
    customValues.value = vals
  } catch {
    customFields.value = []
    customValues.value = {}
  }
}

async function changeStatus(s) {
  showStatusDropdown.value = false
  try {
    if (s.id) {
      await tasksApi.moveStatus(props.task.id, s.id)
    } else {
      await store.moveTask(props.task.id, s.slug)
    }
    emit('updated')
    await loadTransitions()
    await loadActivity()
  } catch (e) {
    const detail = e.response?.data?.detail
    const msg = typeof detail === 'string' ? detail : 'Transition not allowed'
    if (window.showToast) window.showToast(msg, 'error')
  }
}

async function saveTask() {
  const data = {
    title: editForm.value.title,
    description: editForm.value.descriptionJson ? JSON.stringify(editForm.value.descriptionJson) : null,
    priority: editForm.value.priority,
    severity: editForm.value.severity || null,
    component_id: editForm.value.component_id || null,
    story_points: editForm.value.story_points || null,
    assignee: editForm.value.assignee || null,
    due_date: editForm.value.due_date || null,
    estimated_hours: editForm.value.estimated_hours || null,
    labels: editForm.value.labelsInput.split(',').map(l => l.trim()).filter(Boolean),
  }
  await store.updateTask(props.task.id, data)

  // Save custom field values
  if (customFields.value.length) {
    const cfValues = Object.entries(editCustomValues.value)
      .filter(([, v]) => v !== '' && v !== null && v !== undefined)
      .map(([fieldId, value]) => ({ field_id: fieldId, value }))
    if (cfValues.length) {
      try { await customFieldsApi.setValues(props.task.id, cfValues) } catch { /* ignore */ }
    }
  }

  editing.value = false
  emit('updated')
  await loadCustomFields()
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

async function loadLinkedTestCases() {
  if (!props.task?.id) return
  linkedTestCasesLoading.value = true
  try {
    const res = await testCasesApi.list({ linked_issue_id: props.task.id, limit: 20 })
    linkedTestCases.value = Array.isArray(res.data) ? res.data : res.data.items || []
  } catch {
    linkedTestCases.value = []
  } finally {
    linkedTestCasesLoading.value = false
  }
}

function openTestCase(tc) {
  emit('close')
  setTimeout(() => {
    router.push({ path: '/qa', query: { tab: 'tree', tcId: tc.id } })
  }, 100)
}

function loadAll() {
  initEditForm()
  loadTransitions()
  loadActivity()
  loadWorkLogs()
  loadComponents()
  loadCustomFields()
  loadLinkedTestCases()
}

onMounted(loadAll)
watch(() => props.task.id, loadAll)
</script>

<style scoped>
.task-detail-overlay { position: fixed; inset: 0; z-index: 100; background: var(--bg-primary); overflow-y: auto; }
.task-detail { max-width: 1200px; margin: 0 auto; padding: 20px; }
.task-header { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid var(--bg-secondary); }
.back-btn { background: none; border: none; color: var(--text-secondary); cursor: pointer; padding: 8px; border-radius: 6px; }
.back-btn:hover { background: var(--bg-secondary); }
.header-info { flex: 1; display: flex; justify-content: space-between; align-items: center; }
.header-badges { display: flex; align-items: center; gap: 8px; position: relative; }
.type-badge { display: flex; align-items: center; gap: 4px; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; color: white; }
.human-id { font-family: monospace; font-size: 14px; color: var(--text-secondary); background: var(--bg-secondary); padding: 4px 8px; border-radius: 4px; }
.status-badge { padding: 4px 12px; border-radius: 12px; font-size: 13px; font-weight: 500; cursor: pointer; background: var(--bg-secondary); }
.status-badge.todo { color: #6b7280; }
.status-badge.in_progress { color: #3b82f6; }
.status-badge.review { color: #f59e0b; }
.status-badge.done { color: #10b981; }
.status-dropdown { position: absolute; top: 100%; left: 0; margin-top: 4px; background: var(--bg-card); border-radius: 8px; box-shadow: var(--shadow-dropdown); z-index: 10; min-width: 160px; overflow: hidden; }
.status-option { display: block; width: 100%; padding: 10px 14px; border: none; border-left: 3px solid transparent; background: none; color: var(--text-primary); font-size: 13px; cursor: pointer; text-align: left; }
.status-option:hover { background: var(--bg-secondary); }
.header-actions { display: flex; gap: 8px; }
.tab-bar { display: flex; gap: 4px; margin-bottom: 20px; border-bottom: 1px solid var(--bg-secondary); }
.tab-btn { padding: 8px 16px; border: none; background: none; color: var(--text-secondary); font-size: 13px; font-weight: 500; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; transition: color 0.15s, border-color 0.15s; }
.tab-btn:hover { color: var(--text-primary); }
.tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }
.task-body { display: flex; gap: 24px; }
.task-main { flex: 1; min-width: 0; }
.task-title { font-size: 24px; margin: 0 0 20px 0; cursor: pointer; }
.title-input { width: 100%; font-size: 24px; font-weight: bold; padding: 8px; border: 1px solid var(--border-color); border-radius: 8px; background: var(--bg-card); color: var(--text-primary); margin-bottom: 20px; }
.description-section { margin-bottom: 24px; }
.description-section h3 { font-size: 16px; margin: 0 0 12px 0; }
.description-content { cursor: pointer; min-height: 60px; }
.empty-description { padding: 20px; border: 1px dashed var(--border-color); border-radius: 8px; color: var(--text-secondary); cursor: pointer; text-align: center; }
.task-sidebar { width: 320px; flex-shrink: 0; }
.sidebar-section { background: var(--bg-card); border-radius: 8px; padding: 16px; margin-bottom: 16px; }
.sidebar-section h4 { margin: 0 0 12px 0; font-size: 13px; text-transform: uppercase; color: var(--text-secondary); letter-spacing: 0.5px; }
.detail-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--bg-secondary); font-size: 13px; }
.detail-row:last-child { border-bottom: none; }
.detail-row label { color: var(--text-secondary); font-size: 12px; }
.detail-row select, .detail-row input { max-width: 160px; font-size: 13px; }
.priority-badge { padding: 2px 8px; border-radius: 4px; font-size: 12px; }
.priority-badge.high { background: rgba(245,158,11,0.15); color: #f59e0b; }
.priority-badge.medium { background: rgba(59,130,246,0.15); color: #3b82f6; }
.priority-badge.low { background: rgba(107,114,128,0.15); color: #6b7280; }
.sprint-badge { padding: 2px 8px; border-radius: 4px; font-size: 12px; background: rgba(16,185,129,0.15); color: #10b981; }
.overdue { color: #ef4444; }
.labels-list { display: flex; flex-wrap: wrap; gap: 4px; }
.label-tag { padding: 2px 8px; border-radius: 4px; font-size: 11px; background: var(--accent); color: white; }
.btn-sm { padding: 6px 14px; font-size: 12px; border: none; border-radius: 6px; cursor: pointer; background: var(--bg-secondary); color: var(--text-primary); }
.btn-sm:hover { opacity: 0.9; }
.btn-sm.btn-primary { background: var(--accent); color: white; }
.btn-sm.btn-danger { background: #ef4444; color: white; }
/* Linked test cases */
.linked-cases-list { display: flex; flex-direction: column; gap: 6px; }
.linked-case-item {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 8px; background: var(--bg-secondary);
  border-radius: 6px; font-size: 12px;
  transition: background 0.15s;
}
.linked-case-item:hover { background: var(--bg-tertiary); }
.linked-case-id {
  font-family: monospace; font-size: 11px; color: var(--accent);
  background: var(--accent-muted); padding: 1px 5px; border-radius: 3px;
  flex-shrink: 0;
}
.linked-case-title {
  flex: 1; color: var(--text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.linked-case-status {
  font-size: 10px; font-weight: 600; padding: 1px 6px;
  border-radius: 4px; flex-shrink: 0; text-transform: capitalize;
}
.tc-status-draft    { background: rgba(107,114,128,0.15); color: #9ca3af; }
.tc-status-ready    { background: rgba(16,185,129,0.15); color: var(--success); }
.tc-status-approved { background: rgba(124,92,191,0.15); color: var(--accent); }
.empty-hint { font-size: 12px; color: var(--text-secondary); font-style: italic; }
@media (max-width: 768px) {
  .task-body { flex-direction: column; }
  .task-sidebar { width: 100%; }
}
</style>
