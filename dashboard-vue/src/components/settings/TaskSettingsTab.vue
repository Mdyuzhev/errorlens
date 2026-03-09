<template>
  <div class="task-settings">
    <!-- Project selector -->
    <div class="section-header">
      <h2>Task Workflow Settings</h2>
      <select v-model="selectedProjectId" class="project-select" @change="loadTypes">
        <option value="">Select project...</option>
        <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
    </div>

    <div v-if="!selectedProjectId" class="empty-state">
      Select a project to configure task workflow
    </div>

    <template v-if="selectedProjectId">
      <!-- Task Types -->
      <div class="settings-section">
        <div class="section-title">
          <h3>Task Types</h3>
          <button class="btn btn-sm" @click="showAddType = true">+ Add Type</button>
        </div>

        <div class="types-grid">
          <div v-for="t in types" :key="t.id" class="type-card" :style="{ borderLeftColor: t.color }">
            <div class="type-header">
              <AppIcon :name="t.icon" :size="16" />
              <span class="type-name">{{ t.name }}</span>
              <span class="type-slug">{{ t.slug }}</span>
            </div>
            <div class="type-actions">
              <label class="toggle-sm">
                <input type="checkbox" :checked="t.is_active" @change="toggleTypeActive(t)" />
                <span>{{ t.is_active ? 'Active' : 'Inactive' }}</span>
              </label>
            </div>
            <div v-if="t.statuses?.length" class="status-pills">
              <span
                v-for="s in t.statuses"
                :key="s.id"
                class="status-pill"
                :style="{ background: s.color }"
                :class="{ initial: s.is_initial, final: s.is_final }"
              >
                {{ s.name }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Workflows -->
      <div class="settings-section">
        <div class="section-title">
          <h3>Workflows</h3>
        </div>

        <div class="workflow-select">
          <select v-model="selectedTypeId" @change="loadWorkflow">
            <option value="">Select type...</option>
            <option v-for="t in types" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
        </div>

        <div v-if="selectedTypeId && workflowStatuses.length" class="workflow-view">
          <div v-for="s in workflowStatuses" :key="s.id" class="workflow-status">
            <div class="status-header">
              <span class="status-badge" :style="{ background: s.color }">{{ s.name }}</span>
              <span v-if="s.is_initial" class="flag">initial</span>
              <span v-if="s.is_final" class="flag">final</span>
            </div>
            <div class="transitions-list">
              <span class="arrow-label">can transition to:</span>
              <span
                v-for="tid in getTransitionsFrom(s.id)"
                :key="tid"
                class="transition-target"
                :style="{ background: getStatusById(tid)?.color || '#666' }"
              >
                {{ getStatusById(tid)?.name || '?' }}
              </span>
              <span v-if="!getTransitionsFrom(s.id).length" class="no-transitions">none</span>
            </div>
          </div>

          <div class="workflow-actions">
            <button class="btn btn-sm" @click="showAddStatus = true">+ Add Status</button>
            <button class="btn btn-sm" @click="showAddTransition = true">+ Add Transition</button>
          </div>
        </div>
      </div>

      <!-- Fields info -->
      <div class="settings-section">
        <div class="section-title">
          <h3>Fields</h3>
        </div>
        <div class="fields-info">
          <p>Standard fields for all task types:</p>
          <div class="field-list">
            <span class="field-tag">Title</span>
            <span class="field-tag">Description</span>
            <span class="field-tag">Priority</span>
            <span class="field-tag">Severity</span>
            <span class="field-tag">Environment</span>
            <span class="field-tag">Assignee</span>
            <span class="field-tag">Due Date</span>
            <span class="field-tag">Labels</span>
            <span class="field-tag">Estimated Hours</span>
            <span class="field-tag">Spent Hours</span>
          </div>
          <p class="hint">Custom fields configuration coming in a future update.</p>
        </div>
      </div>
    </template>

    <!-- Add Type Modal -->
    <div v-if="showAddType" class="modal-overlay" @click.self="showAddType = false">
      <div class="modal-sm">
        <h3>Add Task Type</h3>
        <div class="form-group">
          <label>Name</label>
          <input v-model="newType.name" placeholder="e.g. Bug" />
        </div>
        <div class="form-group">
          <label>Slug</label>
          <input v-model="newType.slug" placeholder="e.g. bug" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Icon</label>
            <input v-model="newType.icon" placeholder="alert" />
          </div>
          <div class="form-group">
            <label>Color</label>
            <input v-model="newType.color" type="color" />
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showAddType = false">Cancel</button>
          <button class="btn btn-primary" @click="addType">Create</button>
        </div>
      </div>
    </div>

    <!-- Add Status Modal -->
    <div v-if="showAddStatus" class="modal-overlay" @click.self="showAddStatus = false">
      <div class="modal-sm">
        <h3>Add Status</h3>
        <div class="form-group">
          <label>Name</label>
          <input v-model="newStatus.name" placeholder="e.g. Testing" />
        </div>
        <div class="form-group">
          <label>Slug</label>
          <input v-model="newStatus.slug" placeholder="e.g. testing" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Color</label>
            <input v-model="newStatus.color" type="color" />
          </div>
          <div class="form-group">
            <label>Flags</label>
            <label class="checkbox-label"><input type="checkbox" v-model="newStatus.is_initial" /> Initial</label>
            <label class="checkbox-label"><input type="checkbox" v-model="newStatus.is_final" /> Final</label>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showAddStatus = false">Cancel</button>
          <button class="btn btn-primary" @click="addStatus">Create</button>
        </div>
      </div>
    </div>

    <!-- Add Transition Modal -->
    <div v-if="showAddTransition" class="modal-overlay" @click.self="showAddTransition = false">
      <div class="modal-sm">
        <h3>Add Transition</h3>
        <div class="form-group">
          <label>From Status</label>
          <select v-model="newTransition.from_status_id">
            <option value="">Select...</option>
            <option v-for="s in workflowStatuses" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>
        <div class="form-group">
          <label>To Status</label>
          <select v-model="newTransition.to_status_id">
            <option value="">Select...</option>
            <option v-for="s in workflowStatuses" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="showAddTransition = false">Cancel</button>
          <button class="btn btn-primary" @click="addTransition">Create</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { projectsApi, taskSettingsApi } from '@/services/api'
import AppIcon from '@/components/common/AppIcon.vue'

const projects = ref([])
const selectedProjectId = ref('')
const types = ref([])
const selectedTypeId = ref('')
const workflowStatuses = ref([])
const workflowTransitions = ref([])

const showAddType = ref(false)
const showAddStatus = ref(false)
const showAddTransition = ref(false)

const newType = ref({ name: '', slug: '', icon: 'check-square', color: '#3b82f6' })
const newStatus = ref({ name: '', slug: '', color: '#6b7280', is_initial: false, is_final: false })
const newTransition = ref({ from_status_id: '', to_status_id: '' })

onMounted(async () => {
  try {
    const res = await projectsApi.list()
    projects.value = res.data.items || res.data
  } catch {}
})

async function loadTypes() {
  if (!selectedProjectId.value) { types.value = []; return }
  try {
    const res = await taskSettingsApi.getTypes(selectedProjectId.value)
    types.value = res.data
  } catch { types.value = [] }
  selectedTypeId.value = ''
  workflowStatuses.value = []
  workflowTransitions.value = []
}

async function loadWorkflow() {
  if (!selectedTypeId.value) return
  try {
    const [statusRes, transRes] = await Promise.all([
      taskSettingsApi.getStatuses(selectedTypeId.value, selectedProjectId.value),
      taskSettingsApi.getTransitions(selectedTypeId.value, selectedProjectId.value),
    ])
    workflowStatuses.value = statusRes.data
    workflowTransitions.value = transRes.data
  } catch {}
}

function getTransitionsFrom(statusId) {
  return workflowTransitions.value
    .filter(t => t.from_status_id === statusId)
    .map(t => t.to_status_id)
}

function getStatusById(id) {
  return workflowStatuses.value.find(s => s.id === id)
}

async function toggleTypeActive(t) {
  try {
    await taskSettingsApi.updateType(t.id, { is_active: !t.is_active })
    t.is_active = !t.is_active
  } catch {}
}

async function addType() {
  try {
    await taskSettingsApi.createType(selectedProjectId.value, newType.value)
    showAddType.value = false
    newType.value = { name: '', slug: '', icon: 'check-square', color: '#3b82f6' }
    await loadTypes()
  } catch {}
}

async function addStatus() {
  try {
    await taskSettingsApi.createStatus(selectedTypeId.value, selectedProjectId.value, newStatus.value)
    showAddStatus.value = false
    newStatus.value = { name: '', slug: '', color: '#6b7280', is_initial: false, is_final: false }
    await loadWorkflow()
    await loadTypes()
  } catch {}
}

async function addTransition() {
  try {
    await taskSettingsApi.createTransition(selectedTypeId.value, selectedProjectId.value, newTransition.value)
    showAddTransition.value = false
    newTransition.value = { from_status_id: '', to_status_id: '' }
    await loadWorkflow()
  } catch {}
}
</script>

<style scoped>
.task-settings {
  max-width: 900px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.section-header h2 {
  margin: 0;
}

.project-select {
  min-width: 200px;
}

.empty-state {
  padding: 40px;
  text-align: center;
  color: var(--text-secondary);
}

.settings-section {
  margin-bottom: 32px;
}

.section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title h3 {
  margin: 0;
  font-size: 16px;
}

.types-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.type-card {
  background: var(--bg-card);
  border-radius: 8px;
  padding: 16px;
  border-left: 4px solid;
}

.type-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.type-name {
  font-weight: 600;
}

.type-slug {
  font-size: 12px;
  color: var(--text-secondary);
  font-family: monospace;
}

.type-actions {
  margin-bottom: 8px;
}

.toggle-sm {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
}

.status-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.status-pill {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  color: white;
  font-weight: 500;
}

.status-pill.initial { box-shadow: 0 0 0 2px rgba(255,255,255,0.5); }
.status-pill.final { opacity: 0.8; }

.workflow-select {
  margin-bottom: 16px;
}

.workflow-view {
  background: var(--bg-card);
  border-radius: 8px;
  padding: 16px;
}

.workflow-status {
  padding: 12px 0;
  border-bottom: 1px solid var(--bg-secondary);
}

.workflow-status:last-of-type {
  border-bottom: none;
}

.status-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.status-badge {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 13px;
  color: white;
  font-weight: 500;
}

.flag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.transitions-list {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  padding-left: 12px;
}

.arrow-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.transition-target {
  padding: 1px 6px;
  border-radius: 8px;
  font-size: 11px;
  color: white;
}

.no-transitions {
  font-size: 12px;
  color: var(--text-secondary);
  font-style: italic;
}

.workflow-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--bg-secondary);
}

.fields-info {
  background: var(--bg-card);
  border-radius: 8px;
  padding: 16px;
}

.fields-info p {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: var(--text-secondary);
}

.field-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.field-tag {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.hint {
  font-size: 12px;
  color: var(--text-secondary);
  font-style: italic;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.btn-sm:hover { opacity: 0.9; }

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
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

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  cursor: pointer;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}
</style>
