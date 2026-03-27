<template>
  <div class="qa-runs">
    <h3 class="runs-title">Test Runs</h3>

    <div class="runs-filters">
      <select v-model="filterStatus" class="filter-select">
        <option value="">Все статусы</option>
        <option value="in_progress">In Progress</option>
        <option value="completed">Completed</option>
        <option value="aborted">Aborted</option>
      </select>
      <select v-model="filterPlan" class="filter-select">
        <option value="">Все планы</option>
        <option v-for="plan in store.plans" :key="plan.id" :value="plan.id">
          {{ plan.name }}
        </option>
      </select>
      <button
        v-if="filterStatus || filterPlan"
        class="filter-reset"
        @click="filterStatus = ''; filterPlan = ''"
      >Сбросить</button>
    </div>

    <div v-if="store.loading" class="runs-loading">Loading...</div>

    <div v-else-if="!store.allRuns.length" class="runs-empty">
      No test runs found
    </div>

    <div v-else class="runs-list">
      <div
        v-for="run in filteredRuns"
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
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useQAStore } from '@/stores/qa'

const props = defineProps({
  projectId: { type: String, required: true }
})

const store = useQAStore()
const router = useRouter()

const filterStatus = ref('')
const filterPlan = ref('')

const filteredRuns = computed(() => {
  let runs = store.allRuns
  if (filterStatus.value) {
    runs = runs.filter(r => r.status === filterStatus.value)
  }
  if (filterPlan.value) {
    runs = runs.filter(r => r.plan_id === filterPlan.value || r.test_plan_id === filterPlan.value)
  }
  return runs
})

onMounted(() => {
  store.fetchAllRuns(props.projectId)
  store.fetchPlans(props.projectId)
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
.runs-filters {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  align-items: center;
  flex-wrap: wrap;
}
.filter-select {
  padding: 6px 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  outline: none;
}
.filter-select:focus {
  border-color: var(--accent);
}
.filter-reset {
  padding: 6px 12px;
  background: none;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.filter-reset:hover {
  border-color: var(--accent);
  color: var(--accent);
}
</style>
