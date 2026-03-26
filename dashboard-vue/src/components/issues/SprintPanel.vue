<template>
  <div class="sprint-panel">
    <div class="sprint-info">
      <div class="sprint-header">
        <h3 class="sprint-name">{{ sprint.name }}</h3>
        <span class="sprint-status" :class="sprint.status">{{ sprint.status }}</span>
      </div>
      <p v-if="sprint.goal" class="sprint-goal">{{ sprint.goal }}</p>
      <div class="sprint-dates">
        <span v-if="sprint.start_date">Start: {{ formatDate(sprint.start_date) }}</span>
        <span v-if="sprint.end_date">End: {{ formatDate(sprint.end_date) }}</span>
        <span v-if="daysRemaining !== null" class="days-remaining" :class="{ overdue: daysRemaining < 0 }">
          {{ daysRemaining >= 0 ? daysRemaining + 'd remaining' : Math.abs(daysRemaining) + 'd overdue' }}
        </span>
      </div>
    </div>
    <div class="sprint-actions">
      <button
        v-if="sprint.status === 'planned'"
        class="btn btn-primary btn-sm"
        @click="$emit('start', sprint.id)"
      >Start Sprint</button>
      <button
        v-if="sprint.status === 'active'"
        class="btn btn-secondary btn-sm"
        @click="$emit('complete', sprint.id)"
      >Complete Sprint</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  sprint: { type: Object, required: true }
})

defineEmits(['start', 'complete'])

const daysRemaining = computed(() => {
  if (!props.sprint.end_date || props.sprint.status !== 'active') return null
  const end = new Date(props.sprint.end_date)
  const now = new Date()
  return Math.ceil((end - now) / (1000 * 60 * 60 * 24))
})

function formatDate(date) {
  if (!date) return ''
  return new Date(date).toLocaleDateString()
}
</script>

<style scoped>
.sprint-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-card);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 16px;
  border-left: 4px solid var(--accent);
}

.sprint-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.sprint-name {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.sprint-status {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
}

.sprint-status.planned { background: var(--bg-secondary); color: var(--text-secondary); }
.sprint-status.active { background: rgba(34, 197, 94, 0.15); color: #22c55e; }
.sprint-status.completed { background: rgba(107, 114, 128, 0.15); color: #6b7280; }

.sprint-goal {
  margin: 4px 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.sprint-dates {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--text-secondary);
}

.days-remaining { font-weight: 500; }
.days-remaining.overdue { color: #ef4444; }

.sprint-actions {
  flex-shrink: 0;
}

.btn-sm {
  padding: 6px 14px;
  font-size: 13px;
}
</style>
