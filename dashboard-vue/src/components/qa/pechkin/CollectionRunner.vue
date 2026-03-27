<template>
  <Teleport to="body">
    <div class="runner-overlay" @click.self="$emit('close')">
      <div class="runner-modal">
        <!-- Header -->
        <div class="runner-header">
          <h3 class="runner-title">Collection Runner — {{ collectionName }}</h3>
          <button class="runner-close" @click="$emit('close')">&times;</button>
        </div>

        <!-- Settings -->
        <div v-if="!running && !done" class="runner-settings">
          <div class="settings-row">
            <label class="setting-label">
              Delay between requests (ms)
              <input v-model.number="options.delayMs" type="number" min="0" step="100" class="setting-input" />
            </label>
            <label class="setting-label">
              Iterations
              <input v-model.number="options.iterations" type="number" min="1" max="100" class="setting-input" />
            </label>
            <label class="setting-check">
              <input v-model="options.stopOnError" type="checkbox" />
              Stop on error
            </label>
          </div>

          <!-- Request list with drag reorder -->
          <div class="request-list">
            <div class="request-list-header">Requests (drag to reorder)</div>
            <div
              v-for="(req, idx) in orderedRequests"
              :key="req.id"
              class="request-item"
              draggable="true"
              @dragstart="onDragStart(idx, $event)"
              @dragover.prevent="onDragOver(idx)"
              @drop="onDrop(idx)"
              @dragend="dragIdx = -1"
              :class="{ 'drag-over': dragOverIdx === idx }"
            >
              <span class="drag-handle">&#x2630;</span>
              <input type="checkbox" v-model="req.selected" class="req-check" />
              <span class="method-badge" :class="methodClass(req.method)">{{ req.method }}</span>
              <span class="req-name">{{ req.name || 'Untitled' }}</span>
            </div>
            <div v-if="!orderedRequests.length" class="empty-msg">No requests in collection</div>
          </div>
        </div>

        <!-- Progress -->
        <div v-if="running" class="runner-progress">
          <div class="progress-bar-wrap">
            <div class="progress-bar" :style="{ width: progressPct + '%' }"></div>
          </div>
          <div class="progress-stats">
            <span>{{ completed }} / {{ totalRequests }}</span>
            <span class="stat-passed">{{ passed }} passed</span>
            <span class="stat-failed">{{ failed }} failed</span>
          </div>
        </div>

        <!-- Results -->
        <div v-if="results.length" class="runner-results">
          <div class="results-header">Results</div>
          <div v-for="(r, i) in results" :key="i" class="result-item" :class="resultClass(r)">
            <span class="result-status" :class="statusClass(r.status_code)">{{ r.status_code || 'ERR' }}</span>
            <span class="method-badge small" :class="methodClass(r.method)">{{ r.method }}</span>
            <span class="result-name">{{ r.request_name || 'Request' }}</span>
            <span class="result-duration">{{ r.duration_ms }}ms</span>
            <span v-if="r.passed" class="stat-passed">{{ r.passed }}&#10003;</span>
            <span v-if="r.failed" class="stat-failed">{{ r.failed }}&#10007;</span>
            <span v-if="r.error" class="result-error" :title="r.error">{{ r.error }}</span>
          </div>
        </div>

        <!-- Summary -->
        <div v-if="done" class="runner-summary">
          <div class="summary-stats">
            <span class="summary-rate" :class="passRateCls">{{ passRate }}% pass rate</span>
            <span class="summary-time">Total: {{ totalTime }}ms</span>
          </div>
        </div>

        <!-- Actions -->
        <div class="runner-actions">
          <button v-if="!running && !done" class="btn btn-primary" @click="runAll"
            :disabled="!selectedCount">
            Run ({{ selectedCount }})
          </button>
          <button v-if="running" class="btn btn-danger" @click="stopRun">Stop</button>
          <button v-if="done" class="btn btn-secondary" @click="exportResults">Export CSV</button>
          <button v-if="done" class="btn btn-primary" @click="reset">Run Again</button>
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

const running = ref(false)
const done = ref(false)
const stopped = ref(false)
const results = ref([])
const passed = ref(0)
const failed = ref(0)
const completed = ref(0)
const totalTime = ref(0)
const options = reactive({ delayMs: 0, stopOnError: false, iterations: 1 })
const orderedRequests = ref([])

