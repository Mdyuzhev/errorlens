<template>
  <div class="endpoint-selector">
    <div class="selector-toolbar">
      <span class="selection-count">{{ selectedIds.length }} / {{ endpoints.length }} selected</span>
      <button class="btn-sm" @click="selectAll">All</button>
      <button class="btn-sm" @click="deselectAll">None</button>
    </div>

    <div v-if="loading" class="skeleton-list">
      <div v-for="i in 5" :key="i" class="skeleton-row" />
    </div>

    <div v-else class="groups">
      <div v-for="[tag, eps] in groupedByTag" :key="tag" class="tag-group">
        <div class="tag-header" @click="toggleGroup(tag)">
          <span class="tag-arrow">{{ expandedTags.has(tag) ? '\u25BC' : '\u25B6' }}</span>
          <span class="tag-name">{{ tag }}</span>
          <span class="tag-count">{{ eps.length }}</span>
          <input
            type="checkbox"
            :checked="isGroupSelected(tag)"
            @click.stop="toggleGroupSelect(tag)"
          />
        </div>

        <div v-if="expandedTags.has(tag)" class="tag-endpoints">
          <label v-for="ep in eps" :key="ep.id" class="endpoint-row">
            <input type="checkbox" :value="ep.id" v-model="selectedIds" />
            <span class="method-badge" :class="'method-' + ep.method.toLowerCase()">
              {{ ep.method }}
            </span>
            <span class="ep-path">{{ ep.path }}</span>
            <span v-if="ep.summary" class="ep-summary">{{ ep.summary }}</span>
          </label>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'

const props = defineProps({
  endpoints: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['selection-changed'])

const selectedIds = ref([])
const expandedTags = ref(new Set())

const groupedByTag = computed(() => {
  const map = new Map()
  for (const ep of props.endpoints) {
    const tag = ep.tags?.[0] || 'Other'
    if (!map.has(tag)) map.set(tag, [])
    map.get(tag).push(ep)
  }
  return map
})

onMounted(() => {
  // Expand all groups and select all endpoints
  selectAll()
  for (const [tag] of groupedByTag.value) {
    expandedTags.value.add(tag)
  }
})

watch(selectedIds, (val) => {
  emit('selection-changed', [...val])
}, { deep: true })

watch(() => props.endpoints, (eps) => {
  if (eps.length > 0) {
    selectedIds.value = eps.map(e => e.id)
    expandedTags.value = new Set(groupedByTag.value.keys())
  }
})

function selectAll() {
  selectedIds.value = props.endpoints.map(e => e.id)
}

function deselectAll() {
  selectedIds.value = []
}

function toggleGroup(tag) {
  if (expandedTags.value.has(tag)) {
    expandedTags.value.delete(tag)
  } else {
    expandedTags.value.add(tag)
  }
  // Force reactivity
  expandedTags.value = new Set(expandedTags.value)
}

function isGroupSelected(tag) {
  const eps = groupedByTag.value.get(tag) || []
  return eps.every(ep => selectedIds.value.includes(ep.id))
}

function toggleGroupSelect(tag) {
  const eps = groupedByTag.value.get(tag) || []
  const allSelected = isGroupSelected(tag)
  if (allSelected) {
    const idsToRemove = new Set(eps.map(e => e.id))
    selectedIds.value = selectedIds.value.filter(id => !idsToRemove.has(id))
  } else {
    const currentSet = new Set(selectedIds.value)
    for (const ep of eps) currentSet.add(ep.id)
    selectedIds.value = [...currentSet]
  }
}
</script>

<style scoped>
.endpoint-selector {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.selector-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

.selection-count {
  flex: 1;
}

.btn-sm {
  padding: 3px 10px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
}
.btn-sm:hover {
  color: var(--text-primary);
}

.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-row {
  height: 32px;
  background: var(--bg-tertiary);
  border-radius: 6px;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}

.tag-group {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.tag-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-secondary);
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.tag-arrow {
  font-size: 10px;
  width: 14px;
  color: var(--text-secondary);
}

.tag-name {
  flex: 1;
}

.tag-count {
  font-size: 11px;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  padding: 1px 6px;
  border-radius: 10px;
}

.tag-endpoints {
  display: flex;
  flex-direction: column;
}

.endpoint-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px 6px 34px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.1s;
}
.endpoint-row:hover {
  background: var(--bg-tertiary);
}

.method-badge {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  min-width: 50px;
  text-align: center;
}

.method-get {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}
.method-post {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}
.method-put {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}
.method-patch {
  background: rgba(168, 85, 247, 0.15);
  color: #a855f7;
}
.method-delete {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.ep-path {
  color: var(--text-primary);
  font-family: monospace;
}

.ep-summary {
  color: var(--text-secondary);
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
