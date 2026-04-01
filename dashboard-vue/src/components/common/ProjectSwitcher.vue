<template>
  <div class="project-switcher" ref="switcherRef">
    <button
      class="switcher-btn"
      @click="toggleDropdown"
      :title="`Активный проект: ${projectStore.currentProject?.name || 'Не выбран'}`"
    >
      <span v-if="projectStore.currentProject?.key" class="proj-key">
        {{ projectStore.currentProject.key }}
      </span>
      <span class="proj-name">{{ projectStore.currentProject?.name || 'Проект' }}</span>
      <span class="proj-arrow" :class="{ open: showDropdown }">▾</span>
    </button>

    <div v-if="showDropdown" class="switcher-dropdown">
      <div class="dropdown-header">Проекты</div>
      <div
        v-for="project in projectStore.projects"
        :key="project.id"
        class="dropdown-item"
        :class="{ active: project.id === projectStore.currentProjectId }"
        @click="selectProject(project)"
      >
        <span class="item-key">{{ project.key || '—' }}</span>
        <span class="item-name">{{ project.name }}</span>
        <span v-if="project.id === projectStore.currentProjectId" class="item-check">✓</span>
      </div>
      <div v-if="!projectStore.projects.length" class="dropdown-empty">
        Нет проектов
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useCurrentProjectStore } from '@/stores/currentProject'

const projectStore = useCurrentProjectStore()
const showDropdown = ref(false)
const switcherRef = ref(null)

function toggleDropdown() {
  showDropdown.value = !showDropdown.value
}

function selectProject(project) {
  projectStore.setProject(project)
  showDropdown.value = false
}

function onClickOutside(e) {
  if (switcherRef.value && !switcherRef.value.contains(e.target)) {
    showDropdown.value = false
  }
}

onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))
</script>

<style scoped>
.project-switcher {
  position: relative;
  display: flex;
  align-items: center;
}

.switcher-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: none;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  max-width: 200px;
  white-space: nowrap;
}

.switcher-btn:hover {
  border-color: var(--accent);
  color: var(--text-primary);
  background: var(--accent-muted);
}

.proj-key {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  background: var(--accent-muted);
  color: var(--accent);
  padding: 1px 5px;
  border-radius: 4px;
  flex-shrink: 0;
}

.proj-name {
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

.proj-arrow {
  font-size: 10px;
  opacity: 0.6;
  transition: transform 0.15s;
  flex-shrink: 0;
}
.proj-arrow.open {
  transform: rotate(180deg);
}

.switcher-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  min-width: 220px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  box-shadow: var(--shadow-dropdown);
  z-index: 300;
  overflow: hidden;
}

.dropdown-header {
  padding: 8px 14px 6px;
  font-size: 10px;
  font-weight: 700;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  border-bottom: 1px solid var(--border-color);
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  cursor: pointer;
  transition: background 0.1s;
}

.dropdown-item:hover {
  background: var(--bg-secondary);
}

.dropdown-item.active {
  background: var(--accent-bg);
}

.item-key {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  background: var(--accent-muted);
  color: var(--accent);
  padding: 2px 6px;
  border-radius: 4px;
  flex-shrink: 0;
  min-width: 30px;
  text-align: center;
}

.item-name {
  flex: 1;
  font-size: 13px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-check {
  color: var(--accent);
  font-weight: 700;
  font-size: 13px;
  flex-shrink: 0;
}

.dropdown-empty {
  padding: 16px 14px;
  font-size: 13px;
  color: var(--text-secondary);
  text-align: center;
}
</style>
