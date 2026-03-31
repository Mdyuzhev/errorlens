<template>
  <Teleport to="body">
    <div class="runner-overlay" @click.self="$emit('close')">
      <div class="runner-modal">

        <!-- ── Header ─────────────────────────────────────── -->
        <div class="runner-header">
          <div class="runner-header-left">
            <h3 class="runner-title">Collection Runner</h3>
            <span class="runner-col-name">{{ collectionName }}</span>
          </div>
          <div class="runner-header-right">
            <button
              v-if="!running && !done"
              class="btn-settings"
              @click="showSettings = !showSettings"
              :class="{ active: showSettings }"
            >⚙ Settings</button>
            <button class="runner-close" @click="$emit('close')">&times;</button>
          </div>
        </div>

        <!-- ── Settings panel (collapsible) ──────────────────── -->
        <div v-if="showSettings && !running && !done" class="runner-settings-panel">
          <div class="settings-row">
            <label class="setting-label">
              Delay (ms)
              <input v-model.number="options.delayMs" type="number" min="0" step="100" class="setting-input" />
            </label>
            <label class="setting-label">
              Iterations
              <input v-model.number="options.iterations" type="number" min="1" max="100" class="setting-input" />
            </label>
            <label class="setting-check">
              <input v-model="options.stopOnError" type="checkbox" />
              Stop on first error
            </label>
          </div>
          <!-- Requests list with drag -->
          <div class="request-list">
            <div class="request-list-header">
              <span>Requests ({{ selectedCount }} selected)</span>
              <button class="btn-select-all" @click="selectAll">Select All</button>
            </div>
            <div
              v-for="(req, idx) in orderedRequests" :key="req.id"
              class="request-item"
              draggable="true"
              @dragstart="onDragStart(idx, $event)"
              @dragover.prevent="onDragOver(idx)"
              @drop="onDrop(idx)"
              @dragend="dragIdx = -1"
              :class="{ 'drag-over': dragOverIdx === idx }"
            >
              <span class="drag-handle">⠿</span>
              <input type="checkbox" v-model="req.selected" class="req-check" />
              <span class="method-badge" :class="methodClass(req.method)">{{ req.method }}</span>
              <span class="req-name">{{ req.name || 'Untitled' }}</span>
            </div>
            <div v-if="!orderedRequests.length" class="empty-msg">No requests in collection</div>
          </div>
        </div>

        <!-- ── Summary Bar ───────────────────────────────────── -->
        <div class="runner-summary-bar" :class="summaryBarClass">
          <div class="summary-bar-left">
            <template v-if="!running && !done">
              <span class="sb-item sb-neutral">{{ selectedCount }} requests selected</span>
            </template>
            <template v-else>
              <span class="sb-item sb-accent">
                {{ done ? completedCount : completed }}/{{ totalRequests }} requests
              </span>
              <span class="sb-sep">·</span>
              <span class="sb-item" :class="totalFailed > 0 ? 'sb-fail' : 'sb-pass'">
                {{ totalPassed }}/{{ totalPassed + totalFailed }} assertions
              </span>
              <span class="sb-sep">·</span>
              <span class="sb-item" :class="passRateCls">{{ passRate }}% pass</span>
              <span class="sb-sep">·</span>
              <span class="sb-item sb-neutral">{{ totalTime }}ms</span>
            </template>
          </div>
          <div class="summary-bar-right">
            <div v-if="running" class="sb-progress-wrap">
              <div class="sb-progress-bar" :style="{ width: progressPct + '%' }"></div>
            </div>
          </div>
        </div>

        <!-- ── Main Body: split layout ───────────────────────── -->
        <div v-if="running || done" class="runner-body">

          <!-- LEFT: request list -->
          <div class="runner-left">
            <div class="runner-left-filters">
              <button
                v-for="f in filters" :key="f.key"
                class="filter-tab"
                :class="{ active: activeFilter === f.key }"
                @click="activeFilter = f.key"
              >
                {{ f.label }}
                <span v-if="f.count !== undefined" class="filter-count" :class="f.colorClass">
                  {{ f.count }}
                </span>
              </button>
            </div>

            <div class="request-results-list">
              <div
                v-for="(r, i) in filteredResults" :key="i"
                class="req-result-row"
                :class="[rowStatusClass(r), { active: selectedResult === r }]"
                @click="selectResult(r)"
              >
                <span class="req-result-icon">{{ resultIcon(r) }}</span>
                <div class="req-result-info">
                  <div class="req-result-name">{{ r.request_name || 'Request' }}</div>
                  <div class="req-result-meta">
                    <span class="rr-status" :class="statusClass(r.status_code)">{{ r.status_code || 'ERR' }}</span>
                    <span class="rr-method" :class="methodClass(r.method)">{{ r.method }}</span>
                    <span class="rr-time">{{ r.duration_ms }}ms</span>
                    <span v-if="r.tests?.assertions" class="rr-tests" :class="r.tests.assertions.failed > 0 ? 'rr-fail' : 'rr-pass'">
                      {{ r.tests.assertions.passed }}/{{ r.tests.assertions.passed + r.tests.assertions.failed }}
                    </span>
                    <span v-if="r.error" class="rr-error-badge">ERR</span>
                  </div>
                </div>
              </div>

              <div v-if="running && filteredResults.length < totalRequests" class="req-result-pending">
                <span class="pending-spinner">⟳</span>
                <span>Running {{ totalRequests - filteredResults.length }} more...</span>
              </div>
            </div>
          </div>

          <!-- RIGHT: detail panel -->
          <div class="runner-right">
            <div v-if="!selectedResult" class="runner-right-empty">
              <div class="empty-icon">←</div>
              <p>Select a request to see details</p>
            </div>

            <template v-else>
              <!-- Request title -->
              <div class="rr-detail-header">
                <span class="rr-detail-icon">{{ resultIcon(selectedResult) }}</span>
                <div class="rr-detail-title">
                  <span class="rr-detail-name">{{ selectedResult.request_name }}</span>
                  <span class="rr-detail-url">{{ selectedResult.resolved_url || selectedResult.url }}</span>
                </div>
                <div class="rr-detail-badges">
                  <span class="rr-status" :class="statusClass(selectedResult.status_code)">{{ selectedResult.status_code }}</span>
                  <span class="rr-time">{{ selectedResult.duration_ms }}ms</span>
                  <span v-if="selectedResult.size_bytes">{{ formatSize(selectedResult.size_bytes) }}</span>
                </div>
              </div>

              <!-- Detail tabs -->
              <div class="rr-detail-tabs">
                <button
                  v-for="t in detailTabs(selectedResult)" :key="t.key"
                  class="rr-detail-tab"
                  :class="{ active: activeDetailTab === t.key, 'tab-fail': t.hasFail }"
                  @click="activeDetailTab = t.key"
                >{{ t.label }}</button>
              </div>

              <!-- TESTS tab -->
              <div v-if="activeDetailTab === 'tests'" class="rr-detail-content">
                <div v-if="!selectedResult.tests" class="detail-empty">
                  No test script for this request
                </div>
                <template v-else>
                  <!-- Error -->
                  <div v-if="selectedResult.tests.error" class="test-script-error">
                    ⚠ Script error: {{ selectedResult.tests.error }}
                  </div>
                  <!-- Assertions -->
                  <div
                    v-for="(a, ai) in (selectedResult.tests.assertions?.tests || [])"
                    :key="ai"
                    class="assertion-row"
                    :class="a.passed ? 'a-pass' : 'a-fail'"
                  >
                    <span class="a-icon">{{ a.passed ? '✓' : '✗' }}</span>
                    <span class="a-name">{{ a.name }}</span>
                  </div>
                  <div v-if="!selectedResult.tests.assertions?.tests?.length" class="detail-empty">
                    Test script ran but produced no assertions
                  </div>
                </template>
              </div>

              <!-- RESPONSE tab -->
              <div v-if="activeDetailTab === 'response'" class="rr-detail-content">
                <div v-if="selectedResult.error" class="detail-error">
                  Connection error: {{ selectedResult.error }}
                </div>
                <template v-else>
                  <div class="response-toolbar">
                    <button class="rv-toggle" :class="{ active: prettyResponse }" @click="prettyResponse = !prettyResponse">Pretty</button>
                    <button class="rv-toggle" @click="copyResponse">{{ responseCopied ? 'Copied!' : 'Copy' }}</button>
                  </div>
                  <pre class="rr-code">{{ formattedResponseBody }}</pre>
                </template>
              </div>

              <!-- HEADERS tab -->
              <div v-if="activeDetailTab === 'headers'" class="rr-detail-content">
                <div class="headers-section-title">Response Headers</div>
                <table class="rr-headers-table">
                  <tbody>
                    <tr v-for="(val, key) in (selectedResult.response_headers || {})" :key="key">
                      <td class="rh-key">{{ key }}</td>
                      <td class="rh-val">{{ val }}</td>
                    </tr>
                    <tr v-if="!Object.keys(selectedResult.response_headers || {}).length">
                      <td colspan="2" class="detail-empty">No headers</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- CONSOLE tab -->
              <div v-if="activeDetailTab === 'console'" class="rr-detail-content">
                <div v-if="!consoleLines.length" class="detail-empty">
                  No console output
                </div>
                <div v-else class="console-output">
                  <div v-for="(line, li) in consoleLines" :key="li" class="console-line">
                    <span class="console-prefix">[log]</span>
                    <span class="console-text">{{ line }}</span>
                  </div>
                </div>
              </div>

              <!-- REQUEST tab -->
              <div v-if="activeDetailTab === 'request'" class="rr-detail-content">
                <div class="headers-section-title">Sent to</div>
                <div class="rr-sent-url">{{ selectedResult.resolved_url || selectedResult.url }}</div>
                <div class="headers-section-title" style="margin-top:12px">Request Headers</div>
                <table class="rr-headers-table">
                  <tbody>
                    <tr v-for="(val, key) in (selectedResult.request_headers || {})" :key="key">
                      <td class="rh-key">{{ key }}</td>
                      <td class="rh-val">{{ val }}</td>
                    </tr>
                  </tbody>
                </table>
                <template v-if="selectedResult.request_body">
                  <div class="headers-section-title" style="margin-top:12px">Request Body</div>
                  <pre class="rr-code">{{ selectedResult.request_body }}</pre>
                </template>
              </div>

            </template>
          </div>
        </div>

        <!-- ── Actions ────────────────────────────────────────── -->
        <div class="runner-actions">
          <template v-if="!running && !done">
            <button class="btn btn-primary" @click="runAll" :disabled="!selectedCount">
              ▶ Run ({{ selectedCount }})
            </button>
          </template>
          <template v-else-if="running">
            <button class="btn btn-danger" @click="stopRun">■ Stop</button>
          </template>
          <template v-else>
            <button class="btn btn-secondary" @click="exportResults">↓ Export CSV</button>
            <button
              v-if="failedResults.length"
              class="btn btn-warn"
              @click="rerunFailed"
            >↺ Re-run Failed ({{ failedResults.length }})</button>
            <button class="btn btn-primary" @click="reset">▶ Run Again</button>
          </template>
        </div>

      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { pechkinApi } from '@/services/api'
