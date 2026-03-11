<template>
  <div class="workflow-editor">
    <!-- Validation warnings -->
    <div v-if="validationWarnings.length" class="validation-warnings">
      <div v-for="(w, i) in validationWarnings" :key="i" class="warning-item">⚠ {{ w }}</div>
    </div>

    <!-- Section 1: Status cards -->
    <div class="section-label">Statuses</div>
    <div class="status-cards">
      <div
        v-for="s in statuses"
        :key="s.id"
        class="status-card"
        :style="{ borderTopColor: s.color }"
      >
        <div class="status-card-row">
          <input
            type="color"
            :value="s.color"
            class="color-picker"
            @input="updateStatus(s, { color: $event.target.value })"
          />
          <input
            type="text"
            :value="s.name"
            class="status-name-input"
            @blur="updateStatus(s, { name: $event.target.value })"
            @keydown.enter="$event.target.blur()"
          />
          <button
            class="btn-delete-status"
            title="Delete status"
            @click="deleteStatus(s)"
          >×</button>
        </div>
        <div class="status-card-flags">
          <label class="flag-label">
            <input
              type="checkbox"
              :checked="s.is_initial"
              @change="setInitial(s)"
            /> Initial
          </label>
          <label class="flag-label">
            <input
              type="checkbox"
              :checked="s.is_final"
              @change="updateStatus(s, { is_final: !s.is_final })"
            /> Final
          </label>
        </div>
      </div>

      <!-- Add Status inline form -->
      <div v-if="showAddStatus" class="status-card add-status-form">
        <input v-model="newStatus.name" placeholder="Name" class="status-name-input" @input="autoSlug" />
        <input v-model="newStatus.slug" placeholder="Slug" class="status-slug-input" />
        <div class="add-status-row">
          <input type="color" v-model="newStatus.color" class="color-picker" />
          <label class="flag-label"><input type="checkbox" v-model="newStatus.is_initial" /> Initial</label>
          <label class="flag-label"><input type="checkbox" v-model="newStatus.is_final" /> Final</label>
        </div>
        <div class="add-status-actions">
          <button class="btn-save" @click="addStatus">Save</button>
          <button class="btn-cancel" @click="showAddStatus = false">Cancel</button>
        </div>
      </div>
      <button v-else class="btn-add-status" @click="showAddStatus = true">+ Add Status</button>
    </div>

    <!-- Section 2: Transition Matrix -->
    <div class="section-label">Transition Matrix</div>
    <div class="matrix-wrapper" v-if="statuses.length">
      <table class="transition-matrix">
        <thead>
          <tr>
            <th class="matrix-corner">From ↓ \ To →</th>
            <th v-for="s in statuses" :key="s.id" class="matrix-col-header">
              <span class="matrix-badge" :style="{ background: s.color }">{{ s.name }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="from in statuses" :key="from.id">
            <td class="matrix-row-header">
              <span class="matrix-badge" :style="{ background: from.color }">{{ from.name }}</span>
            </td>
            <td
              v-for="to in statuses"
              :key="to.id"
              class="matrix-cell"
              :class="{
                'cell-diagonal': from.id === to.id,
                'cell-active': matrix[`${from.id}::${to.id}`],
                'cell-has-conditions': matrix[`${from.id}::${to.id}`]?.required_fields?.length > 0,
              }"
              @click="handleCellClick(from, to, $event)"
            >
              <template v-if="from.id === to.id">—</template>
              <template v-else-if="matrix[`${from.id}::${to.id}`]">
                <span class="cell-check">✓</span>
                <span v-if="matrix[`${from.id}::${to.id}`]?.required_fields?.length" class="cell-gear">⚙</span>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Transition Popover -->
    <TransitionPopover
      v-if="activePopover"
      :transition="activePopover.transition"
      :from-status="activePopover.from"
      :to-status="activePopover.to"
      :anchor-rect="activePopover.rect"
      @update="onPopoverUpdate"
      @remove="onPopoverRemove"
      @close="activePopover = null"
    />

    <div v-if="saving" class="saving-indicator">Saving...</div>
    <div v-if="error" class="error-toast" @click="error = ''">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { taskSettingsApi } from '../../services/api.js'
import TransitionPopover from './TransitionPopover.vue'

