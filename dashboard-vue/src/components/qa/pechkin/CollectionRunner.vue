<template>
  <Teleport to="body">
    <div class="runner-overlay" @click.self="$emit('close')">
      <div class="runner-modal">

        <!-- Header -->
        <div class="runner-header">
          <div class="runner-header-left">
            <span class="runner-title">{{ collectionName }}</span>
            <span v-if="done" class="runner-run-badge" :class="totalFailed > 0 ? 'badge-error' : 'badge-ok'">
              {{ totalFailed > 0 ? 'ERROR' : 'PASS' }}
            </span>
          </div>
          <button class="runner-close" @click="$emit('close')">&times;</button>
        </div>

        <!-- Pre-run settings -->
        <div v-if="!running && !done" class="runner-setup">
          <div class="setup-row">
            <label class="setup-label">
              Delay (ms)
              <input v-model.number="options.delayMs" type="number" min="0" step="100" class="setup-input" />
            </label>
            <label class="setup-label">
              Iterations
              <input v-model.number="options.iterations" type="number" min="1" max="100" class="setup-input" />
            </label>
            <label class="setup-check">
              <input v-model="options.stopOnError" type="checkbox" />
              Stop on error
            </label>
          </div>

          <div class="req-checklist">
            <div class="req-checklist-header">
              <span>Requests</span>
              <button class="btn-link" @click="toggleAll">
                {{ allSelected ? 'Deselect All' : 'Select All' }}
              </button>
            </div>
            <div
              v-for="(req, idx) in orderedRequests" :key="req.id"
              class="req-check-row"
              draggable="true"
              @dragstart="onDragStart(idx, $event)"
              @dragover.prevent="onDragOver(idx)"
              @drop="onDrop(idx)"
              @dragend="dragIdx = -1"
              :class="{ 'drag-over': dragOverIdx === idx }"
            >
              <span class="drag-dots">⠿</span>
              <input type="checkbox" v-model="req.selected" class="req-checkbox" />
              <span class="req-method-badge" :class="methodClass(req.method)">{{ req.method }}</span>
              <span class="req-check-name">{{ req.name || 'Untitled' }}</span>
            </div>
            <div v-if="!orderedRequests.length" class="setup-empty">No requests</div>
          </div>
        </div>

        <!-- Running: progress -->
        <div v-if="running" class="runner-progress-wrap">
          <div class="runner-progress-bar" :style="{ width: progressPct + '%' }"></div>
          <div class="runner-progress-text">
            Running {{ results.length }} / {{ totalRequests }}...
          </div>
        </div>

        <!-- Stats bar (after run starts) -->
        <div v-if="running || done" class="runner-stats-bar">
          <div class="stat-block">
            <div class="stat-label">Duration</div>
            <div class="stat-value">{{ totalTime }}ms</div>
          </div>
          <div class="stat-block">
            <div class="stat-label">All tests</div>
            <div class="stat-value">{{ totalPassed + totalFailed }}</div>
          </div>
          <div class="stat-block">
            <div class="stat-label">Passed</div>
            <div class="stat-value stat-pass">{{ totalPassed }}</div>
          </div>
          <div class="stat-block">
            <div class="stat-label">Failed</div>
            <div class="stat-value stat-fail">{{ totalFailed }}</div>
          </div>
          <div class="stat-block">
            <div class="stat-label">Avg. Resp.</div>
            <div class="stat-value">{{ avgTime }}ms</div>
          </div>
        </div>

        <!-- Filter tabs -->
        <div v-if="results.length" class="runner-filter-tabs">
          <button
            v-for="f in filterTabs" :key="f.key"
            class="filter-tab"
            :class="{ active: activeFilter === f.key }"
            @click="activeFilter = f.key"
          >
            {{ f.label }}
            <span class="filter-tab-count" :class="f.cls">{{ f.count }}</span>
          </button>
        </div>

        <!-- Results list -->
        <div v-if="running || done" class="runner-results-scroll">

          <div v-for="(r, i) in filteredResults" :key="i">
            <!-- Request row -->
            <div
              class="result-request-row"
              :class="rowClass(r)"
              @click="toggleExpand(i)"
            >
              <span class="expand-arrow">{{ expandedRows.has(i) ? '▾' : '▸' }}</span>
              <span class="rr-method" :class="methodClass(r.method)">{{ r.method || 'GET' }}</span>
              <div class="rr-name-url">
                <span class="rr-name">{{ r.request_name }}</span>
                <span class="rr-url">{{ r.resolved_url || r.url || '' }}</span>
              </div>
              <div class="rr-right">
                <span class="rr-status" :class="statusBadgeClass(r.status_code)">
                  {{ r.status_code || 'ERR' }}
                </span>
                <span class="rr-time">{{ r.duration_ms }} ms</span>
                <span v-if="r.size_bytes" class="rr-size">{{ formatSize(r.size_bytes) }}</span>
                <!-- Test count badges -->
                <template v-if="r.tests?.assertions">
                  <span v-if="r.tests.assertions.passed" class="rr-badge rr-pass">
                    {{ r.tests.assertions.passed }}
                  </span>
                  <span v-if="r.tests.assertions.failed" class="rr-badge rr-fail">
                    {{ r.tests.assertions.failed }}
                  </span>
                </template>
                <span v-if="r.error" class="rr-badge rr-fail">ERR</span>
              </div>
            </div>

            <!-- Expanded: assertions inline -->
            <div v-if="expandedRows.has(i)" class="result-assertions">

              <!-- HTTP error -->
              <div v-if="r.error" class="assertion-row assertion-fail">
                <span class="assertion-badge badge-fail">FAIL</span>
                <span class="assertion-text">Connection error: {{ r.error }}</span>
              </div>

              <!-- No test script -->
              <div v-else-if="!r.tests" class="assertion-no-tests">
                No tests found
              </div>

              <!-- Script error -->
              <div v-else-if="r.tests.error" class="assertion-row assertion-fail">
                <span class="assertion-badge badge-fail">ERROR</span>
                <span class="assertion-text">{{ r.tests.error }}</span>
              </div>

              <!-- Individual assertions -->
              <template v-else>
                <div
                  v-for="(a, ai) in (r.tests.assertions?.tests || [])"
                  :key="ai"
                  class="assertion-row"
                  :class="a.passed ? 'assertion-pass' : 'assertion-fail'"
                >
                  <span class="assertion-badge" :class="a.passed ? 'badge-pass' : 'badge-fail'">
                    {{ a.passed ? 'PASS' : 'FAIL' }}
                  </span>
                  <span class="assertion-text">{{ a.name }}</span>
                </div>

                <div v-if="!r.tests.assertions?.tests?.length" class="assertion-no-tests">
                  Script ran but no assertions found
                </div>
              </template>

              <!-- Console output -->
              <div
                v-if="r.tests?.output?.length"
                class="assertion-console"
              >
                <div class="console-header">Console</div>
                <div
                  v-for="(line, li) in r.tests.output" :key="li"
                  class="console-line"
                >{{ line }}</div>
              </div>

              <!-- Response preview (collapsed by default) -->
              <div class="assertion-response">
                <button
                  class="response-toggle"
                  @click.stop="toggleResponse(i)"
                >
                  {{ openResponses.has(i) ? '▾ Hide Response' : '▸ Show Response' }}
                  <span class="response-status" :class="statusBadgeClass(r.status_code)">
                    {{ r.status_code }}
                  </span>
                </button>
                <div v-if="openResponses.has(i)" class="response-body-wrap">
                  <pre class="response-body">{{ prettyBody(r.response_body) }}</pre>
                </div>
              </div>

            </div>
          </div>

          <!-- Running spinner -->
          <div v-if="running" class="running-indicator">
            <span class="running-spinner">⟳</span> Running...
          </div>
        </div>

        <!-- Actions -->
        <div class="runner-actions">
          <template v-if="!running && !done">
            <button class="btn btn-primary" @click="runAll" :disabled="!selectedCount">
              ▶ Run {{ selectedCount > 0 ? `(${selectedCount})` : '' }}
            </button>
          </template>
          <template v-else-if="running">
            <button class="btn btn-danger" @click="stopped = true">■ Stop</button>
          </template>
          <template v-else>
            <button class="btn btn-secondary" @click="exportCsv">↓ Export CSV</button>
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
const running   = ref(false)
const done      = ref(false)
const stopped   = ref(false)
const results   = ref([])
const totalTime = ref(0)
const activeFilter  = ref('all')
const expandedRows  = ref(new Set())
const openResponses = ref(new Set())
const options   = reactive({ delayMs: 0, stopOnError: false, iterations: 1 })
const orderedRequests = ref([])
const dragIdx     = ref(-1)
const dragOverIdx = ref(-1)

