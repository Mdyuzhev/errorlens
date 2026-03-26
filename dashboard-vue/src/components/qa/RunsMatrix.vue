<template>
  <div class="runs-matrix" v-if="runs.length">
    <div class="matrix-scroll">
      <table class="matrix-table">
        <thead>
          <tr>
            <th class="case-col">Test Case</th>
            <th v-for="run in recentRuns" :key="run.id" class="run-col">
              {{ formatDate(run.created_at || run.started_at) }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="tc in cases" :key="tc.id">
            <td class="case-col">{{ tc.title || tc.name }}</td>
            <td v-for="run in recentRuns" :key="run.id" class="run-col">
              <span
                class="status-dot"
                :class="getStatus(run, tc.id)"
                :title="getStatus(run, tc.id)"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
  <div v-else class="matrix-empty">No runs to display</div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  cases: { type: Array, required: true },
  runs: { type: Array, required: true }
})

const recentRuns = computed(() => {
  const sorted = [...props.runs].sort(
    (a, b) => new Date(b.created_at || b.started_at) - new Date(a.created_at || a.started_at)
  )
  return sorted.slice(0, 10).reverse()
})

function getStatus(run, testcaseId) {
  const r = run.results?.find(x => x.testcase_id === testcaseId)
  return r?.status || 'untested'
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString()
}
</script>

<style scoped>
.runs-matrix {
  overflow-x: auto;
  margin-top: 12px;
}
.matrix-scroll {
  min-width: 100%;
}
.matrix-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.matrix-table th,
.matrix-table td {
  padding: 8px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  white-space: nowrap;
}
.matrix-table thead th {
  color: #7a788a;
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.case-col {
  position: sticky;
  left: 0;
  background: #0f0e17;
  z-index: 2;
  color: #e8e6f0;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.run-col {
  text-align: center;
  min-width: 60px;
}
.status-dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
}
.status-dot.passed {
  background: #10b981;
}
.status-dot.failed {
  background: #ef4444;
}
.status-dot.blocked {
  background: #f59e0b;
}
.status-dot.skipped {
  background: #6b7280;
}
.status-dot.in_progress {
  background: #3b82f6;
}
.status-dot.untested {
  background: #22203a;
  border: 1px solid rgba(255, 255, 255, 0.12);
}
.matrix-empty {
  color: #7a788a;
  text-align: center;
  padding: 24px;
  font-size: 13px;
}
</style>