import { usePechkinStore } from '@/stores/pechkin'

const props = defineProps({
  collectionId: { type: String, required: true },
  collectionName: { type: String, default: '' },
  requests: { type: Array, default: () => [] },
})
const emit = defineEmits(['close'])
const store = usePechkinStore()

// ── State ──────────────────────────────────────────────────
const running = ref(false)
const done = ref(false)
const stopped = ref(false)
const results = ref([])
const completed = ref(0)
const completedCount = ref(0)
const totalTime = ref(0)
const showSettings = ref(false)
const activeFilter = ref('all')
const selectedResult = ref(null)
const activeDetailTab = ref('tests')
const prettyResponse = ref(true)
const responseCopied = ref(false)
const options = reactive({ delayMs: 0, stopOnError: false, iterations: 1 })
const orderedRequests = ref([])
const dragIdx = ref(-1)
const dragOverIdx = ref(-1)

// ── Computed ───────────────────────────────────────────────
const selectedCount = computed(() => orderedRequests.value.filter(r => r.selected).length)
const totalRequests = computed(() => selectedCount.value * options.iterations)
const progressPct = computed(() =>
  totalRequests.value ? (results.value.length / totalRequests.value) * 100 : 0
)

const totalPassed = computed(() =>
  results.value.reduce((s, r) => s + (r.tests?.assertions?.passed || 0), 0)
)
const totalFailed = computed(() =>
  results.value.reduce((s, r) => s + (r.tests?.assertions?.failed || 0), 0)
)
const passRate = computed(() => {
  const total = totalPassed.value + totalFailed.value
  return total ? Math.round((totalPassed.value / total) * 100) : 100
})
const passRateCls = computed(() =>
  passRate.value >= 80 ? 'sb-pass' : passRate.value >= 50 ? 'sb-warn' : 'sb-fail'
)
const summaryBarClass = computed(() => {
  if (running.value) return 'bar-running'
  if (done.value) return totalFailed.value > 0 ? 'bar-fail' : 'bar-pass'
  return ''
})

