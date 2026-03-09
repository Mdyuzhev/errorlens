<template>
  <div class="run-view-overlay">
    <!-- Header -->
    <div class="run-header">
      <div class="run-header-left">
        <button class="btn-back" @click="goBack">&larr; Back</button>
        <h2 v-if="run">{{ run.name }}</h2>
        <span v-if="run" class="row-status" :class="run.status">{{ run.status }}</span>
      </div>
      <div class="run-header-right" v-if="run">
        <div class="run-counters-bar">
          <span class="counter-item total">{{ run.total }} total</span>
          <span class="counter-item passed">{{ run.passed }} passed</span>
          <span class="counter-item failed">{{ run.failed }} failed</span>
          <span class="counter-item blocked">{{ run.blocked }} blocked</span>
          <span class="counter-item skipped">{{ run.skipped }} skipped</span>
          <span class="counter-item remaining">{{ remaining }} remaining</span>
        </div>
        <button
          v-if="run.status !== 'completed'"
          class="btn-finish"
          :disabled="resultsCount === 0"
          @click="handleFinish"
        >
          Finish Run
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="loading-state">Loading run...</div>

    <!-- Content -->
    <div v-else-if="run" class="run-content">
      <!-- Left: case list -->
      <div class="case-list-panel">
        <div class="filter-bar">
          <select v-model="statusFilter" class="form-input filter-select">
            <option value="all">All</option>
            <option value="untested">Not tested</option>
            <option value="passed">Passed</option>
            <option value="failed">Failed</option>
            <option value="blocked">Blocked</option>
            <option value="skipped">Skipped</option>
          </select>
        </div>
        <div class="case-items">
          <div
            v-for="item in filteredResults"
            :key="item.testcase_id"
            class="case-item"
            :class="{ selected: selectedId === item.testcase_id, [`status-${item.status || 'none'}`]: true }"
            @click="selectCase(item)"
          >
            <div class="case-item-stripe" :class="item.status || 'none'"></div>
            <div class="case-item-body">
              <span v-if="item.human_id" class="human-id-badge">{{ item.human_id }}</span>
              <span class="case-item-title">{{ item.title }}</span>
              <span class="tc-priority" :class="item.priority?.toLowerCase()">{{ item.priority }}</span>
              <RunResultStatus :status="item.status" />
            </div>
          </div>
          <div v-if="filteredResults.length === 0" class="empty-state">
            No cases match filter.
          </div>
        </div>
      </div>

      <!-- Right: case detail + result marking -->
      <div class="case-detail-panel">
        <div v-if="!selectedCase" class="empty-state">Select a test case from the list.</div>
        <div v-else class="case-detail-content">
          <div class="case-info">
            <div class="case-info-header">
              <span v-if="selectedCase.human_id" class="human-id-badge">{{ selectedCase.human_id }}</span>
              <h3>{{ selectedCase.title }}</h3>
              <span class="tc-priority" :class="selectedCase.priority?.toLowerCase()">{{ selectedCase.priority }}</span>
            </div>

            <!-- Steps table -->
            <div v-if="parsedSteps.length > 0" class="steps-section">
              <h4>Steps</h4>
              <table class="steps-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Action</th>
                    <th>Expected Result</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(step, idx) in parsedSteps" :key="idx">
                    <td class="step-num">{{ idx + 1 }}</td>
                    <td>{{ step.action }}</td>
                    <td>{{ step.expected }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Result marking block -->
          <div v-if="run.status !== 'completed'" class="result-block" data-testid="result-block">
            <h4>Mark Result</h4>
            <div class="result-buttons" data-testid="result-buttons">
              <button
                class="result-btn passed"
                :class="{ active: resultForm.status === 'passed' }"
                @click="resultForm.status = 'passed'"
              >Passed</button>
              <button
                class="result-btn failed"
                :class="{ active: resultForm.status === 'failed' }"
                @click="resultForm.status = 'failed'"
              >Failed</button>
              <button
                class="result-btn blocked"
                :class="{ active: resultForm.status === 'blocked' }"
                @click="resultForm.status = 'blocked'"
              >Blocked</button>
              <button
                class="result-btn skipped"
                :class="{ active: resultForm.status === 'skipped' }"
                @click="resultForm.status = 'skipped'"
              >Skip</button>
            </div>
            <textarea
              v-model="resultForm.comment"
              class="form-textarea"
              placeholder="Comment (optional)"
              rows="2"
            ></textarea>
            <textarea
              v-if="resultForm.status === 'failed' || resultForm.status === 'blocked'"
              v-model="resultForm.error_details"
              class="form-textarea"
              placeholder="Error details"
              rows="2"
            ></textarea>
            <button
              class="btn-save-result"
              :disabled="!resultForm.status || store.runLoading"
              @click="saveResult"
            >
              {{ store.runLoading ? 'Saving...' : 'Save Result' }}
            </button>
          </div>

          <!-- Readonly results for completed runs -->
          <div v-else class="result-readonly">
            <h4>Result</h4>
            <RunResultStatus :status="selectedCase.status" />
            <p v-if="selectedCase.comment" class="readonly-comment">{{ selectedCase.comment }}</p>
            <p v-if="selectedCase.error_details" class="readonly-error">{{ selectedCase.error_details }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTestPlansStore } from '@/stores/testPlans'
import RunResultStatus from '@/components/testplans/RunResultStatus.vue'

const route = useRoute()
const router = useRouter()
const store = useTestPlansStore()

const selectedId = ref(null)
const statusFilter = ref('all')
const resultForm = ref({ status: null, comment: '', error_details: '' })

const run = computed(() => store.currentRun)

const remaining = computed(() => {
  if (!run.value) return 0
  return run.value.total - (run.value.passed + run.value.failed + run.value.blocked + run.value.skipped)
})

const resultsCount = computed(() => {
  if (!run.value) return 0
  return run.value.passed + run.value.failed + run.value.blocked + run.value.skipped
})

const filteredResults = computed(() => {
  if (!run.value?.results) return []
  if (statusFilter.value === 'all') return run.value.results
  if (statusFilter.value === 'untested') return run.value.results.filter(r => !r.status)
  return run.value.results.filter(r => r.status === statusFilter.value)
})

const selectedCase = computed(() => {
  if (!selectedId.value || !run.value?.results) return null
  return run.value.results.find(r => r.testcase_id === selectedId.value) || null
})

function extractText(value) {
  if (!value) return ''
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      if (parsed?.type === 'doc') return extractTextFromTipTap(parsed)
      return value
    } catch {
      return value
    }
  }
  if (typeof value === 'object' && value.type === 'doc') {
    return extractTextFromTipTap(value)
  }
  return String(value)
}