// Drag state
const dragIdx = ref(-1)
const dragOverIdx = ref(-1)

onMounted(() => {
  orderedRequests.value = props.requests.map(r => ({ ...r, selected: true }))
})

const selectedCount = computed(() => orderedRequests.value.filter(r => r.selected).length)
const totalRequests = computed(() => selectedCount.value * options.iterations)
const progressPct = computed(() => totalRequests.value ? (completed.value / totalRequests.value) * 100 : 0)
const passRate = computed(() => {
  const total = passed.value + failed.value
  return total ? Math.round((passed.value / total) * 100) : 100
})
const passRateCls = computed(() => passRate.value >= 80 ? 'rate-good' : passRate.value >= 50 ? 'rate-warn' : 'rate-bad')

function methodClass(m) {
  const map = { GET: 'method-get', POST: 'method-post', PUT: 'method-put', PATCH: 'method-patch', DELETE: 'method-delete' }
  return map[m?.toUpperCase()] || 'method-get'
}

function statusClass(code) {
  if (!code) return 'status-err'
  if (code < 300) return 'status-ok'
  if (code < 400) return 'status-redirect'
  return 'status-err'
}

function resultClass(r) {
  return r.error || r.failed ? 'result-fail' : 'result-pass'
}

// Drag and drop
function onDragStart(idx, e) {
  dragIdx.value = idx
  e.dataTransfer.effectAllowed = 'move'
}
function onDragOver(idx) { dragOverIdx.value = idx }
function onDrop(idx) {
  const arr = [...orderedRequests.value]
  const [moved] = arr.splice(dragIdx.value, 1)
  arr.splice(idx, 0, moved)
  orderedRequests.value = arr
  dragOverIdx.value = -1
}

async function runAll() {
  running.value = true
  done.value = false
  stopped.value = false
  results.value = []
  passed.value = 0
  failed.value = 0
  completed.value = 0
  totalTime.value = 0

  const selectedIds = orderedRequests.value.filter(r => r.selected).map(r => r.id)
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
    for (const r of results.value) {
      completed.value++
      passed.value += r.passed || 0
      failed.value += r.failed || 0
    }
    totalTime.value = resp.data.total_time_ms || results.value.reduce((s, r) => s + (r.duration_ms || 0), 0)
  } catch (e) {
    console.error('Collection run failed:', e)
  } finally {
    running.value = false
    done.value = true
  }
}

function stopRun() { stopped.value = true }

function reset() {
  done.value = false
  results.value = []
  passed.value = 0
  failed.value = 0
  completed.value = 0
  totalTime.value = 0
}

