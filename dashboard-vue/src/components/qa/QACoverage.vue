<template>
  <div class="cov-root">
    <!-- Loading -->
    <div v-if="store.coverageLoading" class="cov-loading">Загрузка покрытия...</div>

    <!-- Empty -->
    <div v-else-if="!store.coverage" class="cov-loading">Нет данных</div>

    <!-- Main -->
    <template v-else>
      <!-- Summary bar -->
      <div class="cov-summary">
        <div class="cov-stat">
          <span class="cov-stat-label">Покрыто</span>
          <span class="cov-stat-value">{{ summary.covered_issues }}/{{ summary.total_issues }}</span>
          <div class="cov-progress">
            <div
              class="cov-progress-fill"
              :style="{ width: summary.coverage_pct + '%' }"
            />
          </div>
          <span class="cov-stat-pct">{{ summary.coverage_pct }}%</span>
        </div>

        <div class="cov-stat">
          <span class="cov-dot cov-dot--passed" />
          <span class="cov-stat-label">Passed</span>
          <span class="cov-stat-value">{{ summary.passed }}</span>
        </div>

        <div class="cov-stat">
          <span class="cov-dot cov-dot--failed" />
          <span class="cov-stat-label">Failed</span>
          <span class="cov-stat-value">{{ summary.failed }}</span>
        </div>

        <div class="cov-stat">
          <span class="cov-dot cov-dot--notrun" />
          <span class="cov-stat-label">Без прогона</span>
          <span class="cov-stat-value">{{ summary.not_run }}</span>
        </div>
      </div>

      <!-- Issues tree -->
      <div class="cov-list">
        <template v-for="issue in issues" :key="issue.id">
          <!-- Issue row -->
          <div
            class="cov-issue-row"
            @click="toggleIssue(issue.id)"
          >
            <span class="cov-arrow" :class="{ expanded: expandedIssues.has(issue.id) }">&#9654;</span>
            <span class="cov-type-badge" :class="'cov-type--' + (issue.type_slug || 'task')">
              {{ issue.type_name || issue.type_slug || 'task' }}
            </span>
            <span class="cov-human-id">{{ issue.human_id }}</span>
            <span class="cov-issue-title">{{ issue.title }}</span>
            <span class="cov-spacer" />
            <span class="cov-indicator" :class="'cov-status--' + issue.coverage_status">
              {{ coverageLabel(issue) }}
            </span>
          </div>

          <!-- Expanded test cases -->
          <template v-if="expandedIssues.has(issue.id)">
            <div
              v-for="tc in (issue.test_cases || [])"
              :key="tc.id"
              class="cov-tc-row"
              @click="$emit('open-case', tc.id)"
            >
              <span class="cov-tc-icon">&#128203;</span>
              <span class="cov-human-id">{{ tc.human_id }}</span>
              <span class="cov-tc-title">{{ tc.title }}</span>
              <span class="cov-spacer" />
              <span class="cov-run-badge" :class="'cov-run--' + (tc.last_run_status || 'none')">
                {{ runStatusLabel(tc.last_run_status) }}
              </span>
            </div>
            <div v-if="!issue.test_cases?.length" class="cov-tc-row cov-tc-empty">
              Нет привязанных тест-кейсов
            </div>
          </template>
        </template>

        <div v-if="!issues.length" class="cov-loading">
          Нет задач в проекте
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useQAStore } from '@/stores/qa'

const props = defineProps({
  projectId: { type: String, default: null }
})

defineEmits(['open-case'])

const store = useQAStore()
const expandedIssues = ref(new Set())

const summary = computed(() => store.coverage?.summary || {
  total_issues: 0,
  covered_issues: 0,
  coverage_pct: 0,
  total_test_cases: 0,
  passed: 0,
  failed: 0,
  not_run: 0
})

const issues = computed(() => store.coverage?.issues || [])

function toggleIssue(id) {
  if (expandedIssues.value.has(id)) expandedIssues.value.delete(id)
  else expandedIssues.value.add(id)
}