function extractTextFromTipTap(node) {
  if (!node) return ''
  if (node.type === 'text') return node.text || ''
  if (node.type === 'entityMention') return node.attrs?.entityTitle || ''
  if (!node.content) return ''
  const parts = node.content.map(child => extractTextFromTipTap(child))
  if (node.type === 'paragraph' || node.type === 'doc') {
    return parts.join('')
  }
  return parts.join('')
}

const parsedSteps = computed(() => {
  if (!selectedCase.value?.steps) return []
  let steps = selectedCase.value.steps
  if (typeof steps === 'string') {
    try { steps = JSON.parse(steps) } catch { return [] }
  }
  if (!Array.isArray(steps)) return []
  return steps.map(s => ({
    action: extractText(s.action || s.step || ''),
    expected: extractText(s.expected || s.expected_result || ''),
  }))
})

function selectCase(item) {
  selectedId.value = item.testcase_id
  // Pre-fill form with existing result
  resultForm.value = {
    status: item.status || null,
    comment: item.comment || '',
    error_details: item.error_details || '',
  }
}

async function saveResult() {
  if (!resultForm.value.status || !selectedId.value) return
  await store.recordResult(run.value.id, selectedId.value, {
    status: resultForm.value.status,
    comment: resultForm.value.comment || null,
    error_details: resultForm.value.error_details || null,
  })
}

async function handleFinish() {
  if (confirm('Finish this run? No more results can be recorded.')) {
    await store.finishRun(run.value.id)
  }
}

function goBack() {
  router.back()
}

onMounted(async () => {
  const runId = route.params.runId
  if (runId) {
    await store.fetchRun(runId)
    // Auto-select first case
    if (run.value?.results?.length > 0) {
      selectCase(run.value.results[0])
    }
  }
})
</script>

<style scoped>
.run-view-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.run-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.run-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.run-header-left h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 18px;
}

.run-header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.run-counters-bar {
  display: flex;
  gap: 8px;
}

