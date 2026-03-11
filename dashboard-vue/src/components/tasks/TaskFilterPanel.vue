<template>
  <div class="filter-panel">
    <div class="filter-chips">
      <!-- Status -->
      <div class="filter-chip-wrapper" v-for="filter in filterDefs" :key="filter.key">
        <button
          class="filter-chip"
          :class="{ active: filterState[filter.key]?.length }"
          @click="toggleDropdown(filter.key)"
        >
          {{ filter.label }}
          <span v-if="filterState[filter.key]?.length" class="chip-badge">
            {{ filterState[filter.key].length }}
          </span>
          <span class="chip-arrow">&#9662;</span>
        </button>

        <div v-if="openDropdown === filter.key" class="filter-dropdown" @mousedown.prevent>
          <!-- Search input for assignee/label -->
          <input
            v-if="filter.searchable"
            v-model="searchQueries[filter.key]"
            class="filter-search"
            :placeholder="`Search ${filter.label.toLowerCase()}...`"
            @input="onSearchInput(filter.key)"
          />
          <div class="filter-options">
            <label
              v-for="opt in getOptions(filter.key)"
              :key="opt.value"
              class="filter-option"
            >
              <input
                type="checkbox"
                :checked="filterState[filter.key]?.includes(opt.value)"
                @change="toggleOption(filter.key, opt.value)"
              />
              <span>{{ opt.label }}</span>
            </label>
            <div v-if="!getOptions(filter.key).length" class="no-options">
              No options
            </div>
          </div>
        </div>
      </div>

      <!-- Due Date -->
      <div class="filter-chip-wrapper">
        <button
          class="filter-chip"
          :class="{ active: filterState.dueAfter || filterState.dueBefore }"
          @click="toggleDropdown('due')"
        >
          Due date
          <span v-if="filterState.dueAfter || filterState.dueBefore" class="chip-badge">1</span>
          <span class="chip-arrow">&#9662;</span>
        </button>

        <div v-if="openDropdown === 'due'" class="filter-dropdown date-dropdown" @mousedown.prevent>
          <div class="date-field">
            <label>From</label>
            <input type="date" v-model="filterState.dueAfter" @change="emitFilter" />
          </div>
          <div class="date-field">
            <label>To</label>
            <input type="date" v-model="filterState.dueBefore" @change="emitFilter" />
          </div>
        </div>
      </div>

      <!-- Clear button -->
      <button
        v-if="hasActiveFilters"
        class="filter-clear-btn"
        @click="clearFilters"
      >
        &times; Clear
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { tasksApi } from '@/services/api'

const props = defineProps({
  taskTypes: { type: Array, default: () => [] },
  projectId: { type: String, default: null },
})

const emit = defineEmits(['filter-change', 'clear'])

const filterState = ref({
  status: [],
  priority: [],
  type: [],
  severity: [],
  assignee: [],
  label: [],
  dueBefore: '',
  dueAfter: '',
})

const openDropdown = ref(null)
const searchQueries = ref({ assignee: '', label: '' })
const dynamicOptions = ref({ assignee: [], label: [] })
let searchTimer = null

const filterDefs = computed(() => [
  { key: 'status', label: 'Status', searchable: false },
  { key: 'priority', label: 'Priority', searchable: false },
  { key: 'type', label: 'Type', searchable: false },
  { key: 'severity', label: 'Severity', searchable: false },
  { key: 'assignee', label: 'Assignee', searchable: true },
  { key: 'label', label: 'Label', searchable: true },
])

const staticOptions = {
  status: [
    { value: 'todo', label: 'To Do' },
    { value: 'in_progress', label: 'In Progress' },
    { value: 'review', label: 'Review' },
    { value: 'done', label: 'Done' },
  ],
  priority: [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'critical', label: 'Critical' },
  ],
  severity: [
    { value: 'trivial', label: 'Trivial' },
    { value: 'minor', label: 'Minor' },
    { value: 'major', label: 'Major' },
    { value: 'critical', label: 'Critical' },
  ],
}

function getOptions(key) {
  if (key === 'type') {
    return props.taskTypes.map(t => ({ value: t.slug || t.name, label: t.name }))
  }
  if (key === 'assignee' || key === 'label') {
    return dynamicOptions.value[key]
  }
  return staticOptions[key] || []
}

function toggleDropdown(key) {
  if (openDropdown.value === key) {
    openDropdown.value = null
  } else {
    openDropdown.value = key
    if (key === 'assignee' || key === 'label') {
      fetchDynamicOptions(key, '')
    }
  }
}