function coverageLabel(issue) {
  const map = {
    none: 'Нет кейсов',
    passing: 'Покрыто',
    failing: 'Есть падения',
    not_run: 'Без прогона',
    partial: 'Частично',
  }
  return map[issue.coverage_status] || '—'
}

function runStatusLabel(status) {
  const map = {
    passed: 'Passed',
    failed: 'Failed',
    blocked: 'Blocked',
    skipped: 'Skipped'
  }
  return status ? (map[status] || status) : 'Не запускался'
}

async function load() {
  if (props.projectId) await store.fetchCoverage(props.projectId)
}

onMounted(load)
watch(() => props.projectId, load)
</script>

<style scoped>
.cov-root {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.cov-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  color: var(--text-secondary);
  font-size: 14px;
}

/* Summary bar */
.cov-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  padding: 16px 24px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.cov-stat {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.cov-stat-label {
  color: var(--text-secondary);
}

.cov-stat-value {
  font-weight: 600;
  color: var(--text-primary);
}

.cov-stat-pct {
  font-weight: 600;
  color: var(--accent);
  font-size: 12px;
}

.cov-progress {
  width: 80px;
  height: 6px;
  border-radius: 3px;
  background: var(--bg-tertiary);
  overflow: hidden;
}

.cov-progress-fill {
  height: 100%;
  border-radius: 3px;
  background: var(--accent);
  transition: width 0.3s ease;
}

.cov-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.cov-dot--passed {
  background: #10b981;
}

.cov-dot--failed {
  background: #ef4444;
}

.cov-dot--notrun {
  background: #6b7280;
}

/* Issues list */
.cov-list {
  flex: 1;
  overflow-y: auto;
}

.cov-issue-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  cursor: pointer;
  border-bottom: 1px solid var(--border-color);
  transition: background 0.1s;
}

.cov-issue-row:hover {
  background: var(--bg-tertiary);
}

.cov-arrow {
  font-size: 10px;
  color: var(--text-secondary);
  transition: transform 0.15s;
  width: 14px;
  text-align: center;
  flex-shrink: 0;
}

.cov-arrow.expanded {
  transform: rotate(90deg);
}

.cov-type-badge {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  padding: 2px 6px;
  border-radius: 3px;
  flex-shrink: 0;
}

.cov-type--epic {
  background: rgba(139, 92, 246, 0.15);
  color: #8b5cf6;
}

.cov-type--bug {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.cov-type--story {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.cov-type--task {
  background: rgba(107, 114, 128, 0.15);
  color: var(--text-secondary);
}

.cov-human-id {
  font-family: monospace;
  font-size: 12px;
  color: var(--accent);
  background: var(--bg-tertiary);
  padding: 1px 6px;
  border-radius: 3px;
  flex-shrink: 0;
}

.cov-issue-title {
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.cov-spacer {
  flex: 1;
}

/* Coverage status indicator */
.cov-indicator {
  font-size: 12px;
  font-weight: 500;
  flex-shrink: 0;
  white-space: nowrap;
}

.cov-status--none {
  color: #6b7280;
}

.cov-status--passing {
  color: #10b981;
}

.cov-status--failing {
  color: #ef4444;
}

.cov-status--not_run {
  color: #eab308;
}

.cov-status--partial {
  color: #eab308;
}

/* Test case rows */
.cov-tc-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px 8px 42px;
  cursor: pointer;
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
  transition: background 0.1s;
}

.cov-tc-row:hover {
  background: var(--bg-tertiary);
}

.cov-tc-empty {
  color: var(--text-secondary);
  font-size: 12px;
  font-style: italic;
  cursor: default;
}

.cov-tc-icon {
  font-size: 14px;
  flex-shrink: 0;
}

.cov-tc-title {
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

/* Run status badge */
.cov-run-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 3px;
  flex-shrink: 0;
  white-space: nowrap;
}

.cov-run--passed {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.cov-run--failed {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.cov-run--blocked {
  background: rgba(234, 179, 8, 0.15);
  color: #eab308;
}

.cov-run--skipped {
  background: rgba(107, 114, 128, 0.15);
  color: var(--text-secondary);
}

.cov-run--none {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}
</style>