const props = defineProps({
  typeId: { type: String, required: true },
  projectId: { type: String, required: true },
  typeName: { type: String, default: '' },
})

const emit = defineEmits(['updated'])

const statuses = ref([])
const transitions = ref([])
const saving = ref(false)
const error = ref('')
const showAddStatus = ref(false)
const newStatus = ref({ name: '', slug: '', color: '#6b7280', is_initial: false, is_final: false })
const activePopover = ref(null)

// ---- Data loading ----
async function loadData() {
  try {
    const [statusRes, transRes] = await Promise.all([
      taskSettingsApi.getStatuses(props.typeId, props.projectId),
      taskSettingsApi.getTransitions(props.typeId, props.projectId),
    ])
    statuses.value = statusRes.data
    transitions.value = transRes.data
  } catch (e) {
    error.value = 'Failed to load workflow data'
  }
}

onMounted(loadData)
watch(() => props.typeId, loadData)

// ---- Matrix computed ----
const matrix = computed(() => {
  const m = {}
  for (const t of transitions.value) {
    m[`${t.from_status_id}::${t.to_status_id}`] = t
  }
  return m
})

// ---- Validation warnings ----
const validationWarnings = computed(() => {
  const warnings = []
  const hasInitial = statuses.value.some(s => s.is_initial)
  if (!hasInitial && statuses.value.length > 0) {
    warnings.push("No initial status — tasks won't get a default status on creation")
  }
  for (const s of statuses.value) {
    if (s.is_final) continue
    const hasOutgoing = transitions.value.some(t => t.from_status_id === s.id)
    if (!hasOutgoing) {
      warnings.push(`Status '${s.name}' is a dead end — tasks will be stuck here`)
    }
  }
  return warnings
})

// ---- Status actions ----
function autoSlug() {
  newStatus.value.slug = newStatus.value.name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '')
}

async function addStatus() {
  if (!newStatus.value.name || !newStatus.value.slug) return
  saving.value = true
  try {
    await taskSettingsApi.createStatus(props.typeId, props.projectId, {
      ...newStatus.value,
      sort_order: statuses.value.length,
    })
    showAddStatus.value = false
    newStatus.value = { name: '', slug: '', color: '#6b7280', is_initial: false, is_final: false }
    await loadData()
    emit('updated')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to create status'
  } finally {
    saving.value = false
  }
}

async function updateStatus(s, updates) {
  saving.value = true
  try {
    await taskSettingsApi.updateStatus(s.id, updates)
    await loadData()
    emit('updated')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to update status'
  } finally {
    saving.value = false
  }
}

async function setInitial(s) {
  // Unset previous initial
  const prev = statuses.value.find(st => st.is_initial && st.id !== s.id)
  if (prev) {
    await taskSettingsApi.updateStatus(prev.id, { is_initial: false })
  }
  await updateStatus(s, { is_initial: !s.is_initial })
}

async function deleteStatus(s) {
  if (!confirm(`Delete status "${s.name}"?`)) return
  saving.value = true
  try {
    await taskSettingsApi.deleteStatus(s.id)
    await loadData()
    emit('updated')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Cannot delete status'
  } finally {
    saving.value = false
  }
}

// ---- Matrix actions ----
async function handleCellClick(from, to, event) {
  if (from.id === to.id) return
  const key = `${from.id}::${to.id}`
  const existing = matrix.value[key]

  if (existing) {
    // Open popover
    const rect = event.target.closest('td').getBoundingClientRect()
    activePopover.value = {
      transition: existing,
      from,
      to,
      rect,
    }
  } else {
    // Create transition
    saving.value = true
    try {
      await taskSettingsApi.createTransition(props.typeId, props.projectId, {
        from_status_id: from.id,
        to_status_id: to.id,
      })
      await loadData()
    } catch (e) {
      error.value = e.response?.data?.detail || 'Failed to create transition'
    } finally {
      saving.value = false
    }
  }
}

async function onPopoverUpdate(requiredFields) {
  if (!activePopover.value) return
  saving.value = true
  try {
    await taskSettingsApi.updateTransition(activePopover.value.transition.id, {
      required_fields: requiredFields,
    })
    await loadData()
    // Keep popover open with refreshed data
    const key = `${activePopover.value.from.id}::${activePopover.value.to.id}`
    if (matrix.value[key]) {
      activePopover.value.transition = matrix.value[key]
    }
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to update transition'
  } finally {
    saving.value = false
  }
}

