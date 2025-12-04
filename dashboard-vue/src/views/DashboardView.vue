<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h1>Sessions</h1>
      <div class="filters">
        <button
          v-for="f in filters"
          :key="f.value"
          class="filter-btn"
          :class="{ active: currentFilter === f.value }"
          @click="setFilter(f.value)"
        >
          {{ f.label }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <span>Loading sessions...</span>
    </div>

    <div v-else-if="filteredSessions.length === 0" class="empty-state">
      <p>No sessions found</p>
      <p class="hint">Record a session using the bookmarklet</p>
    </div>

    <div v-else class="sessions-grid">
      <div
        v-for="session in filteredSessions"
        :key="session.id"
        class="session-card"
        @click="openSession(session)"
      >
        <div class="session-header">
          <span class="session-type" :class="getSessionType(session)">
            {{ getSessionType(session) }}
          </span>
          <span class="session-time">{{ formatTime(session.created_at) }}</span>
        </div>

        <h3 class="session-url">{{ truncateUrl(session.url) }}</h3>

        <div class="session-stats">
          <span v-if="session.recorded_requests?.length" class="stat">
            {{ session.recorded_requests.length }} requests
          </span>
          <span v-if="session.console_logs?.length" class="stat">
            {{ session.console_logs.length }} logs
          </span>
          <span v-if="session.analysis?.severity" class="severity" :class="session.analysis.severity">
            {{ session.analysis.severity }}
          </span>
        </div>

        <p v-if="session.analysis?.summary" class="session-summary">
          {{ session.analysis.summary }}
        </p>
      </div>
    </div>

    <!-- Session Detail Modal -->
    <div v-if="selectedSession" class="modal-overlay" @click.self="closeSession">
      <div class="modal-content modal-large">
        <button class="modal-close" @click="closeSession">&times;</button>

        <h2>{{ selectedSession.url }}</h2>
        <p class="session-meta">
          {{ formatTime(selectedSession.created_at) }} |
          {{ selectedSession.user_agent }}
        </p>

        <!-- Analysis Section -->
        <div v-if="selectedSession.analysis" class="analysis-section">
          <h3>Analysis</h3>
          <div class="analysis-card">
            <div class="analysis-header">
              <span class="severity-badge" :class="selectedSession.analysis.severity">
                {{ selectedSession.analysis.severity }}
              </span>
            </div>
            <p><strong>Summary:</strong> {{ selectedSession.analysis.summary }}</p>
            <p><strong>Cause:</strong> {{ selectedSession.analysis.probable_cause }}</p>
            <p><strong>Solution:</strong> {{ selectedSession.analysis.suggested_fix }}</p>
          </div>
        </div>

        <!-- Recorded Requests -->
        <div v-if="selectedSession.recorded_requests?.length" class="requests-section">
          <h3>Recorded Requests ({{ selectedSession.recorded_requests.length }})</h3>
          <div class="requests-list">
            <div
              v-for="(req, idx) in selectedSession.recorded_requests"
              :key="idx"
              class="request-item"
              :class="{ error: req.response?.status >= 400 }"
            >
              <div class="request-method" :class="req.request?.method?.toLowerCase()">
                {{ req.request?.method }}
              </div>
              <div class="request-url">{{ req.request?.url }}</div>
              <div class="request-status" :class="getStatusClass(req.response?.status)">
                {{ req.response?.status }}
              </div>
            </div>
          </div>
        </div>

        <!-- TestIt Link -->
        <div v-if="selectedSession.testit_url" class="testit-link-section">
          <a :href="selectedSession.testit_url" target="_blank" class="testit-link">
            View in TestIt (#{{ selectedSession.testit_id }})
          </a>
        </div>

        <!-- Actions -->
        <div class="modal-actions">
          <button class="btn btn-primary" @click="analyzeSession">
            Analyze
          </button>
          <button
            v-if="testItStatus.enabled && testItStatus.connected && !selectedSession.testit_url"
            class="btn btn-testit"
            :disabled="sendingToTestIt"
            @click="sendToTestIt"
            :title="`Send to TestIt (${testItStatus.project_name || 'Connected'})`"
          >
            {{ sendingToTestIt ? 'Sending...' : 'Send to TestIt' }}
          </button>
          <a
            v-else-if="selectedSession.testit_url"
            :href="selectedSession.testit_url"
            target="_blank"
            class="btn btn-testit-view"
          >
            Open in TestIt
          </a>
          <button class="btn btn-secondary" @click="exportSession('testit', 'json')">
            Export TestIt
          </button>
          <button class="btn btn-secondary" @click="exportSession('postman')">
            Export Postman
          </button>
          <button class="btn btn-secondary" @click="exportSession('pytest')">
            Export pytest
          </button>
          <button class="btn btn-danger" @click="deleteSession">
            Delete
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionsStore } from '@/stores/sessions'
import { sessionsApi, integrationsApi } from '@/services/api'

const route = useRoute()
const router = useRouter()
const store = useSessionsStore()

const selectedSession = ref(null)
const testItStatus = ref({ enabled: false, connected: false })
const sendingToTestIt = ref(false)

const filters = [
  { label: 'All', value: 'all' },
  { label: 'Bugs', value: 'bug' },
  { label: 'Chains', value: 'chain' }
]

const currentFilter = computed(() => store.filter)
const loading = computed(() => store.loading)
const filteredSessions = computed(() => store.filteredSessions)

function setFilter(filter) {
  store.setFilter(filter)
}

function getSessionType(session) {
  if (session.analysis?.severity === 'critical' || session.analysis?.severity === 'high') {
    return 'bug'
  }
  if (session.recorded_requests?.length > 0) {
    return 'chain'
  }
  return 'log'
}

function formatTime(isoDate) {
  if (!isoDate) return ''
  const date = new Date(isoDate)
  return date.toLocaleString()
}

function truncateUrl(url) {
  if (!url) return ''
  if (url.length > 60) {
    return url.substring(0, 60) + '...'
  }
  return url
}

function getStatusClass(status) {
  if (!status) return ''
  if (status >= 500) return 'error-500'
  if (status >= 400) return 'error-400'
  if (status >= 300) return 'redirect'
  return 'success'
}

function openSession(session) {
  selectedSession.value = session
  router.push(`/sessions/${session.id}`)
}

function closeSession() {
  selectedSession.value = null
  router.push('/')
}

async function analyzeSession() {
  if (!selectedSession.value) return
  const result = await store.analyzeSession(selectedSession.value.id)
  if (result) {
    selectedSession.value = { ...selectedSession.value, analysis: result }
  }
}

async function exportSession(format, subformat) {
  if (!selectedSession.value) return
  try {
    const response = await sessionsApi.export(selectedSession.value.id, format, subformat)
    const blob = response.data
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `export-${selectedSession.value.id.slice(0, 8)}.${format === 'testit' ? (subformat || 'json') : format}`
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Export failed:', error)
  }
}

async function deleteSession() {
  if (!selectedSession.value) return
  if (confirm('Delete this session?')) {
    await store.deleteSession(selectedSession.value.id)
    closeSession()
  }
}

async function checkTestItStatus() {
  try {
    const response = await integrationsApi.testItStatus()
    testItStatus.value = response.data
  } catch (error) {
    console.error('Failed to check TestIt status:', error)
  }
}

async function sendToTestIt() {
  if (!selectedSession.value || sendingToTestIt.value) return

  sendingToTestIt.value = true
  try {
    const response = await integrationsApi.sendToTestIt(selectedSession.value.id)
    const data = response.data

    if (data.success) {
      // Update session with TestIt URL
      selectedSession.value = {
        ...selectedSession.value,
        testit_url: data.testit_url,
        testit_id: data.testit_id
      }
      // Refresh sessions list
      await store.fetchSessions()

      window.open(data.testit_url, '_blank')
    }
  } catch (error) {
    const message = error.response?.data?.detail || error.message
    alert(`Failed to send to TestIt: ${message}`)
  } finally {
    sendingToTestIt.value = false
  }
}

onMounted(async () => {
  await store.fetchSessions()
  await checkTestItStatus()

  // Open session from route if specified
  if (route.params.id) {
    const session = await store.fetchSession(route.params.id)
    if (session) {
      selectedSession.value = session
    }
  }
})
</script>

<style scoped>
.dashboard-page {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
}

.filters {
  display: flex;
  gap: 8px;
}

.filter-btn {
  padding: 8px 16px;
  background: var(--bg-card);
  border: none;
  border-radius: 8px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.filter-btn:hover,
.filter-btn.active {
  background: var(--accent);
  color: white;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px;
  color: var(--text-secondary);
}

.sessions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 16px;
}

.session-card {
  background: var(--bg-card);
  padding: 20px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.session-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

.session-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.session-type {
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.session-type.bug {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.session-type.chain {
  background: rgba(124, 58, 237, 0.2);
  color: #a78bfa;
}

.session-type.log {
  background: rgba(107, 114, 128, 0.2);
  color: #9ca3af;
}

.session-time {
  font-size: 12px;
  color: var(--text-secondary);
}

.session-url {
  font-size: 14px;
  font-weight: 500;
  margin: 0 0 12px 0;
  word-break: break-all;
}

.session-stats {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}

.severity {
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.severity.critical {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.severity.high {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.severity.medium {
  background: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
}

.severity.low {
  background: rgba(107, 114, 128, 0.2);
  color: #9ca3af;
}

.session-summary {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 12px 0 0 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: var(--bg-card);
  border-radius: 16px;
  padding: 24px;
  max-width: 800px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
}

.modal-close {
  position: absolute;
  top: 16px;
  right: 16px;
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 24px;
  cursor: pointer;
}

.modal-close:hover {
  color: var(--text-primary);
}

.session-meta {
  color: var(--text-secondary);
  font-size: 12px;
  margin-bottom: 20px;
}

.analysis-section,
.requests-section {
  margin-bottom: 24px;
}

.analysis-section h3,
.requests-section h3 {
  font-size: 16px;
  margin-bottom: 12px;
}

.analysis-card {
  background: var(--bg-secondary);
  padding: 16px;
  border-radius: 8px;
}

.analysis-card p {
  margin: 8px 0;
  font-size: 14px;
}

.severity-badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
}

.requests-list {
  max-height: 300px;
  overflow-y: auto;
}

.request-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border-radius: 6px;
  margin-bottom: 4px;
  font-size: 13px;
}

.request-item.error {
  border-left: 3px solid var(--error);
}

.request-method {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  min-width: 60px;
  text-align: center;
}

.request-method.get {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.request-method.post {
  background: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
}

.request-method.put,
.request-method.patch {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.request-method.delete {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.request-url {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.request-status {
  min-width: 40px;
  text-align: right;
  font-weight: 500;
}

.request-status.success {
  color: #10b981;
}

.request-status.error-400 {
  color: #f59e0b;
}

.request-status.error-500 {
  color: #ef4444;
}

.modal-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--bg-secondary);
}

.btn-testit {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-testit:hover {
  filter: brightness(1.1);
  transform: translateY(-1px);
}

.btn-testit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-testit-view {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  text-decoration: none;
  display: inline-block;
  transition: all 0.2s;
}

.btn-testit-view:hover {
  filter: brightness(1.1);
  transform: translateY(-1px);
}

.testit-link-section {
  margin-bottom: 16px;
  padding: 12px 16px;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 8px;
}

.testit-link {
  color: #10b981;
  font-weight: 600;
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 8px;
}

.testit-link:hover {
  text-decoration: underline;
}

.testit-link::before {
  content: "✓";
  display: inline-block;
}
</style>