const filters = computed(() => [
  { key: 'all', label: 'All', count: results.value.length, colorClass: '' },
  {
    key: 'passed',
    label: 'Passed',
    count: results.value.filter(r => isResultPassed(r)).length,
    colorClass: 'fc-pass'
  },
  {
    key: 'failed',
    label: 'Failed',
    count: results.value.filter(r => !isResultPassed(r)).length,
    colorClass: 'fc-fail'
  },
])

const filteredResults = computed(() => {
  if (activeFilter.value === 'passed') return results.value.filter(r => isResultPassed(r))
  if (activeFilter.value === 'failed') return results.value.filter(r => !isResultPassed(r))
  return results.value
})

const failedResults = computed(() => results.value.filter(r => !isResultPassed(r)))

const formattedResponseBody = computed(() => {
  const body = selectedResult.value?.response_body
  if (!body) return ''
  if (!prettyResponse.value) return body
  try {
    return JSON.stringify(JSON.parse(body), null, 2)
  } catch { return body }
})

const consoleLines = computed(() => {
  const r = selectedResult.value
  if (!r) return []
  const lines = []
  if (r.tests?.output?.length) lines.push(...r.tests.output)
  if (r.pre_output?.length) lines.push(...r.pre_output)
  return lines
})

// ── Helpers ────────────────────────────────────────────────
function isResultPassed(r) {
  if (r.error) return false
  if (r.status_code >= 400) return false
  if ((r.tests?.assertions?.failed || 0) > 0) return false
  return true
}