function exportResults() {
  const rows = [
    'Name,Method,URL,Status,Duration(ms),Passed,Failed,Error',
    ...results.value.map(r =>
      `"${r.request_name || ''}",${r.method || ''},"${r.url || ''}",${r.status_code || ''},${r.duration_ms || 0},${r.passed || 0},${r.failed || 0},"${(r.error || '').replace(/"/g, '""')}"`
    )
  ]
  const csv = rows.join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.collectionName}-run.csv`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.runner-overlay {
  position: fixed; inset: 0; z-index: 9000;
  background: rgba(0, 0, 0, 0.5); display: flex;
  align-items: center; justify-content: center;
}
.runner-modal {
  background: var(--bg-card); border: 1px solid var(--border-color);
  border-radius: 10px; box-shadow: var(--shadow);
  width: 640px; max-height: 80vh; display: flex;
  flex-direction: column; overflow: hidden;
}
.runner-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; border-bottom: 1px solid var(--border-color);
}
.runner-title { font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 0; }
.runner-close {
  background: none; border: none; font-size: 22px;
  color: var(--text-secondary); cursor: pointer; line-height: 1;
}
.runner-close:hover { color: var(--text-primary); }

/* Settings */
.runner-settings { padding: 16px 20px; overflow-y: auto; flex: 1; }
.settings-row {
  display: flex; gap: 16px; align-items: flex-end;
  margin-bottom: 16px; flex-wrap: wrap;
}
.setting-label {
  display: flex; flex-direction: column; gap: 4px;
  font-size: 12px; color: var(--text-secondary);
}
.setting-input {
  width: 100px; padding: 6px 8px; border: 1px solid var(--border-color);
  border-radius: 6px; background: var(--bg-primary); color: var(--text-primary);
  font-size: 13px;
}
.setting-check {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: var(--text-secondary); cursor: pointer;
  padding-bottom: 6px;
}

/* Request list */
.request-list { border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; }
.request-list-header {
  padding: 8px 12px; font-size: 11px; font-weight: 600;
  color: var(--text-secondary); background: var(--bg-tertiary);
  text-transform: uppercase; letter-spacing: 0.5px;
}
.request-item {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 12px; border-top: 1px solid var(--border-color);
  font-size: 12px; color: var(--text-primary); cursor: grab;
  transition: background 0.1s;
}
.request-item:hover { background: var(--bg-tertiary); }
.request-item.drag-over { border-top: 2px solid var(--accent); }
.drag-handle { color: var(--text-secondary); font-size: 11px; cursor: grab; user-select: none; }
.req-check { accent-color: var(--accent); }
.req-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty-msg { padding: 20px; text-align: center; color: var(--text-secondary); font-size: 12px; }

/* Progress */
.runner-progress { padding: 16px 20px; }
.progress-bar-wrap {
  height: 6px; background: var(--bg-tertiary); border-radius: 3px; overflow: hidden;
}
.progress-bar {
  height: 100%; background: var(--accent); border-radius: 3px;
  transition: width 0.3s ease;
}
.progress-stats {
  display: flex; gap: 16px; margin-top: 10px;
  font-size: 12px; color: var(--text-secondary);
}
.stat-passed { color: var(--success); font-weight: 600; }
.stat-failed { color: var(--error); font-weight: 600; }

/* Results */
.runner-results { padding: 0 20px 16px; overflow-y: auto; flex: 1; max-height: 300px; }
.results-header {
  font-size: 11px; font-weight: 600; color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;
}
.result-item {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 10px; border-radius: 6px; margin-bottom: 4px;
  font-size: 12px; color: var(--text-primary);
}
.result-pass { background: rgba(16, 185, 129, 0.06); }
.result-fail { background: rgba(239, 68, 68, 0.06); }
.result-status {
  font-size: 11px; font-weight: 700; min-width: 36px; text-align: center;
  padding: 2px 4px; border-radius: 4px;
}
.status-ok { color: var(--success); background: rgba(16, 185, 129, 0.12); }
.status-redirect { color: var(--warning); background: rgba(245, 158, 11, 0.12); }
.status-err { color: var(--error); background: rgba(239, 68, 68, 0.12); }
.result-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.result-duration { color: var(--text-secondary); font-size: 11px; }
.result-error {
  color: var(--error); font-size: 11px; max-width: 160px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* Method badges */
.method-badge {
  font-size: 9px; font-weight: 700; padding: 1px 4px; border-radius: 3px;
  text-transform: uppercase; flex-shrink: 0; min-width: 32px; text-align: center;
}
.method-badge.small { font-size: 8px; min-width: 28px; }
.method-get { color: var(--success); background: rgba(16, 185, 129, 0.12); }
.method-post { color: var(--accent); background: var(--accent-muted); }
.method-put { color: var(--warning); background: rgba(245, 158, 11, 0.12); }
.method-patch { color: var(--warning); background: rgba(245, 158, 11, 0.08); }
.method-delete { color: var(--error); background: rgba(239, 68, 68, 0.12); }

/* Summary */
.runner-summary { padding: 12px 20px; border-top: 1px solid var(--border-color); }
.summary-stats { display: flex; gap: 16px; align-items: center; font-size: 13px; }
.summary-rate { font-weight: 700; }
.rate-good { color: var(--success); }
.rate-warn { color: var(--warning); }
.rate-bad { color: var(--error); }
.summary-time { color: var(--text-secondary); font-size: 12px; }

/* Actions */
.runner-actions {
  display: flex; gap: 10px; padding: 14px 20px;
  border-top: 1px solid var(--border-color); justify-content: flex-end;
}
.btn {
  padding: 7px 18px; border: none; border-radius: 6px;
  font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.15s;
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: var(--accent); color: #fff; }
.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
.btn-danger { background: var(--error); color: #fff; }
.btn-danger:hover { opacity: 0.9; }
.btn-secondary { background: var(--bg-tertiary); color: var(--text-primary); border: 1px solid var(--border-color); }
.btn-secondary:hover { background: var(--bg-secondary); }
</style>
