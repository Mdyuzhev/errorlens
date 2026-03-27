<template>
  <div class="qa-runs">
    <h3 class="runs-title">Test Runs</h3>

    <div v-if="store.loading" class="runs-loading">Loading...</div>

    <div v-else-if="!store.allRuns.length" class="runs-empty">
      No test runs found
    </div>

    <div v-else class="runs-list">
      <div
        v-for="run in store.allRuns"
        :key="run.id"
        class="run-row"
        @click="goToRun(run)"
      >
        <div class="run-info">
          <span class="run-name">{{ run.name || `Run #${run.id}` }}</span>
          <span class="run-plan" v-if="run.plan_name">{{ run.plan_name }}</span>
        </div>

        <div class="run-meta">
          <span class="run-date">{{ formatDate(run.created_at) }}</span>
          <span class="run-badge" :class="run.status">{{ run.status }}</span>
        </div>

        <div class="run-counters">
          <span class="counter passed" v-if="run.passed_count">
            {{ run.passed_count }} passed
          </span>
          <span class="counter failed" v-if="run.failed_count">
            {{ run.failed_count }} failed
          </span>
          <span class="counter blocked" v-if="run.blocked_count">
            {{ run.blocked_count }} blocked
          </span>
        </div>

        <div class="run-percent">
          {{ passPercent(run) }}%
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQAStore } from '@/stores/qa'

const props = defineProps({
  projectId: { type: String, required: true }
})

const store = useQAStore()
const router = useRouter()

onMounted(() => {
  store.fetchAllRuns(props.projectId)
})

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString()
}

function passPercent(run) {
  const total = (run.passed_count || 0) + (run.failed_count || 0) +
    (run.blocked_count || 0) + (run.skipped_count || 0)
  if (!total) return 0
  return Math.round(((run.passed_count || 0) / total) * 100)
}

function goToRun(run) {
  router.push(`/test-plans/runs/${run.id}`)
}
</script>

<style scoped>
.qa-runs {
  padding: 0;
}
.runs-title {
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px 0;
}
.runs-loading,
.runs-empty {
  color: var(--text-secondary);
  text-align: center;
  padding: 32px;
  font-size: 13px;
}
.runs-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.run-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  border-radius: 6px;
  cursor: pointer;
  border-bottom: 1px solid var(--border-color);
  transition: background 0.15s;
}
.run-row:hover {
  background: var(--bg-tertiary);
}
.run-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.run-name {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.run-plan {
  color: var(--text-secondary);
  font-size: 12px;
}
.run-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}
.run-date {
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}
.run-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
  text-transform: capitalize;
}
.run-badge.completed,
.run-badge.finished {
  color: var(--success);
  background: var(--accent-bg, var(--accent-muted));
}
.run-badge.in_progress,
.run-badge.active {
  color: var(--accent);
  background: var(--accent-muted);
}
.run-badge.aborted {
  color: var(--error);
  background: var(--accent-bg, var(--accent-muted));
}
.run-counters {
  display: flex;
  gap: 8px;
}
.counter {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}
.counter.passed {
  color: var(--success);
  background: var(--accent-bg, var(--accent-muted));
}
.counter.failed {
  color: var(--error);
  background: var(--accent-bg, var(--accent-muted));
}
.counter.blocked {
  color: var(--warning);
  background: var(--accent-bg, var(--accent-muted));
}
.run-percent {
  color: var(--accent);
  font-size: 14px;
  font-weight: 600;
  min-width: 40px;
  text-align: right;
}
</style>