function resultIcon(r) {
  if (!r) return '○'
  if (r.error || r.status_code >= 400 || (r.tests?.assertions?.failed || 0) > 0) return '✗'
  return '✓'
}

function rowStatusClass(r) {
  if (!r) return ''
  if (r.error || r.status_code >= 400) return 'row-error'
  if ((r.tests?.assertions?.failed || 0) > 0) return 'row-fail'
  return 'row-pass'
}

function statusClass(code) {
  if (!code) return 'status-err'
  if (code < 300) return 'status-ok'
  if (code < 400) return 'status-redirect'
  return 'status-err'
}

function methodClass(m) {
  const map = { GET: 'method-get', POST: 'method-post', PUT: 'method-put', PATCH: 'method-patch', DELETE: 'method-delete' }
  return map[m?.toUpperCase()] || 'method-get'
}

function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + 'B'
  return (bytes / 1024).toFixed(1) + 'KB'
}

function detailTabs(r) {
  const tabs = []
  const testsFailed = r.tests?.assertions?.failed > 0
  const testsExist = r.tests !== null
  tabs.push({
    key: 'tests',
    label: testsExist
      ? `Tests (${r.tests?.assertions?.passed || 0}/${(r.tests?.assertions?.passed || 0) + (r.tests?.assertions?.failed || 0)})`
      : 'Tests',
    hasFail: testsFailed
  })
  tabs.push({ key: 'response', label: 'Response', hasFail: false })
  tabs.push({ key: 'headers', label: 'Headers', hasFail: false })
  const hasConsole = (r.tests?.output?.length || 0) + (r.pre_output?.length || 0) > 0
  tabs.push({ key: 'console', label: hasConsole ? 'Console ●' : 'Console', hasFail: false })
  tabs.push({ key: 'request', label: 'Request', hasFail: false })
  return tabs
}

