<template>
  <div class="global-history">
    <div class="history-toolbar">
      <input v-model="search" class="history-search" placeholder="Filter by URL or status..." />
      <button class="btn-clear" @click="clearAll" v-if="history.length">Clear All</button>
    </div>
    <div class="history-list">
      <div
        v-for="h in filteredHistory"
        :key="h.id"
        class="history-item"
        @click="replay(h)"
      >
        <span class="h-method" :class="'method-' + h.method.toLowerCase()">{{ h.method }}</span>
        <span class="h-url">{{ h.resolved_url }}</span>
        <span class="h-status" :class="statusClass(h.status_code)">{{ h.status_code || '—' }}</span>
        <span class="h-time">{{ h.duration_ms }}ms</span>
        <span class="h-date">{{ formatRelative(h.executed_at) }}</span>
      </div>
      <div v-if="!filteredHistory.length" class="history-empty">
        {{ search ? 'No matches' : 'No history yet' }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { usePechkinStore } from '@/stores/pechkin'

const props = defineProps({
  projectId: { type: String, required: true }
})
const emit = defineEmits(['replay'])

const store = usePechkinStore()
const search = ref('')
const history = ref([])

onMounted(async () => {
  await fetchHistory()
})

async function fetchHistory() {
  history.value = await store.fetchGlobalHistory(props.projectId)
}

const filteredHistory = computed(() => {
  if (!search.value) return history.value
  const q = search.value.toLowerCase()
  return history.value.filter(h =>
    (h.resolved_url || '').toLowerCase().includes(q) ||
    String(h.status_code || '').includes(q)
  )
})

function statusClass(code) {
  if (!code) return 'status-none'
  if (code < 300) return 'status-ok'
  if (code < 400) return 'status-redirect'
  if (code < 500) return 'status-client-err'
  return 'status-server-err'
}

function formatRelative(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diff = Math.floor((now - d) / 1000)
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

function replay(h) {
  emit('replay', h)
}

function clearAll() {
  history.value = []
}
</script>

<style scoped>
.global-history {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-secondary);
}
.history-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-color);
}
.history-search {
  flex: 1;
  padding: 6px 10px;
  font-size: 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  outline: none;
}
.history-search:focus {
  border-color: var(--accent);
}
.history-search::placeholder {
  color: var(--text-secondary);
}
.btn-clear {
  padding: 5px 10px;
  font-size: 11px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-tertiary);
  color: var(--error);
  cursor: pointer;
  white-space: nowrap;
}
.btn-clear:hover {
  background: var(--bg-card);
}
.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}
.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 12px;
  transition: background 0.1s;
}
.history-item:hover {
  background: var(--bg-tertiary);
}
.h-method {
  font-size: 9px;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 3px;
  text-transform: uppercase;
  min-width: 32px;
  text-align: center;
  flex-shrink: 0;
}
.method-get { color: var(--success); background: rgba(16, 185, 129, 0.12); }
.method-post { color: var(--accent); background: var(--accent-muted); }
.method-put { color: var(--warning); background: rgba(245, 158, 11, 0.12); }
.method-patch { color: var(--warning); background: rgba(245, 158, 11, 0.08); }
.method-delete { color: var(--error); background: rgba(239, 68, 68, 0.12); }
.h-url {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary);
}
.h-status {
  font-weight: 600;
  font-size: 11px;
  min-width: 28px;
  text-align: center;
  flex-shrink: 0;
}
.status-ok { color: var(--success); }
.status-redirect { color: var(--warning); }
.status-client-err { color: var(--error); }
.status-server-err { color: var(--error); }
.status-none { color: var(--text-secondary); }
.h-time {
  color: var(--text-secondary);
  font-size: 11px;
  min-width: 44px;
  text-align: right;
  flex-shrink: 0;
}
.h-date {
  color: var(--text-secondary);
  font-size: 10px;
  min-width: 48px;
  text-align: right;
  flex-shrink: 0;
}
.history-empty {
  padding: 32px 16px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
}
</style>
