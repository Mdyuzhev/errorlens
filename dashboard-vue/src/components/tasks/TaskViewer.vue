<template>
  <div class="task-viewer" @keydown.esc="$emit('close')">
    <!-- Header -->
    <div class="viewer-header">
      <button class="btn-back" @click="$emit('close')">← Назад</button>
      <span v-if="task.human_id" class="human-id-badge">{{ task.human_id }}</span>
      <span class="viewer-title">{{ task.title }}</span>
      <span v-if="task.type" class="type-badge" :style="{ background: task.type.color }">
        <AppIcon :name="task.type.icon" :size="12" />
        {{ task.type.name }}
      </span>
      <div style="position: relative;">
        <span
          class="status-badge"
          :class="task.status"
          :style="allowedTransitions.length ? 'cursor:pointer' : ''"
          :title="allowedTransitions.length ? 'Click to change status' : ''"
          @click="allowedTransitions.length && (showStatusDropdown = !showStatusDropdown)"
        >
          {{ task.task_status?.name || task.status }}
          <span v-if="allowedTransitions.length" style="font-size:10px;opacity:0.6"> &#9662;</span>
        </span>
        <div v-if="showStatusDropdown && allowedTransitions.length" class="status-dropdown">
          <button
            v-for="s in allowedTransitions" :key="s.id"
            class="status-option"
            :style="{ borderLeftColor: s.color }"
            @click="changeStatus(s)"
          >{{ s.name }}</button>
        </div>
      </div>
      <span class="priority-badge" :class="task.priority">{{ task.priority }}</span>
      <button class="btn btn-primary btn-sm" @click="$emit('edit')">Edit</button>
    </div>

    <!-- Body -->
    <div class="viewer-body">
      <!-- Left: Main content -->
      <div class="viewer-main">
        <!-- Description -->
        <section v-if="descriptionJson" class="doc-section">
          <h2 class="doc-section-title">Description</h2>
          <RichEditor :modelValue="descriptionJson" :editable="false" :showToolbar="false" />
        </section>
        <div v-else class="empty-hint">No description</div>

        <!-- Activity Feed -->
        <TaskActivityFeed
          :taskId="task.id"
          :activity="activity"
          @comment-added="loadActivity"
        />
      </div>

      <!-- Right: Sidebar -->
      <div class="viewer-sidebar">
        <!-- Details -->
        <div class="sidebar-section">
          <h4>Details</h4>
          <div class="detail-row">
            <label>Priority</label>
            <span class="priority-pill" :class="task.priority">{{ task.priority }}</span>
          </div>
          <div class="detail-row">
            <label>Severity</label>
            <span>{{ task.severity || '-' }}</span>
          </div>
          <div class="detail-row">
            <label>Environment</label>
            <span>{{ task.environment || '-' }}</span>
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
            <span>{{ task.assignee_user?.display_name || task.assignee_user?.username || task.assignee || '-' }}</span>
          </div>
          <div class="detail-row">
            <label>Due Date</label>
            <span :class="{ overdue: isOverdue }">{{ formatDate(task.due_date) || '-' }}</span>
          </div>
        </div>

        <!-- Time -->
        <div class="sidebar-section">
          <h4>Time</h4>
          <div class="detail-row">
            <label>Estimated</label>
            <span>{{ task.estimated_hours ? task.estimated_hours + 'h' : '-' }}</span>
          </div>
          <div class="detail-row">
            <label>Spent</label>
            <span>{{ task.spent_hours ? task.spent_hours + 'h' : '-' }}</span>
          </div>
        </div>

        <!-- Relations -->
        <div class="sidebar-section">
          <h4>Relations</h4>
          <div v-if="relations.length" class="relations-list">
            <div v-for="r in relations" :key="r.id" class="relation-item" @click="$emit('open-task', r.target_task_id)">
              <span class="relation-type">{{ formatRelationType(r.relation_type) }}</span>
              <span class="relation-target">
                <span v-if="r.target_task?.human_id" class="rel-id">{{ r.target_task.human_id }}</span>
                {{ r.target_task?.title || r.target_task_id }}
              </span>
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
        <div v-if="task.labels?.length" class="sidebar-section">
          <h4>Labels</h4>
          <div class="labels-list">
            <span v-for="l in task.labels" :key="l" class="label-tag">{{ l }}</span>
          </div>
        </div>

        <!-- Automation Runs -->
        <div v-if="automationRuns.length" class="sidebar-section">
          <h4>Automation</h4>
          <div v-for="run in automationRuns" :key="run.id" class="auto-run-item">
            <div class="auto-run-header">
              <span class="auto-run-name">{{ run.rule_name || 'Rule' }}</span>
              <span class="auto-run-status" :class="run.status">{{ run.status }}</span>
            </div>
            <div v-if="run.gitlab_pipeline_id" class="auto-run-pipeline">
              Pipeline #{{ run.gitlab_pipeline_id }}
              <span v-if="run.status === 'running'" class="auto-spinner"></span>
            </div>
            <div class="auto-run-time">{{ formatTimeAgo(run.started_at) }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useTasksStore } from '@/stores/tasks'
import { tasksApi, automationsApi } from '@/services/api'
import RichEditor from '@/components/common/RichEditor.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import TaskActivityFeed from './TaskActivityFeed.vue'

const props = defineProps({
  task: { type: Object, required: true },
  backlinks: { type: Array, default: () => [] },
})

const emit = defineEmits(['close', 'edit', 'open-task', 'updated'])

const store = useTasksStore()
const activity = ref([])
const relations = ref([])
const automationRuns = ref([])
const showStatusDropdown = ref(false)
const allowedTransitions = ref([])
let autoRunsPollTimer = null