function selectResult(r) {
  selectedResult.value = r
  // Auto-select first relevant tab
  if (r.tests) {
    activeDetailTab.value = 'tests'
  } else {
    activeDetailTab.value = 'response'
  }
}

function copyResponse() {
  navigator.clipboard.writeText(formattedResponseBody.value)
  responseCopied.value = true
  setTimeout(() => { responseCopied.value = false }, 2000)
}

// ── Drag & Drop ────────────────────────────────────────────
function onDragStart(idx, e) { dragIdx.value = idx; e.dataTransfer.effectAllowed = 'move' }
function onDragOver(idx) { dragOverIdx.value = idx }
function onDrop(idx) {
  const arr = [...orderedRequests.value]
  const [moved] = arr.splice(dragIdx.value, 1)
  arr.splice(idx, 0, moved)
  orderedRequests.value = arr
  dragOverIdx.value = -1
}
function selectAll() {
  const allSelected = orderedRequests.value.every(r => r.selected)
  orderedRequests.value.forEach(r => { r.selected = !allSelected })
}

// ── Run ────────────────────────────────────────────────────
async function runAll(onlyIds = null) {
  running.value = true
  done.value = false
  stopped.value = false
  results.value = []
  completed.value = 0
  completedCount.value = 0
  totalTime.value = 0
  selectedResult.value = null

  const selectedIds = onlyIds || orderedRequests.value.filter(r => r.selected).map(r => r.id)
  try {
    const resp = await pechkinApi.runCollection({
      collection_id: props.collectionId,
      request_ids: selectedIds,
      delay_ms: options.delayMs,
      stop_on_error: options.stopOnError,
      iterations: options.iterations,
      variables: store.resolvedVariables,
    })
    results.value = resp.data.results || resp.data
    completedCount.value = results.value.length
    totalTime.value = resp.data.total_time_ms
      || results.value.reduce((s, r) => s + (r.duration_ms || 0), 0)

    // Auto-select first failed or first result
    if (results.value.length) {
      const firstFailed = results.value.find(r => !isResultPassed(r))
      selectResult(firstFailed || results.value[0])
    }
  } catch (e) {
    console.error('Collection run failed:', e)
  } finally {
    running.value = false
    done.value = true
  }
}

function stopRun() { stopped.value = true }
function reset() { done.value = false; results.value = []; selectedResult.value = null }
function rerunFailed() { runAll(failedResults.value.map(r => r.request_id)) }