function toggleOption(key, value) {
  const arr = filterState.value[key]
  const idx = arr.indexOf(value)
  if (idx >= 0) {
    arr.splice(idx, 1)
  } else {
    arr.push(value)
  }
  emitFilter()
}

function onSearchInput(key) {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    fetchDynamicOptions(key, searchQueries.value[key])
  }, 300)
}

async function fetchDynamicOptions(key, query) {
  try {
    const field = key === 'label' ? 'labels' : key
    const res = await tasksApi.jqlSuggest(field, query, props.projectId)
    dynamicOptions.value[key] = (res.data || []).map(s => ({
      value: s.value,
      label: s.label || s.value,
    }))
  } catch {
    dynamicOptions.value[key] = []
  }
}

const hasActiveFilters = computed(() => {
  const s = filterState.value
  return s.status.length || s.priority.length || s.type.length ||
    s.severity.length || s.assignee.length || s.label.length ||
    s.dueBefore || s.dueAfter
})

function buildJQL(state) {
  const parts = []
  for (const key of ['status', 'priority', 'type', 'severity', 'assignee', 'label']) {
    const values = state[key]
    if (!values.length) continue
    const field = key === 'label' ? 'labels' : key
    if (values.length === 1) {
      parts.push(`${field} = ${quoteValue(values[0])}`)
    } else {
      parts.push(`${field} in (${values.map(quoteValue).join(', ')})`)
    }
  }
  if (state.dueAfter) parts.push(`due >= "${state.dueAfter}"`)
  if (state.dueBefore) parts.push(`due <= "${state.dueBefore}"`)
  return parts.join(' AND ')
}

function quoteValue(v) {
  return v.includes(' ') ? `"${v}"` : v
}

function emitFilter() {
  const jql = buildJQL(filterState.value)
  emit('filter-change', { jql, filters: { ...filterState.value } })
}

function clearFilters() {
  filterState.value = {
    status: [], priority: [], type: [], severity: [],
    assignee: [], label: [], dueBefore: '', dueAfter: '',
  }
  openDropdown.value = null
  emit('clear')
}

// Close dropdown on outside click
function onDocClick(e) {
  if (!e.target.closest('.filter-chip-wrapper')) {
    openDropdown.value = null
  }
}

onMounted(() => document.addEventListener('click', onDocClick))
onUnmounted(() => document.removeEventListener('click', onDocClick))

defineExpose({ clearFilters })
</script>

<style scoped>
.filter-panel {
  margin-bottom: 12px;
}

.filter-chips {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.filter-chip-wrapper {
  position: relative;
}

.filter-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border: 1px solid var(--bg-secondary);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.filter-chip:hover {
  border-color: var(--accent);
  color: var(--text-primary);
}

.filter-chip.active {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(124, 58, 237, 0.1);
}

.chip-badge {
  background: var(--accent);
  color: white;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 10px;
}

.chip-arrow {
  font-size: 9px;
  opacity: 0.6;
}

.filter-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 180px;
  background: var(--bg-card);
  border: 1px solid var(--bg-secondary);
  border-radius: 8px;
  box-shadow: var(--shadow-dropdown);
  z-index: 200;
  padding: 4px 0;
}

.filter-search {
  width: calc(100% - 16px);
  margin: 4px 8px;
  padding: 5px 8px;
  border: 1px solid var(--bg-secondary);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 12px;
  outline: none;
}

.filter-search:focus {
  border-color: var(--accent);
}

.filter-options {
  max-height: 200px;
  overflow-y: auto;
}

.filter-option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  font-size: 13px;
  cursor: pointer;
  color: var(--text-primary);
  transition: background 0.1s;
}

.filter-option:hover {
  background: var(--bg-secondary);
}

.filter-option input[type="checkbox"] {
  width: 14px;
  height: 14px;
  accent-color: var(--accent);
  cursor: pointer;
}

.no-options {
  padding: 12px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 12px;
}

.date-dropdown {
  padding: 8px 12px;
  min-width: 200px;
}

.date-field {
  margin-bottom: 8px;
}

.date-field:last-child {
  margin-bottom: 0;
}

.date-field label {
  display: block;
  font-size: 11px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.date-field input[type="date"] {
  width: 100%;
  padding: 5px 8px;
  border: 1px solid var(--bg-secondary);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 12px;
  outline: none;
}

.date-field input[type="date"]:focus {
  border-color: var(--accent);
}

.filter-clear-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  padding: 5px 8px;
  border-radius: 6px;
  transition: all 0.2s;
}

.filter-clear-btn:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}
</style>
