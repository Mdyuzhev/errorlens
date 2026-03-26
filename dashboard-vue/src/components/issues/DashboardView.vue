<template>
  <div class="dashboard-view">
    <div v-if="loading" class="loading-state">Loading dashboard...</div>

    <div v-else-if="data" class="dashboard-grid">
      <!-- By Type -->
      <div class="dash-card">
        <h3>By Type</h3>
        <div v-if="data.by_type?.length" class="bar-chart">
          <div v-for="item in data.by_type" :key="item.name" class="bar-chart-row">
            <span class="bar-chart-label">{{ item.name }}</span>
            <div class="bar-chart-track">
              <div
                class="bar-chart-fill"
                :style="{ width: barWidth(item.count, maxByType) + '%', background: item.color || 'var(--accent)' }"
              ></div>
            </div>
            <span class="bar-chart-count">{{ item.count }}</span>
          </div>
        </div>
        <div v-else class="empty-hint">No data</div>
      </div>

      <!-- By Priority -->
      <div class="dash-card">
        <h3>By Priority</h3>
        <div v-if="data.by_priority?.length" class="bar-chart">
          <div v-for="item in data.by_priority" :key="item.name" class="bar-chart-row">
            <span class="bar-chart-label">{{ item.name }}</span>
            <div class="bar-chart-track">
              <div
                class="bar-chart-fill"
                :style="{ width: barWidth(item.count, maxByPriority) + '%', background: priorityColor(item.name) }"
              ></div>
            </div>
            <span class="bar-chart-count">{{ item.count }}</span>
          </div>
        </div>
        <div v-else class="empty-hint">No data</div>
      </div>

      <!-- Top Assignees -->
      <div class="dash-card">
        <h3>Top Assignees</h3>
        <div v-if="data.by_assignee?.length" class="list-stats">
          <div v-for="item in data.by_assignee" :key="item.name" class="list-stat-row">
            <span class="list-stat-name">{{ item.name || 'Unassigned' }}</span>
            <span class="list-stat-badge">{{ item.count }}</span>
          </div>
        </div>
        <div v-else class="empty-hint">No data</div>
      </div>

      <!-- By Component -->
      <div class="dash-card">
        <h3>By Component</h3>
        <div v-if="data.by_component?.length" class="list-stats">
          <div v-for="item in data.by_component" :key="item.name" class="list-stat-row">
            <span class="list-stat-name">{{ item.name || 'None' }}</span>
            <span class="list-stat-badge">{{ item.count }}</span>
          </div>
        </div>
        <div v-else class="empty-hint">No data</div>
      </div>
    </div>

    <div v-else class="empty-state">No dashboard data available</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useIssuesStore } from '@/stores/issues'

const props = defineProps({
  projectId: { type: String, required: true },
})

const store = useIssuesStore()

const loading = computed(() => store.dashboardLoading)
const data = computed(() => store.dashboard)

const maxByType = computed(() => Math.max(...(data.value?.by_type?.map(i => i.count) || [1])))
const maxByPriority = computed(() => Math.max(...(data.value?.by_priority?.map(i => i.count) || [1])))

function barWidth(count, max) {
  if (!max || max === 0) return 0
  return Math.round((count / max) * 100)
}

function priorityColor(name) {
  const map = { high: '#f59e0b', medium: '#3b82f6', low: '#6b7280', critical: '#ef4444' }
  return map[name?.toLowerCase()] || 'var(--accent)'
}

async function loadDashboard() {
  if (props.projectId) {
    await store.fetchDashboard(props.projectId)
  }
}

onMounted(loadDashboard)
watch(() => props.projectId, loadDashboard)
</script>

<style scoped>
.dashboard-view { padding: 4px 0; }

.loading-state,
.empty-state {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
  font-size: 14px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

@media (max-width: 768px) {
  .dashboard-grid { grid-template-columns: 1fr; }
}

.dash-card {
  background: var(--bg-card);
  border-radius: 12px;
  padding: 16px;
}

.dash-card h3 {
  margin: 0 0 14px 0;
  font-size: 14px;
  color: var(--text-primary);
}

/* Bar chart */
.bar-chart-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.bar-chart-label {
  width: 100px;
  font-size: 13px;
  text-align: right;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bar-chart-track {
  flex: 1;
  height: 20px;
  background: var(--bg-secondary);
  border-radius: 4px;
  overflow: hidden;
}

.bar-chart-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}

.bar-chart-count {
  width: 30px;
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 600;
}

/* List stats */
.list-stats {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.list-stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid var(--bg-secondary);
  font-size: 13px;
}

.list-stat-row:last-child { border-bottom: none; }

.list-stat-name { color: var(--text-primary); }

.list-stat-badge {
  background: var(--bg-secondary);
  color: var(--text-primary);
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
}

.empty-hint {
  font-size: 12px;
  color: var(--text-secondary);
  font-style: italic;
}
</style>