// ── Computed ───────────────────────────────────────────────
const selectedCount = computed(() => orderedRequests.value.filter(r => r.selected).length)
const allSelected   = computed(() => orderedRequests.value.every(r => r.selected))
const totalRequests = computed(() => selectedCount.value * options.iterations)
const progressPct   = computed(() =>
  totalRequests.value ? (results.value.length / totalRequests.value) * 100 : 0
)

const totalPassed = computed(() =>
  results.value.reduce((s, r) => s + (r.tests?.assertions?.passed || 0), 0)
)
const totalFailed = computed(() =>
  results.value.reduce((s, r) => s + (r.tests?.assertions?.failed || 0), 0)
)
const avgTime = computed(() => {
  if (!results.value.length) return 0
  const total = results.value.reduce((s, r) => s + (r.duration_ms || 0), 0)
  return Math.round(total / results.value.length)
})

const failedResults = computed(() =>
  results.value.filter(r =>
    r.error || r.status_code >= 400 || (r.tests?.assertions?.failed || 0) > 0
  )
)

const filterTabs = computed(() => [
  {
    key: 'all',
    label: 'All Tests',
    count: results.value.length,
    cls: '',
  },
  {
    key: 'passed',
    label: 'Passed',
    count: results.value.filter(r => isPass(r)).length,
    cls: 'cnt-pass',
  },
  {
    key: 'failed',
    label: 'Failed',
    count: failedResults.value.length,
    cls: 'cnt-fail',
  },
])