async function onPopoverRemove() {
  if (!activePopover.value) return
  saving.value = true
  try {
    await taskSettingsApi.deleteTransition(props.typeId, {
      from_status_id: activePopover.value.from.id,
      to_status_id: activePopover.value.to.id,
    })
    activePopover.value = null
    await loadData()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to delete transition'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.workflow-editor { position: relative; }

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 16px 0 8px;
}

/* Validation warnings */
.validation-warnings {
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 6px;
  padding: 8px 12px;
  margin-bottom: 12px;
}
.warning-item {
  font-size: 12px;
  color: #f59e0b;
  padding: 2px 0;
}

/* Status cards */
.status-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 20px;
}
.status-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-top: 3px solid var(--border-color);
  border-radius: 6px;
  padding: 8px 10px;
  min-width: 160px;
}
.status-card-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.color-picker {
  width: 24px;
  height: 24px;
  border: none;
  padding: 0;
  cursor: pointer;
  background: none;
  border-radius: 4px;
}
.status-name-input {
  flex: 1;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 4px 6px;
  font-size: 13px;
  color: var(--text-primary);
  min-width: 80px;
}
.status-slug-input {
  width: 100%;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 4px 6px;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}
.btn-delete-status {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}
.btn-delete-status:hover { color: #ef4444; }

.status-card-flags {
  display: flex;
  gap: 10px;
}
.flag-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--text-secondary);
  cursor: pointer;
}
.flag-label input { accent-color: var(--accent); }

/* Add status */
.add-status-form {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.add-status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 4px 0;
}
.add-status-actions {
  display: flex;
  gap: 6px;
  margin-top: 4px;
}
.btn-save {
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 4px 12px;
  font-size: 12px;
  cursor: pointer;
}
.btn-cancel {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: none;
  border-radius: 4px;
  padding: 4px 12px;
  font-size: 12px;
  cursor: pointer;
}
.btn-add-status {
  background: none;
  border: 1px dashed var(--border-color);
  border-radius: 6px;
  padding: 8px 16px;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  min-width: 120px;
  transition: all 0.2s;
}
.btn-add-status:hover {
  border-color: var(--accent);
  color: var(--accent);
}

/* Transition Matrix */
.matrix-wrapper {
  overflow-x: auto;
  margin-bottom: 16px;
}
.transition-matrix {
  border-collapse: collapse;
  font-size: 12px;
}
.transition-matrix th,
.transition-matrix td {
  border: 1px solid var(--border-color);
  text-align: center;
  vertical-align: middle;
}
.matrix-corner {
  background: var(--bg-secondary);
  padding: 6px 10px;
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 500;
  white-space: nowrap;
}
.matrix-col-header,
.matrix-row-header {
  background: var(--bg-secondary);
  padding: 4px 6px;
  white-space: nowrap;
}
.matrix-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  color: #fff;
  font-size: 11px;
  font-weight: 500;
}
.matrix-cell {
  width: 36px;
  height: 36px;
  min-width: 36px;
  cursor: pointer;
  transition: background 0.15s;
  position: relative;
}
.matrix-cell:hover:not(.cell-diagonal) {
  background: var(--bg-tertiary);
}
.cell-diagonal {
  background: var(--bg-secondary);
  cursor: not-allowed;
  color: var(--text-secondary);
  font-size: 10px;
}
.cell-active {
  background: rgba(16, 185, 129, 0.1);
}
.cell-check {
  color: #10b981;
  font-size: 14px;
  font-weight: 700;
}
.cell-gear {
  color: var(--text-secondary);
  font-size: 10px;
  position: absolute;
  top: 2px;
  right: 3px;
}

/* Saving indicator */
.saving-indicator {
  position: fixed;
  bottom: 16px;
  right: 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 12px;
  color: var(--text-secondary);
  z-index: 50;
}
.error-toast {
  position: fixed;
  bottom: 16px;
  right: 16px;
  background: #ef4444;
  color: #fff;
  border-radius: 6px;
  padding: 8px 14px;
  font-size: 13px;
  cursor: pointer;
  z-index: 50;
}
</style>