.counter-item {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}
.counter-item.total { background: rgba(99, 102, 241, 0.15); color: #818cf8; }
.counter-item.passed { background: rgba(16, 185, 129, 0.15); color: #10b981; }
.counter-item.failed { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.counter-item.blocked { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.counter-item.skipped { background: rgba(107, 114, 128, 0.15); color: #6b7280; }
.counter-item.remaining { background: var(--bg-secondary); color: var(--text-secondary); }

.btn-back {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 14px;
  padding: 4px 8px;
}
.btn-back:hover { color: var(--text-primary); }

.btn-finish {
  padding: 8px 16px;
  background: var(--accent);
  border: none;
  border-radius: 8px;
  color: white;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
}
.btn-finish:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.row-status {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}
.row-status.in_progress { background: rgba(59, 130, 246, 0.2); color: #3b82f6; }
.row-status.completed { background: rgba(16, 185, 129, 0.2); color: #10b981; }

.loading-state {
  padding: 60px;
  text-align: center;
  color: var(--text-secondary);
}

.run-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* Left panel */
.case-list-panel {
  width: 380px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border-color);
  overflow: hidden;
}

.filter-bar {
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
}

.filter-select {
  width: 100%;
  padding: 6px 10px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
}

.case-items {
  flex: 1;
  overflow-y: auto;
}

.case-item {
  display: flex;
  cursor: pointer;
  transition: background 0.15s;
}
.case-item:hover { background: var(--bg-secondary); }
.case-item.selected { background: rgba(99, 102, 241, 0.1); }

.case-item-stripe {
  width: 4px;
  flex-shrink: 0;
}
.case-item-stripe.passed { background: #10b981; }
.case-item-stripe.failed { background: #ef4444; }
.case-item-stripe.blocked { background: #f59e0b; }
.case-item-stripe.skipped { background: #6b7280; }
.case-item-stripe.none { background: transparent; }

.case-item-body {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  min-width: 0;
}

.case-item-title {
  flex: 1;
  color: var(--text-primary);
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.human-id-badge {
  flex-shrink: 0;
  padding: 2px 6px;
  background: rgba(99, 102, 241, 0.2);
  color: #818cf8;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
}

.tc-priority {
  flex-shrink: 0;
  padding: 2px 6px;
  border-radius: 12px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
}
.tc-priority.critical { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
.tc-priority.high { background: rgba(249, 115, 22, 0.2); color: #f97316; }
.tc-priority.medium { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
.tc-priority.low { background: rgba(107, 114, 128, 0.2); color: #6b7280; }

.empty-state {
  padding: 40px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 14px;
}

/* Right panel */
.case-detail-panel {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.case-detail-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.case-info-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.case-info-header h3 {
  margin: 0;
  color: var(--text-primary);
  flex: 1;
}

.steps-section h4 {
  color: var(--text-primary);
  margin: 0 0 12px;
  font-size: 14px;
}

.steps-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.steps-table th {
  text-align: left;
  padding: 8px 12px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-color);
  font-weight: 600;
  font-size: 12px;
}

.steps-table td {
  padding: 8px 12px;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-color);
  vertical-align: top;
}

.step-num {
  color: var(--text-secondary);
  width: 40px;
  text-align: center;
}

/* Result block */
.result-block {
  padding: 20px;
  background: var(--bg-card);
  border-radius: 12px;
  border: 1px solid var(--border-color);
}

.result-block h4 {
  margin: 0 0 12px;
  color: var(--text-primary);
  font-size: 14px;
}

.result-buttons {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.result-btn {
  flex: 1;
  padding: 12px;
  border-radius: 8px;
  border: 2px solid transparent;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
  transition: all 0.2s;
}
.result-btn.passed {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border-color: rgba(16, 185, 129, 0.2);
}
.result-btn.passed.active {
  background: rgba(16, 185, 129, 0.3);
  border-color: #10b981;
}
.result-btn.failed {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.2);
}
.result-btn.failed.active {
  background: rgba(239, 68, 68, 0.3);
  border-color: #ef4444;
}
.result-btn.blocked {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
  border-color: rgba(245, 158, 11, 0.2);
}
.result-btn.blocked.active {
  background: rgba(245, 158, 11, 0.3);
  border-color: #f59e0b;
}
.result-btn.skipped {
  background: rgba(107, 114, 128, 0.1);
  color: #6b7280;
  border-color: rgba(107, 114, 128, 0.2);
}
.result-btn.skipped.active {
  background: rgba(107, 114, 128, 0.3);
  border-color: #6b7280;
}

.form-textarea {
  width: 100%;
  padding: 8px 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 13px;
  font-family: inherit;
  resize: vertical;
  margin-bottom: 8px;
  box-sizing: border-box;
}

.btn-save-result {
  padding: 10px 20px;
  background: var(--accent);
  border: none;
  border-radius: 8px;
  color: white;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
  width: 100%;
}
.btn-save-result:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Readonly */
.result-readonly {
  padding: 20px;
  background: var(--bg-card);
  border-radius: 12px;
  border: 1px solid var(--border-color);
}

.result-readonly h4 {
  margin: 0 0 12px;
  color: var(--text-primary);
  font-size: 14px;
}

.readonly-comment {
  margin: 8px 0 0;
  color: var(--text-secondary);
  font-size: 13px;
}

.readonly-error {
  margin: 4px 0 0;
  color: #ef4444;
  font-size: 13px;
}
</style>