const filteredResults = computed(() => {
  if (activeFilter.value === 'passed') return results.value.filter(r => isPass(r))
  if (activeFilter.value === 'failed') return failedResults.value
  return results.value
})

// ── Helpers ────────────────────────────────────────────────
function isPass(r) {
  return !r.error && r.status_code < 400 && (r.tests?.assertions?.failed || 0) === 0
}

function rowClass(r) {
  if (r.error || r.status_code >= 400) return 'row-error'
  if ((r.tests?.assertions?.failed || 0) > 0) return 'row-fail'
  return 'row-pass'
}

function statusBadgeClass(code) {
  if (!code) return 'status-err'
  if (code < 300) return 'status-ok'
  if (code < 400) return 'status-redirect'
  return 'status-err'
}

function methodClass(m) {
  const map = { GET: 'method-get', POST: 'method-post', PUT: 'method-put', PATCH: 'method-patch', DELETE: 'method-delete' }
  return map[(m || 'GET').toUpperCase()] || 'method-get'
}

function formatSize(b) {
  if (!b) return ''
  return b < 1024 ? b + ' B' : (b / 1024).toFixed(1) + ' KB'
}

function prettyBody(body) {
  if (!body) return 'Empty response'
  try { return JSON.stringify(JSON.parse(body), null, 2) }
  catch { return body }
}

function toggleExpand(idx) {
  const s = new Set(expandedRows.value)
  s.has(idx) ? s.delete(idx) : s.add(idx)
  expandedRows.value = s
}

function toggleResponse(idx) {
  const s = new Set(openResponses.value)
  s.has(idx) ? s.delete(idx) : s.add(idx)
  openResponses.value = s
}

function toggleAll() {
  const val = !allSelected.value
  orderedRequests.value.forEach(r => { r.selected = val })
}

// ── Drag ───────────────────────────────────────────────────
function onDragStart(idx, e) { dragIdx.value = idx; e.dataTransfer.effectAllowed = 'move' }
function onDragOver(idx) { dragOverIdx.value = idx }
function onDrop(idx) {
  const arr = [...orderedRequests.value]
  const [moved] = arr.splice(dragIdx.value, 1)
  arr.splice(idx, 0, moved)
  orderedRequests.value = arr
  dragOverIdx.value = -1
}

