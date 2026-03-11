<template>
  <div class="project-selector">
    <div class="selector-input" @click="toggleDropdown">
      <span v-if="selected" class="selected-name">{{ selected.name }}</span>
      <span v-else class="placeholder">Select GitLab project...</span>
      <span class="arrow">&#9662;</span>
    </div>

    <div v-if="open" class="dropdown">
      <input
        v-model="search"
        class="search-input"
        placeholder="Search projects..."
        @click.stop
        ref="searchRef"
      />
      <div class="dropdown-list">
        <div v-if="loading" class="dropdown-item loading">Loading...</div>
        <div
          v-for="p in filtered"
          :key="p.id"
          class="dropdown-item"
          :class="{ active: p.id === modelValue }"
          @click="selectProject(p)"
        >
          <span class="proj-name">{{ p.name }}</span>
          <span class="proj-path">{{ p.path_with_namespace }}</span>
        </div>
        <div v-if="!loading && !filtered.length" class="dropdown-item empty">
          No projects found
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useGitLabStore } from '@/stores/gitlab'

const props = defineProps({
  connectionId: { type: String, required: true },
  modelValue: { type: Number, default: null },
})

const emit = defineEmits(['update:modelValue', 'select'])

const store = useGitLabStore()
const open = ref(false)
const search = ref('')
const loading = ref(false)
const searchRef = ref(null)

const projects = computed(() => store.projects.get(props.connectionId) || [])
const selected = computed(() => projects.value.find(p => p.id === props.modelValue))

const filtered = computed(() => {
  const q = search.value.toLowerCase()
  if (!q) return projects.value
  return projects.value.filter(
    p => p.name.toLowerCase().includes(q) || p.path_with_namespace.toLowerCase().includes(q)
  )
})

async function loadProjects() {
  if (!store.projects.has(props.connectionId)) {
    loading.value = true
    try {
      await store.fetchProjects(props.connectionId)
    } finally {
      loading.value = false
    }
  }
}

function toggleDropdown() {
  open.value = !open.value
  if (open.value) {
    loadProjects()
    nextTick(() => searchRef.value?.focus())
  }
}

function selectProject(p) {
  emit('update:modelValue', p.id)
  emit('select', p)
  open.value = false
  search.value = ''
}

// Close on outside click
onMounted(() => {
  document.addEventListener('click', () => { open.value = false })
})

watch(() => props.connectionId, () => {
  search.value = ''
})
</script>

<style scoped>
.project-selector {
  position: relative;
  width: 100%;
}

.selector-input {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-secondary);
  cursor: pointer;
  font-size: 14px;
  color: var(--text-primary);
}

.placeholder {
  color: var(--text-secondary);
  opacity: 0.6;
}

.arrow {
  font-size: 10px;
  color: var(--text-secondary);
}

.dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 4px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  z-index: 100;
  max-height: 300px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-dropdown);
}

.search-input {
  padding: 10px 12px;
  border: none;
  border-bottom: 1px solid var(--border-color);
  background: transparent;
  color: var(--text-primary);
  font-size: 14px;
  outline: none;
}

.dropdown-list {
  overflow-y: auto;
  max-height: 250px;
}

.dropdown-item {
  padding: 10px 12px;
  cursor: pointer;
  transition: background 0.15s;
}

.dropdown-item:hover {
  background: var(--bg-secondary);
}

.dropdown-item.active {
  background: rgba(102, 126, 234, 0.15);
}

.dropdown-item.loading,
.dropdown-item.empty {
  color: var(--text-secondary);
  font-size: 13px;
  cursor: default;
}

.proj-name {
  display: block;
  font-size: 14px;
  color: var(--text-primary);
}

.proj-path {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
}
</style>
