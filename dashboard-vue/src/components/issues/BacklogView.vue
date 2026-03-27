<template>
  <div class="backlog-view">
    <div class="backlog-header">
      <h3>Backlog <span class="count">({{ issues.length }})</span></h3>
    </div>

    <div v-if="!issues.length" class="empty-backlog">
      <p>No items in backlog</p>
    </div>

    <div
      v-for="(issue, index) in issues"
      :key="issue.id"
      class="backlog-row"
      draggable="true"
      @dragstart="onDragStart($event, index)"
      @dragover.prevent="onDragOver($event, index)"
      @dragleave="onDragLeave"
      @dragend="onDragEnd"
      @drop="onDrop($event, index)"
      :class="{ 'drag-over': dragOverIndex === index }"
    >
      <div class="row-handle">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
          <circle cx="4" cy="2" r="1" /><circle cx="8" cy="2" r="1" />
          <circle cx="4" cy="6" r="1" /><circle cx="8" cy="6" r="1" />
          <circle cx="4" cy="10" r="1" /><circle cx="8" cy="10" r="1" />
        </svg>
      </div>

      <span v-if="issue.human_id" class="human-id">{{ issue.human_id }}</span>

      <span v-if="issue.type" class="type-indicator" :style="{ background: issue.type.color }">
        <AppIcon :name="issue.type.icon" :size="10" />
      </span>

      <span class="issue-title">{{ issue.title }}</span>

      <div class="row-meta">
        <span v-if="issue.story_points != null" class="story-points">{{ issue.story_points }}SP</span>
        <span class="priority-dot" :class="issue.priority"></span>
        <span v-if="issue.task_status" class="status-pill" :style="{ background: issue.task_status.color }">
          {{ issue.task_status.name }}
        </span>
        <span v-if="issue.assignee_user" class="assignee">
          {{ issue.assignee_user.display_name || issue.assignee_user.username }}
        </span>
        <button
          v-if="sprint"
          class="btn-add-sprint"
          title="Add to sprint"
          @click.stop="$emit('add-to-sprint', issue.id, sprint.id)"
        >+ Sprint</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'

defineProps({
  issues: { type: Array, default: () => [] },
  sprint: { type: Object, default: null }
})

const emit = defineEmits(['rank-change', 'add-to-sprint'])

const dragIndex = ref(null)
const dragOverIndex = ref(null)

function onDragStart(event, index) {
  dragIndex.value = index
  event.dataTransfer.effectAllowed = 'move'
}

function onDragOver(event, index) {
  dragOverIndex.value = index
}

function onDragLeave() {
  dragOverIndex.value = null
}

function onDragEnd() {
  dragIndex.value = null
  dragOverIndex.value = null
}

function onDrop(event, targetIndex) {
  if (dragIndex.value !== null && dragIndex.value !== targetIndex) {
    emit('rank-change', dragIndex.value, targetIndex)
  }
  dragIndex.value = null
  dragOverIndex.value = null
}
</script>

<style scoped>
.backlog-view {
  background: var(--bg-card);
  border-radius: 12px;
  overflow: hidden;
}

.backlog-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.backlog-header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.count { color: var(--text-secondary); font-weight: 400; }

.empty-backlog {
  padding: 40px;
  text-align: center;
  color: var(--text-secondary);
}

.backlog-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-bottom: 1px solid var(--border-color);
  cursor: grab;
  transition: background 0.15s;
}

.backlog-row:hover { background: var(--bg-secondary); }
.backlog-row:last-child { border-bottom: none; }
.backlog-row.drag-over { background: var(--accent-muted); }

.row-handle { color: var(--text-secondary); flex-shrink: 0; }

.human-id {
  font-size: 11px;
  font-family: monospace;
  color: var(--text-secondary);
  background: var(--bg-primary);
  padding: 1px 6px;
  border-radius: 4px;
  flex-shrink: 0;
}

.type-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 4px;
  color: white;
  flex-shrink: 0;
}

.issue-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  color: var(--text-primary);
}

.row-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.story-points {
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-muted);
  padding: 1px 6px;
  border-radius: 4px;
}

.priority-dot { width: 8px; height: 8px; border-radius: 50%; }
.priority-dot.high { background: #f59e0b; }
.priority-dot.medium { background: #3b82f6; }
.priority-dot.low { background: #6b7280; }

.status-pill {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
  color: white;
}

.assignee {
  font-size: 12px;
  color: var(--text-secondary);
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-add-sprint {
  padding: 2px 8px;
  border: 1px solid var(--accent);
  border-radius: 6px;
  background: none;
  color: var(--accent);
  font-size: 11px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
}

.btn-add-sprint:hover {
  background: var(--accent);
  color: white;
}
</style>