// ── Run ────────────────────────────────────────────────────
async function runAll(onlyIds = null) {
  running.value = true
  done.value = false
  stopped.value = false
  results.value = []
  totalTime.value = 0
  expandedRows.value = new Set()
  openResponses.value = new Set()

  const selectedIds = onlyIds || orderedRequests.value.filter(r => r.selected).map(r => r.id)
  try {
    const resp = await pechkinApi.runCollection({
      collection_id: props.collectionId,
      request_ids: selectedIds,
      delay_ms: options.delayMs || 0,
      stop_on_error: options.stopOnError,
      iterations: options.iterations || 1,
      variables: store.resolvedVariables,
    })
    results.value = resp.data.results || resp.data
    totalTime.value = resp.data.total_time_ms
      || results.value.reduce((s, r) => s + (r.duration_ms || 0), 0)

    // Auto-expand failed requests
    results.value.forEach((r, i) => {
      if (!isPass(r)) {
        const s = new Set(expandedRows.value)
        s.add(i)
        expandedRows.value = s
      }
    })
  } catch (e) {
    console.error('Collection run failed:', e)
  } finally {
    running.value = false
    done.value = true
  }
}

function reset() {
  done.value = false
  results.value = []
  expandedRows.value = new Set()
  openResponses.value = new Set()
}

function rerunFailed() {
  runAll(failedResults.value.map(r => r.request_id))
}

