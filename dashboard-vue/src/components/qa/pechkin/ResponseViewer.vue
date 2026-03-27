<template>
  <div class="response-viewer">
    <div v-if="!store.response && !store.executing" class="rv-empty">
      <p class="rv-empty-text">Send a request to see the response</p>
    </div>

    <div v-else-if="store.executing" class="rv-loading">
      <div class="rv-spinner"></div>
      <p>Executing...</p>
    </div>

    <template v-else-if="store.response">
      <!-- Status bar -->
      <div class="rv-status-bar">
        <span class="rv-status-code" :class="statusClass">{{ store.response.status_code }}</span>
        <span class="rv-meta">{{ store.response.duration_ms?.toFixed(0) || '?' }}ms</span>
        <span class="rv-meta">{{ formatSize(store.response.size_bytes) }}</span>
      </div>

      <!-- Tabs -->
      <div class="rv-tabs">
        <button v-for="t in tabs" :key="t" class="rv-tab" :class="{ active: activeTab === t }" @click="activeTab = t">
          {{ t }}
        </button>
      </div>

      <!-- Body tab -->
      <div v-show="activeTab === 'Body'" class="rv-body">
        <div class="rv-body-toolbar">
          <button class="rv-toggle" :class="{ active: prettyMode }" @click="prettyMode = !prettyMode">Pretty</button>
          <button class="rv-toggle" @click="copyBody">{{ copied ? 'Copied!' : 'Copy' }}</button>
        </div>
        <pre class="rv-code"><code>{{ displayBody }}</code></pre>
      </div>

      <!-- Headers tab -->
      <div v-show="activeTab === 'Headers'" class="rv-headers">
        <table class="rv-table">
          <thead><tr><th>Header</th><th>Value</th></tr></thead>
          <tbody>
            <tr v-for="(val, key) in (store.response.headers || {})" :key="key">
              <td class="rv-header-key">{{ key }}</td>
              <td class="rv-header-val">{{ val }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Test Results tab -->
      <div v-show="activeTab === 'Tests'" class="rv-tests">
        <div v-if="!testResults.length" class="rv-no-tests">No test results</div>
        <div v-for="(tr, i) in testResults" :key="i" class="rv-test-item" :class="tr.passed ? 'test-pass' : 'test-fail'">
          <span class="rv-test-icon">{{ tr.passed ? '\u2713' : '\u2717' }}</span>
          <span>{{ tr.name || tr.message }}</span>
        </div>
      </div>

      <!-- History tab -->
      <div v-show="activeTab === 'History'" class="rv-history">
        <div v-if="!store.history.length" class="rv-no-tests">No history yet</div>
        <div
          v-for="h in store.history.slice(0, 20)" :key="h.id"
          class="rv-history-item"
          @click="loadHistory(h)"
        >
          <span class="rv-status-code small" :class="historyStatusClass(h.status_code)">{{ h.status_code }}</span>
          <span class="rv-history-method">{{ h.method }}</span>
          <span class="rv-history-url">{{ truncate(h.url, 40) }}</span>
          <span class="rv-history-time">{{ formatTime(h.created_at) }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { usePechkinStore } from '@/stores/pechkin'

const store = usePechkinStore()
const tabs = ['Body', 'Headers', 'Tests', 'History']
const activeTab = ref('Body')
const prettyMode = ref(true)
const copied = ref(false)

const statusClass = computed(() => {
  const code = store.response?.status_code
  if (code >= 200 && code < 300) return 'status-ok'
  if (code >= 400 && code < 500) return 'status-warn'
  return 'status-err'
})

const displayBody = computed(() => {
  const body = store.response?.body
  if (!body) return ''
  if (!prettyMode.value) return typeof body === 'string' ? body : JSON.stringify(body)
  try {
    const obj = typeof body === 'string' ? JSON.parse(body) : body
    return JSON.stringify(obj, null, 2)
  } catch (e) {
    return typeof body === 'string' ? body : String(body)
  }
})

const testResults = computed(() => store.response?.test_results || [])

function formatSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  return (bytes / 1024).toFixed(1) + ' KB'
}

function copyBody() {
  navigator.clipboard.writeText(displayBody.value)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

function historyStatusClass(code) {
  if (code >= 200 && code < 300) return 'status-ok'
  if (code >= 400 && code < 500) return 'status-warn'
  return 'status-err'
}

function truncate(s, max) {
  if (!s) return ''
  return s.length > max ? s.slice(0, max) + '...' : s
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function loadHistory(h) {
  store.response = {
    status_code: h.status_code,
    duration_ms: h.duration_ms,
    size_bytes: h.size_bytes,
    body: h.response_body,
    headers: h.response_headers || {},
    test_results: h.test_results || [],
  }
}
</script>

<style scoped>
.response-viewer {
  background: var(--bg-secondary);
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.rv-empty, .rv-loading {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 100%; color: var(--text-secondary); font-size: 13px; gap: 8px;
}
.rv-empty-text { color: var(--text-secondary); }
.rv-spinner {
  width: 28px; height: 28px; border: 3px solid var(--border-color);
  border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.rv-status-bar {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 14px; border-bottom: 1px solid var(--border-color);
}
.rv-status-code {
  font-weight: 700; font-size: 14px; padding: 2px 8px; border-radius: 4px;
}
.rv-status-code.small { font-size: 11px; padding: 1px 5px; }
.status-ok { color: var(--success); background: rgba(16, 185, 129, 0.12); }
.status-warn { color: var(--warning); background: rgba(245, 158, 11, 0.12); }
.status-err { color: var(--error); background: rgba(239, 68, 68, 0.12); }
.rv-meta { font-size: 12px; color: var(--text-secondary); }

.rv-tabs {
  display: flex; gap: 0; border-bottom: 1px solid var(--border-color);
}
.rv-tab {
  padding: 8px 16px; background: none; border: none; border-bottom: 2px solid transparent;
  color: var(--text-secondary); font-size: 12px; cursor: pointer; font-weight: 500;
}
.rv-tab:hover { color: var(--text-primary); }
.rv-tab.active { color: var(--accent); border-bottom-color: var(--accent); }

.rv-body { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.rv-body-toolbar {
  display: flex; gap: 6px; padding: 8px 14px; border-bottom: 1px solid var(--border-color);
}
.rv-toggle {
  padding: 3px 10px; background: var(--bg-tertiary); border: 1px solid var(--border-color);
  border-radius: 4px; color: var(--text-secondary); font-size: 11px; cursor: pointer;
}
.rv-toggle:hover { color: var(--text-primary); }
.rv-toggle.active { background: var(--accent-subtle); color: var(--accent); border-color: var(--accent); }

.rv-code {
  margin: 0; padding: 14px; flex: 1; overflow: auto;
  background: var(--bg-primary); color: var(--text-primary);
  font-family: monospace; font-size: 12px; line-height: 1.5; white-space: pre;
}

.rv-headers { padding: 8px 0; overflow: auto; }
.rv-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.rv-table th {
  text-align: left; padding: 6px 14px; color: var(--text-secondary);
  border-bottom: 1px solid var(--border-color); font-weight: 500;
}
.rv-table td { padding: 5px 14px; color: var(--text-primary); border-bottom: 1px solid var(--border-color); }
.rv-header-key { font-weight: 500; white-space: nowrap; }
.rv-header-val { word-break: break-all; }

.rv-tests, .rv-history { padding: 8px 14px; overflow: auto; }
.rv-no-tests { color: var(--text-secondary); font-size: 12px; text-align: center; padding: 20px; }
.rv-test-item {
  display: flex; align-items: center; gap: 8px; padding: 6px 0;
  font-size: 12px; color: var(--text-primary);
}
.rv-test-icon { font-size: 14px; font-weight: 700; }
.test-pass .rv-test-icon { color: var(--success); }
.test-fail .rv-test-icon { color: var(--error); }

.rv-history-item {
  display: flex; align-items: center; gap: 8px; padding: 6px 0;
  font-size: 12px; cursor: pointer; border-bottom: 1px solid var(--border-color);
}
.rv-history-item:hover { background: var(--bg-tertiary); }
.rv-history-method { font-weight: 600; color: var(--text-secondary); font-size: 10px; }
.rv-history-url { flex: 1; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rv-history-time { color: var(--text-secondary); font-size: 11px; white-space: nowrap; }
</style>
