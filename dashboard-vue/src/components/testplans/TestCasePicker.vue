<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h3>Add Test Cases</h3>
        <button class="modal-close" @click="$emit('close')">&times;</button>
      </div>

      <div class="picker-filters">
        <input
          v-model="searchQuery"
          type="text"
          class="search-input"
          placeholder="Search by title..."
        />
        <select v-model="priorityFilter" class="filter-select">
          <option value="">All priorities</option>
          <option value="Critical">Critical</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
      </div>

      <div class="picker-list">
        <div v-if="loading" class="picker-loading">Loading...</div>
        <div v-else-if="filteredCases.length === 0" class="picker-empty">
          No test cases found
        </div>
        <label
          v-for="tc in filteredCases"
          :key="tc.id"
          class="picker-item"
          :class="{ disabled: existingIds.has(tc.id) }"
        >
          <input
            type="checkbox"
            :checked="selectedIds.has(tc.id) || existingIds.has(tc.id)"
            :disabled="existingIds.has(tc.id)"
            @change="toggleCase(tc.id)"
          />
          <span v-if="tc.human_id" class="human-id-badge">{{ tc.human_id }}</span>
          <span class="tc-title">{{ tc.title }}</span>
          <span class="tc-priority" :class="tc.priority?.toLowerCase()">{{ tc.priority }}</span>
        </label>
      </div>

      <div class="modal-footer">
        <button class="btn-cancel" @click="$emit('close')">Cancel</button>
        <button
          class="btn-add"
          :disabled="selectedIds.size === 0"
          @click="emitAdd"
        >
          Add selected ({{ selectedIds.size }})
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { testCasesApi } from '@/services/api'

const props = defineProps({
  existingIds: { type: Set, default: () => new Set() }
})

const emit = defineEmits(['add', 'close'])

const allCases = ref([])
const loading = ref(false)
const searchQuery = ref('')
const priorityFilter = ref('')
const selectedIds = ref(new Set())

let debounceTimer = null

async function loadCases() {
  loading.value = true
  try {
    const response = await testCasesApi.list({ limit: 500 })
    allCases.value = response.data.items || response.data || []
  } catch {
    allCases.value = []
  } finally {
    loading.value = false
  }
}

const filteredCases = computed(() => {
  let result = allCases.value
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(tc => tc.title?.toLowerCase().includes(q))
  }
  if (priorityFilter.value) {
    result = result.filter(tc => tc.priority === priorityFilter.value)
  }
  return result
})

function toggleCase(id) {
  const s = new Set(selectedIds.value)
  if (s.has(id)) {
    s.delete(id)
  } else {
    s.add(id)
  }
  selectedIds.value = s
}

function emitAdd() {
  emit('add', Array.from(selectedIds.value))
}

onMounted(() => {
  loadCases()
})

watch(searchQuery, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {}, 300)
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-card);
  border-radius: 12px;
  width: 600px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  margin: 0;
  color: var(--text-primary);
}

.modal-close {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 24px;
  cursor: pointer;
}

.picker-filters {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border-color);
}

.search-input {
  flex: 1;
  padding: 8px 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
}

.filter-select {
  padding: 8px 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
}

.picker-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 20px;
  max-height: 400px;
}

.picker-loading,
.picker-empty {
  padding: 24px;
  text-align: center;
  color: var(--text-secondary);
}

.picker-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  cursor: pointer;
  border-bottom: 1px solid var(--border-color);
}

.picker-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.picker-item input[type="checkbox"] {
  flex-shrink: 0;
}

.human-id-badge {
  flex-shrink: 0;
  padding: 2px 6px;
  background: rgba(99, 102, 241, 0.2);
  color: #818cf8;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.tc-title {
  flex: 1;
  color: var(--text-primary);
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tc-priority {
  flex-shrink: 0;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}
.tc-priority.critical { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
.tc-priority.high { background: rgba(249, 115, 22, 0.2); color: #f97316; }
.tc-priority.medium { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
.tc-priority.low { background: rgba(107, 114, 128, 0.2); color: #6b7280; }

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 20px;
  border-top: 1px solid var(--border-color);
}

.btn-cancel {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-secondary);
  cursor: pointer;
}

.btn-add {
  padding: 8px 16px;
  background: var(--accent);
  border: none;
  border-radius: 8px;
  color: white;
  cursor: pointer;
  font-weight: 600;
}

.btn-add:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
