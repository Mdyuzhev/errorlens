<template>
  <div v-if="filters.length" class="saved-filters">
    <div class="filters-header">
      <span class="filters-title">Saved Filters</span>
    </div>

    <div v-if="myFilters.length" class="filter-group">
      <span class="group-label">My Filters</span>
      <div
        v-for="f in myFilters"
        :key="f.id"
        class="filter-item"
        :class="{ active: f.jql === activeJQL }"
        @click="$emit('apply', f.jql)"
      >
        <span class="filter-name">{{ f.name }}</span>
        <div class="filter-actions">
          <button
            class="filter-action-btn"
            :title="f.is_shared ? 'Shared' : 'Private'"
            @click.stop="toggleShare(f)"
          >
            {{ f.is_shared ? '🌐' : '🔒' }}
          </button>
          <button class="filter-action-btn delete" title="Delete" @click.stop="onDelete(f)">
            &times;
          </button>
        </div>
      </div>
    </div>

    <div v-if="sharedFilters.length" class="filter-group">
      <span class="group-label">Shared</span>
      <div
        v-for="f in sharedFilters"
        :key="f.id"
        class="filter-item"
        :class="{ active: f.jql === activeJQL }"
        @click="$emit('apply', f.jql)"
      >
        <span class="filter-name">{{ f.name }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useJqlStore } from '@/stores/jql'

const props = defineProps({
  projectId: { type: String, default: null },
  activeJQL: { type: String, default: '' },
})

defineEmits(['apply'])

const jqlStore = useJqlStore()

const filters = computed(() => jqlStore.savedFilters)
const myFilters = computed(() => filters.value.filter(f => f.is_own))
const sharedFilters = computed(() => filters.value.filter(f => !f.is_own && f.is_shared))

async function toggleShare(f) {
  const { savedFiltersApi } = await import('@/services/api')
  await savedFiltersApi.update(f.id, { is_shared: !f.is_shared })
  await jqlStore.fetchSavedFilters(props.projectId)
}

async function onDelete(f) {
  await jqlStore.deleteFilter(f.id, props.projectId)
}
</script>

<style scoped>
.saved-filters {
  margin-bottom: 12px;
}

.filters-header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.filters-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.filter-group {
  margin-bottom: 8px;
}

.group-label {
  font-size: 11px;
  color: var(--text-secondary);
  opacity: 0.7;
  display: block;
  margin-bottom: 4px;
}

.filter-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.15s;
}

.filter-item:hover { background: var(--bg-secondary); }
.filter-item.active { background: var(--accent); color: white; }

.filter-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.filter-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.15s;
}

.filter-item:hover .filter-actions { opacity: 1; }

.filter-action-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  padding: 2px 4px;
  border-radius: 4px;
  color: var(--text-secondary);
}

.filter-action-btn:hover { background: rgba(255,255,255,0.1); }
.filter-action-btn.delete:hover { color: #ef4444; }
</style>