function exportCsv() {
  const rows = [
    'Iteration,Name,Method,URL,Status,Duration(ms),Tests Passed,Tests Failed,Error',
    ...results.value.map(r => [
      r.iteration || 1,
      `"${(r.request_name || '').replace(/"/g, '""')}"`,
      r.method || '',
      `"${(r.resolved_url || r.url || '').replace(/"/g, '""')}"`,
      r.status_code || '',
      r.duration_ms || 0,
      r.tests?.assertions?.passed || 0,
      r.tests?.assertions?.failed || 0,
      `"${(r.error || '').replace(/"/g, '""')}"`,
    ].join(','))
  ]
  const blob = new Blob([rows.join('\n')], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.collectionName.replace(/[^a-zA-Z0-9]/g, '_')}-run.csv`
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
  background: rgba(0, 0, 0, 0.6);
  display: flex; align-items: center; justify-content: center;
}
.runner-modal {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
  width: min(900px, 95vw);
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ── Header ──────────────────────────────────────────── */
.runner-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}
.runner-header-left { display: flex; align-items: center; gap: 10px; }
.runner-title { font-size: 14px; font-weight: 700; color: var(--text-primary); }
.runner-run-badge {
  font-size: 11px; font-weight: 700; padding: 2px 8px;
  border-radius: 4px; letter-spacing: 0.5px;
}
.badge-ok { background: rgba(16,185,129,0.15); color: var(--success); }
.badge-error { background: rgba(239,68,68,0.15); color: var(--error); }
.runner-close {
  background: none; border: none; font-size: 20px;
  color: var(--text-secondary); cursor: pointer; padding: 4px;
}
.runner-close:hover { color: var(--text-primary); }

/* ── Pre-run Setup ───────────────────────────────────── */
.runner-setup { padding: 14px 20px; overflow-y: auto; flex-shrink: 0; max-height: 320px; }
.setup-row { display: flex; gap: 20px; align-items: flex-end; margin-bottom: 14px; flex-wrap: wrap; }
.setup-label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-secondary); }
.setup-input { width: 80px; padding: 5px 8px; border: 1px solid var(--border-color); border-radius: 5px; background: var(--bg-secondary); color: var(--text-primary); font-size: 12px; }
.setup-check { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); cursor: pointer; padding-bottom: 4px; }
.req-checklist { border: 1px solid var(--border-color); border-radius: 6px; overflow: hidden; }
.req-checklist-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 7px 12px; background: var(--bg-tertiary);
  font-size: 11px; font-weight: 600; color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: 0.5px;
}
.btn-link { background: none; border: none; color: var(--accent); font-size: 11px; cursor: pointer; }
.req-check-row {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 12px; border-top: 1px solid var(--border-color);
  font-size: 13px; color: var(--text-primary); cursor: grab;
}
.req-check-row:hover { background: var(--bg-secondary); }
.req-check-row.drag-over { border-top: 2px solid var(--accent); }
.drag-dots { color: var(--text-secondary); user-select: none; }
.req-checkbox { accent-color: var(--accent); }
.req-check-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.setup-empty { padding: 14px; text-align: center; color: var(--text-secondary); font-size: 12px; }

/* ── Progress bar ────────────────────────────────────── */
.runner-progress-wrap {
  flex-shrink: 0; padding: 0 20px 10px; background: var(--bg-secondary);
}
.runner-progress-bar {
  height: 3px; background: var(--accent); border-radius: 2px;
  transition: width 0.3s; margin-bottom: 4px;
}
.runner-progress-text { font-size: 11px; color: var(--text-secondary); text-align: center; }

/* ── Stats bar ───────────────────────────────────────── */
.runner-stats-bar {
  display: flex; gap: 0;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  flex-shrink: 0;
}
.stat-block {
  flex: 1; padding: 10px 16px; text-align: center;
  border-right: 1px solid var(--border-color);
}
.stat-block:last-child { border-right: none; }
.stat-label { font-size: 11px; color: var(--text-secondary); margin-bottom: 2px; }
.stat-value { font-size: 15px; font-weight: 700; color: var(--text-primary); }
.stat-pass { color: var(--success); }
.stat-fail { color: var(--error); }

/* ── Filter tabs ─────────────────────────────────────── */
.runner-filter-tabs {
  display: flex; gap: 0;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  flex-shrink: 0;
}
.filter-tab {
  padding: 8px 18px; background: none; border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary); font-size: 12px; font-weight: 500;
  cursor: pointer; display: flex; align-items: center; gap: 6px;
}
.filter-tab:hover { color: var(--text-primary); }
.filter-tab.active { color: var(--text-primary); border-bottom-color: var(--accent); }
.filter-tab-count {
  font-size: 11px; font-weight: 700; padding: 1px 6px;
  border-radius: 10px; background: var(--bg-tertiary);
  color: var(--text-secondary);
}
.cnt-pass { color: var(--success); background: rgba(16,185,129,0.1); }
.cnt-fail { color: var(--error); background: rgba(239,68,68,0.1); }

/* ── Results scroll area ─────────────────────────────── */
.runner-results-scroll {
  flex: 1; overflow-y: auto;
  min-height: 0;
}

/* ── Request row ─────────────────────────────────────── */
.result-request-row {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 20px; cursor: pointer;
  border-bottom: 1px solid var(--border-color);
  transition: background 0.1s;
  font-size: 13px;
}
.result-request-row:hover { background: var(--bg-secondary); }
.row-pass .expand-arrow { color: var(--success); }
.row-fail .expand-arrow { color: var(--error); }
.row-error .expand-arrow { color: var(--error); }
.expand-arrow { font-size: 13px; color: var(--text-secondary); width: 14px; flex-shrink: 0; }

.rr-method {
  font-size: 10px; font-weight: 700; padding: 2px 6px;
  border-radius: 3px; text-transform: uppercase; flex-shrink: 0;
}
.method-get { color: var(--success); background: rgba(16,185,129,0.12); }
.method-post { color: var(--accent); background: var(--accent-muted); }
.method-put, .method-patch { color: var(--warning); background: rgba(245,158,11,0.12); }
.method-delete { color: var(--error); background: rgba(239,68,68,0.12); }

.rr-name-url {
  flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px;
}
.rr-name {
  font-size: 13px; font-weight: 500; color: var(--text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.rr-url {
  font-size: 11px; font-family: monospace; color: var(--text-secondary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.rr-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.rr-status { font-size: 11px; font-weight: 700; padding: 2px 6px; border-radius: 4px; }
.status-ok { color: var(--success); background: rgba(16,185,129,0.12); }
.status-redirect { color: var(--warning); background: rgba(245,158,11,0.12); }
.status-err { color: var(--error); background: rgba(239,68,68,0.12); }
.rr-time, .rr-size { font-size: 11px; color: var(--text-secondary); }
.rr-badge {
  font-size: 10px; font-weight: 700; padding: 1px 6px;
  border-radius: 10px; min-width: 20px; text-align: center;
}
.rr-pass { background: rgba(16,185,129,0.12); color: var(--success); }
.rr-fail { background: rgba(239,68,68,0.12); color: var(--error); }

/* ── Expanded assertions ─────────────────────────────── */
.result-assertions {
  background: var(--bg-secondary);
  border-bottom: 2px solid var(--border-color);
  padding: 6px 20px 10px 44px;
}

.assertion-row {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 5px 0; border-bottom: 1px solid var(--border-color);
  font-size: 13px;
}
.assertion-row:last-of-type { border-bottom: none; }
.assertion-pass .assertion-badge { }
.assertion-fail .assertion-badge { }

.assertion-badge {
  font-size: 10px; font-weight: 700; padding: 2px 7px;
  border-radius: 3px; letter-spacing: 0.5px; flex-shrink: 0; margin-top: 1px;
  font-family: monospace;
}
.badge-pass { background: rgba(16,185,129,0.15); color: var(--success); }
.badge-fail { background: rgba(239,68,68,0.15); color: var(--error); }

.assertion-text {
  color: var(--text-primary); line-height: 1.4; flex: 1;
}
.assertion-pass .assertion-text { color: var(--text-secondary); }

.assertion-no-tests {
  font-size: 12px; color: var(--text-secondary);
  font-style: italic; padding: 6px 0;
}

/* Console output */
.assertion-console {
  margin-top: 8px; padding: 8px 10px;
  background: var(--bg-primary); border: 1px solid var(--border-color);
  border-radius: 5px;
}
.console-header {
  font-size: 10px; font-weight: 600; text-transform: uppercase;
  color: var(--text-secondary); letter-spacing: 0.5px; margin-bottom: 4px;
}
.console-line {
  font-family: monospace; font-size: 12px; color: var(--text-secondary);
  line-height: 1.6;
}

/* Response toggle */
.assertion-response { margin-top: 8px; }
.response-toggle {
  background: none; border: none; font-size: 12px;
  color: var(--text-secondary); cursor: pointer; padding: 0;
  display: flex; align-items: center; gap: 6px;
}
.response-toggle:hover { color: var(--text-primary); }
.response-status { font-size: 10px; font-weight: 700; padding: 1px 5px; border-radius: 3px; }
.response-body-wrap {
  margin-top: 6px; max-height: 200px; overflow-y: auto;
  border: 1px solid var(--border-color); border-radius: 5px;
}
.response-body {
  margin: 0; padding: 10px 12px;
  background: var(--bg-primary); color: var(--text-primary);
  font-family: 'JetBrains Mono', monospace; font-size: 11px;
  line-height: 1.5; white-space: pre; overflow-x: auto;
}

/* Running indicator */
.running-indicator {
  padding: 16px; text-align: center;
  font-size: 13px; color: var(--text-secondary);
  display: flex; align-items: center; justify-content: center; gap: 8px;
}
.running-spinner { animation: spin 1s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Method badges in request list ──────────────────── */
.req-method-badge {
  font-size: 9px; font-weight: 700; padding: 1px 5px;
  border-radius: 3px; text-transform: uppercase; flex-shrink: 0;
}

/* ── Actions ─────────────────────────────────────────── */
.runner-actions {
  display: flex; gap: 10px; padding: 12px 20px;
  border-top: 1px solid var(--border-color);
  justify-content: flex-end; flex-shrink: 0;
  background: var(--bg-secondary);
}
.btn {
  padding: 7px 18px; border: none; border-radius: 6px;
  font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.15s;
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: var(--accent); color: #fff; }
.btn-primary:hover:not(:disabled) { opacity: 0.85; }
.btn-danger { background: var(--error); color: #fff; }
.btn-danger:hover { opacity: 0.9; }
.btn-warn {
  background: rgba(245,158,11,0.12); color: var(--warning);
  border: 1px solid rgba(245,158,11,0.3);
}
.btn-warn:hover { background: rgba(245,158,11,0.22); }
.btn-secondary {
  background: var(--bg-tertiary); color: var(--text-primary);
  border: 1px solid var(--border-color);
}
.btn-secondary:hover { background: var(--bg-secondary); }
</style>