function exportResults() {
  const rows = [
    'Name,Method,URL,Status,Duration(ms),Tests Passed,Tests Failed,Error',
    ...results.value.map(r => [
      `"${(r.request_name || '').replace(/"/g,'""')}"`,
      r.method || '',
      `"${(r.resolved_url || r.url || '').replace(/"/g,'""')}"`,
      r.status_code || '',
      r.duration_ms || 0,
      r.tests?.assertions?.passed || 0,
      r.tests?.assertions?.failed || 0,
      `"${(r.error || '').replace(/"/g,'""')}"`,
    ].join(','))
  ]
  const blob = new Blob([rows.join('\n')], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.collectionName.replace(/[^a-zA-Z0-9]/g,'_')}-run.csv`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(() => {
  orderedRequests.value = props.requests.map(r => ({ ...r, selected: true }))
})
</script>

<style scoped>
/* ── Overlay & Modal ─────────────────────────────────── */
.runner-overlay {
  position: fixed; inset: 0; z-index: 9000;
  background: rgba(0,0,0,0.65);
  display: flex; align-items: center; justify-content: center;
}
.runner-modal {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: 0 24px 80px rgba(0,0,0,0.4);
  width: min(1100px, 95vw);
  height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ── Header ──────────────────────────────────────────── */
.runner-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 20px; border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}
.runner-header-left { display: flex; align-items: center; gap: 10px; }
.runner-title { font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 0; }
.runner-col-name {
  font-size: 13px; color: var(--text-secondary);
  padding: 2px 8px; background: var(--bg-tertiary); border-radius: 4px;
}
.runner-header-right { display: flex; align-items: center; gap: 8px; }
.btn-settings {
  padding: 5px 12px; font-size: 12px; background: var(--bg-tertiary);
  border: 1px solid var(--border-color); border-radius: 6px;
  color: var(--text-secondary); cursor: pointer; transition: all 0.15s;
}
.btn-settings:hover, .btn-settings.active { color: var(--accent); border-color: var(--accent); }
.runner-close {
  background: none; border: none; font-size: 20px;
  color: var(--text-secondary); cursor: pointer; line-height: 1; padding: 4px;
}
.runner-close:hover { color: var(--text-primary); }

/* ── Settings Panel ──────────────────────────────────── */
.runner-settings-panel {
  padding: 12px 20px; border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary); flex-shrink: 0;
  max-height: 260px; overflow-y: auto;
}
.settings-row { display: flex; gap: 16px; align-items: flex-end; margin-bottom: 12px; flex-wrap: wrap; }
.setting-label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-secondary); }
.setting-input { width: 90px; padding: 5px 8px; border: 1px solid var(--border-color); border-radius: 5px; background: var(--bg-primary); color: var(--text-primary); font-size: 12px; }
.setting-check { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); cursor: pointer; padding-bottom: 4px; }
.request-list { border: 1px solid var(--border-color); border-radius: 6px; overflow: hidden; }
.request-list-header { display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; font-size: 11px; font-weight: 600; color: var(--text-secondary); background: var(--bg-tertiary); text-transform: uppercase; letter-spacing: 0.5px; }
.btn-select-all { background: none; border: none; color: var(--accent); font-size: 11px; cursor: pointer; }
.request-item { display: flex; align-items: center; gap: 6px; padding: 5px 10px; border-top: 1px solid var(--border-color); font-size: 12px; color: var(--text-primary); cursor: grab; }
.request-item:hover { background: var(--bg-tertiary); }
.request-item.drag-over { border-top: 2px solid var(--accent); }
.drag-handle { color: var(--text-secondary); user-select: none; }
.req-check { accent-color: var(--accent); }
.req-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty-msg { padding: 12px; text-align: center; color: var(--text-secondary); font-size: 12px; }

/* ── Summary Bar ─────────────────────────────────────── */
.runner-summary-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 20px; border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary); flex-shrink: 0; min-height: 36px;
}
.summary-bar-left { display: flex; align-items: center; gap: 6px; font-size: 12px; flex-wrap: wrap; }
.sb-item { font-weight: 500; }
.sb-sep { color: var(--text-secondary); }
.sb-accent { color: var(--accent); }
.sb-pass { color: var(--success); }
.sb-fail { color: var(--error); }
.sb-warn { color: var(--warning); }
.sb-neutral { color: var(--text-secondary); }
.sb-progress-wrap { width: 140px; height: 4px; background: var(--bg-tertiary); border-radius: 2px; overflow: hidden; }
.sb-progress-bar { height: 100%; background: var(--accent); border-radius: 2px; transition: width 0.3s; }

/* ── Body split ──────────────────────────────────────── */
.runner-body {
  display: grid;
  grid-template-columns: 320px 1fr;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* ── Left panel ──────────────────────────────────────── */
.runner-left {
  border-right: 1px solid var(--border-color);
  display: flex; flex-direction: column; overflow: hidden;
  background: var(--bg-secondary);
}
.runner-left-filters {
  display: flex; gap: 0; padding: 8px 12px 0;
  border-bottom: 1px solid var(--border-color); flex-shrink: 0;
}
.filter-tab {
  padding: 5px 12px; background: none; border: none; border-bottom: 2px solid transparent;
  color: var(--text-secondary); font-size: 11px; font-weight: 600; cursor: pointer;
  text-transform: uppercase; letter-spacing: 0.4px; display: flex; align-items: center; gap: 4px;
}
.filter-tab:hover { color: var(--text-primary); }
.filter-tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.filter-count { font-size: 10px; padding: 1px 5px; border-radius: 8px; background: var(--bg-tertiary); }
.fc-pass { color: var(--success); }
.fc-fail { color: var(--error); }

.request-results-list { flex: 1; overflow-y: auto; }

.req-result-row {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 8px 12px; cursor: pointer;
  border-bottom: 1px solid var(--border-color);
  transition: background 0.1s;
}
.req-result-row:hover { background: var(--bg-tertiary); }
.req-result-row.active { background: var(--accent-muted); }
.req-result-row.row-pass .req-result-icon { color: var(--success); }
.req-result-row.row-fail .req-result-icon,
.req-result-row.row-error .req-result-icon { color: var(--error); }
.req-result-icon { font-size: 14px; font-weight: 700; flex-shrink: 0; margin-top: 1px; }

.req-result-info { flex: 1; min-width: 0; }
.req-result-name {
  font-size: 12px; font-weight: 500; color: var(--text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  margin-bottom: 3px;
}
.req-result-meta { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }
.rr-status { font-size: 10px; font-weight: 700; padding: 1px 5px; border-radius: 3px; }
.status-ok { color: var(--success); background: rgba(16,185,129,0.12); }
.status-redirect { color: var(--warning); background: rgba(245,158,11,0.12); }
.status-err { color: var(--error); background: rgba(239,68,68,0.12); }
.rr-method { font-size: 9px; font-weight: 700; padding: 1px 4px; border-radius: 3px; text-transform: uppercase; }
.method-get { color: var(--success); background: rgba(16,185,129,0.12); }
.method-post { color: var(--accent); background: var(--accent-muted); }
.method-put, .method-patch { color: var(--warning); background: rgba(245,158,11,0.12); }
.method-delete { color: var(--error); background: rgba(239,68,68,0.12); }
.rr-time { font-size: 10px; color: var(--text-secondary); }
.rr-tests { font-size: 10px; font-weight: 600; padding: 1px 5px; border-radius: 8px; }
.rr-pass { color: var(--success); background: rgba(16,185,129,0.1); }
.rr-fail { color: var(--error); background: rgba(239,68,68,0.1); }
.rr-error-badge { font-size: 9px; padding: 1px 4px; background: rgba(239,68,68,0.15); color: var(--error); border-radius: 3px; font-weight: 700; }
.req-result-pending { padding: 12px; text-align: center; font-size: 12px; color: var(--text-secondary); display: flex; align-items: center; justify-content: center; gap: 6px; }
.pending-spinner { animation: spin 1s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Right panel ─────────────────────────────────────── */
.runner-right {
  display: flex; flex-direction: column; overflow: hidden;
  background: var(--bg-card);
}
.runner-right-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 100%; color: var(--text-secondary);
}
.empty-icon { font-size: 32px; margin-bottom: 8px; }
.runner-right-empty p { font-size: 13px; }

.rr-detail-header {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 16px; border-bottom: 1px solid var(--border-color);
  flex-shrink: 0; background: var(--bg-secondary);
}
.rr-detail-icon { font-size: 16px; font-weight: 700; flex-shrink: 0; }
.row-pass .rr-detail-icon, .runner-right .rr-detail-icon { color: var(--success); }
.rr-detail-title { flex: 1; min-width: 0; }
.rr-detail-name { font-size: 13px; font-weight: 600; color: var(--text-primary); display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rr-detail-url { font-family: monospace; font-size: 11px; color: var(--text-secondary); display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rr-detail-badges { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.rr-time { font-size: 11px; color: var(--text-secondary); }

.rr-detail-tabs {
  display: flex; gap: 0; padding: 0 16px;
  border-bottom: 1px solid var(--border-color); flex-shrink: 0;
  background: var(--bg-secondary);
}
.rr-detail-tab {
  padding: 8px 14px; background: none; border: none; border-bottom: 2px solid transparent;
  color: var(--text-secondary); font-size: 12px; cursor: pointer; font-weight: 500; white-space: nowrap;
}
.rr-detail-tab:hover { color: var(--text-primary); }
.rr-detail-tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.rr-detail-tab.tab-fail { color: var(--error); }
.rr-detail-tab.tab-fail.active { border-bottom-color: var(--error); }

.rr-detail-content {
  flex: 1; overflow-y: auto; padding: 14px 16px;
}

/* Assertions */
.assertion-row {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 6px 8px; border-radius: 5px; margin-bottom: 3px; font-size: 12px;
}
.a-pass { background: rgba(16,185,129,0.07); }
.a-fail { background: rgba(239,68,68,0.07); }
.a-icon { font-size: 13px; font-weight: 700; flex-shrink: 0; }
.a-pass .a-icon { color: var(--success); }
.a-fail .a-icon { color: var(--error); }
.a-name { color: var(--text-primary); line-height: 1.4; }
.test-script-error {
  padding: 8px 10px; background: rgba(239,68,68,0.08);
  border: 1px solid rgba(239,68,68,0.25); border-radius: 6px;
  font-size: 12px; color: var(--error); margin-bottom: 10px;
}
.detail-empty { color: var(--text-secondary); font-size: 12px; font-style: italic; text-align: center; padding: 20px; }
.detail-error { color: var(--error); font-size: 12px; padding: 8px 0; }

/* Response */
.response-toolbar { display: flex; gap: 6px; margin-bottom: 8px; }
.rv-toggle { padding: 3px 10px; background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-secondary); font-size: 11px; cursor: pointer; }
.rv-toggle:hover { color: var(--text-primary); }
.rv-toggle.active { background: var(--accent-muted); color: var(--accent); border-color: var(--accent); }
.rr-code {
  margin: 0; padding: 12px; background: var(--bg-primary);
  border: 1px solid var(--border-color); border-radius: 6px;
  color: var(--text-primary); font-family: 'JetBrains Mono', monospace;
  font-size: 12px; line-height: 1.5; white-space: pre; overflow-x: auto;
  max-height: 300px; overflow-y: auto;
}

/* Headers table */
.headers-section-title { font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--text-secondary); letter-spacing: 0.5px; margin-bottom: 6px; }
.rr-headers-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.rr-headers-table td { padding: 4px 8px; border-bottom: 1px solid var(--border-color); }
.rh-key { font-weight: 500; color: var(--text-secondary); white-space: nowrap; width: 40%; }
.rh-val { color: var(--text-primary); word-break: break-all; font-family: monospace; font-size: 11px; }

/* Console */
.console-output { background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; padding: 10px 12px; }
.console-line { display: flex; gap: 8px; padding: 2px 0; font-size: 12px; font-family: monospace; line-height: 1.6; }
.console-prefix { color: var(--accent); font-weight: 600; flex-shrink: 0; }
.console-text { color: var(--text-primary); }

/* Request */
.rr-sent-url { font-family: monospace; font-size: 12px; color: var(--text-primary); padding: 6px 8px; background: var(--bg-secondary); border-radius: 4px; word-break: break-all; }

/* ── Actions ─────────────────────────────────────────── */
.runner-actions {
  display: flex; gap: 10px; padding: 12px 20px;
  border-top: 1px solid var(--border-color); justify-content: flex-end; flex-shrink: 0;
  background: var(--bg-secondary);
}
.btn { padding: 7px 18px; border: none; border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.15s; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: var(--accent); color: #fff; }
.btn-primary:hover:not(:disabled) { opacity: 0.85; }
.btn-danger { background: var(--error); color: #fff; }
.btn-danger:hover { opacity: 0.9; }
.btn-warn { background: rgba(245,158,11,0.15); color: var(--warning); border: 1px solid rgba(245,158,11,0.3); }
.btn-warn:hover { background: rgba(245,158,11,0.25); }
.btn-secondary { background: var(--bg-tertiary); color: var(--text-primary); border: 1px solid var(--border-color); }
.btn-secondary:hover { background: var(--bg-secondary); }
</style>