function parseContent(raw) {
  if (!raw) return null
  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (parsed?.type === 'doc') return parsed
  } catch {}
  return null
}

const descriptionJson = computed(() => parseContent(props.task.description))

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

const FIELD_DISPLAY_NAMES = {
  assignee_id: 'Assignee', due_date: 'Due Date',
  estimated_hours: 'Estimated Hours', severity: 'Severity',
  environment: 'Environment', reporter_id: 'Reporter', labels: 'Labels',
}

async function changeStatus(s) {
  showStatusDropdown.value = false
  try {
    await tasksApi.moveStatus(props.task.id, s.id)
    emit('updated')
    await loadTransitions()
    await loadActivity()
  } catch (e) {
    const detail = e.response?.data?.detail
    if (detail?.error === 'missing_required_fields') {
      const fieldNames = detail.fields.map(f => FIELD_DISPLAY_NAMES[f] || f).join(', ')
      if (window.showToast) window.showToast(
        `Cannot change status: fill required fields first — ${fieldNames}`, 'error', 5000
      )
    } else {
      const msg = typeof detail === 'string' ? detail : 'Transition not allowed'
      if (window.showToast) window.showToast(msg, 'error')
    }
  }
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

async function loadAutomationRuns() {
  try {
    const res = await automationsApi.getTaskRuns(props.task.id)
    automationRuns.value = res.data
    // Poll if any are running
    if (res.data.some(r => r.status === 'running')) {
      if (!autoRunsPollTimer) {
        autoRunsPollTimer = setInterval(loadAutomationRuns, 10000)
      }
    } else if (autoRunsPollTimer) {
      clearInterval(autoRunsPollTimer)
      autoRunsPollTimer = null
    }
  } catch { automationRuns.value = [] }
}

function formatTimeAgo(iso) {
  if (!iso) return ''
  const diff = Math.floor((Date.now() - new Date(iso)) / 1000)
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

onMounted(() => {
  loadActivity()
  loadRelations()
  loadAutomationRuns()
  loadTransitions()
})

onUnmounted(() => {
  if (autoRunsPollTimer) clearInterval(autoRunsPollTimer)
})

watch(() => props.task.id, () => {
  loadActivity()
  loadRelations()
  loadAutomationRuns()
  loadTransitions()
})
</script>

<style scoped>
.task-viewer {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

.viewer-header {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 48px;
  padding: 0 16px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--bg-secondary);
  flex-shrink: 0;
}

.btn-back {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 14px;
  padding: 4px 8px;
  border-radius: 6px;
  white-space: nowrap;
}

.btn-back:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.viewer-title {
  flex: 1;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.human-id-badge {
  font-size: 11px;
  font-family: monospace;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  padding: 1px 6px;
  border-radius: 4px;
  flex-shrink: 0;
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
  flex-shrink: 0;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  background: var(--bg-secondary);
  flex-shrink: 0;
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

.priority-badge {
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  flex-shrink: 0;
}

.priority-badge.high { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
.priority-badge.medium { background: rgba(59, 130, 246, 0.2); color: #3b82f6; }
.priority-badge.low { background: rgba(107, 114, 128, 0.2); color: #9ca3af; }

.btn-sm {
  padding: 4px 12px !important;
  font-size: 13px !important;
}

.viewer-body {
  flex: 1;
  overflow-y: auto;
  display: flex;
  gap: 24px;
  padding: 24px;
}

.viewer-main {
  flex: 1;
  min-width: 0;
}

.doc-section {
  margin-bottom: 32px;
}

.doc-section-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--bg-secondary);
  color: var(--text-primary);
}

.viewer-sidebar {
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

.priority-pill {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.priority-pill.high { background: rgba(245,158,11,0.15); color: #f59e0b; }
.priority-pill.medium { background: rgba(59,130,246,0.15); color: #3b82f6; }
.priority-pill.low { background: rgba(107,114,128,0.15); color: #6b7280; }

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
  cursor: pointer;
}

.relation-item:hover { opacity: 0.8; }

.relation-type {
  font-size: 10px;
  text-transform: uppercase;
  color: var(--text-secondary);
  font-weight: 600;
  min-width: 70px;
}

.relation-target {
  flex: 1;
  color: var(--accent);
}

.rel-id {
  font-family: monospace;
  margin-right: 4px;
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
  font-size: 13px;
  color: var(--text-secondary);
  font-style: italic;
}

/* Automation runs */
.auto-run-item {
  padding: 8px 0;
  border-bottom: 1px solid var(--bg-secondary);
  font-size: 13px;
}
.auto-run-item:last-child { border-bottom: none; }

.auto-run-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.auto-run-name {
  font-weight: 500;
}

.auto-run-status {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 6px;
}
.auto-run-status.completed { background: rgba(76, 175, 80, 0.15); color: #4caf50; }
.auto-run-status.failed { background: rgba(229, 57, 53, 0.15); color: #e53935; }
.auto-run-status.running { background: rgba(33, 150, 243, 0.15); color: #2196f3; }
.auto-run-status.pending { background: var(--bg-secondary); color: var(--text-secondary); }

.auto-run-pipeline {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.auto-run-time {
  font-size: 11px;
  color: var(--text-secondary);
}

.auto-spinner {
  display: inline-block;
  width: 10px;
  height: 10px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  vertical-align: middle;
  margin-left: 4px;
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) {
  .viewer-body {
    flex-direction: column;
  }
  .viewer-sidebar {
    width: 100%;
  }
}
</style>
