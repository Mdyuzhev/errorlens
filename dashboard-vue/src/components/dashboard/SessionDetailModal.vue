<template>
  <div class="modal-overlay modal" data-testid="session-detail-modal" @click.self="$emit('close')">
    <div class="modal-content modal-large session-detail">
      <button class="modal-close" @click="$emit('close')">&times;</button>

      <h2>{{ session.url }}</h2>
      <p class="session-meta">
        {{ formatTime(session.created_at) }} |
        {{ session.user_agent }}
      </p>

      <!-- Analysis Section -->
      <div v-if="session.analysis" class="analysis-section">
        <h3>Analysis</h3>
        <div class="analysis-card">
          <div class="analysis-header">
            <span class="severity-badge" :class="session.analysis.severity">
              {{ session.analysis.severity }}
            </span>
          </div>
          <p><strong>Summary:</strong> {{ session.analysis.summary }}</p>
          <p><strong>Cause:</strong> {{ session.analysis.probable_cause }}</p>
          <p><strong>Solution:</strong> {{ session.analysis.suggested_fix }}</p>
        </div>
      </div>

      <!-- Recorded Requests -->
      <div v-if="session.recorded_requests?.length" class="requests-section">
        <h3>Recorded Requests ({{ session.recorded_requests.length }})</h3>
        <div class="requests-list">
          <div
            v-for="(req, idx) in session.recorded_requests"
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
      <div v-if="session.testit_url" class="testit-link-section">
        <a :href="session.testit_url" target="_blank" class="testit-link">
          View in TestIt (#{{ session.testit_id }})
        </a>
      </div>

      <!-- Actions -->
      <div class="modal-actions">
        <button class="btn btn-primary" @click="$emit('analyze')">
          Analyze
        </button>
        <button
          v-if="session.recorded_requests?.length > 0"
          class="btn btn-generate"
          @click="$emit('generate-tests')"
        >
          🔧 Генерировать тесты
        </button>
        <button
          v-if="testItStatus.enabled && testItStatus.connected && !session.testit_url"
          class="btn btn-testit"
          :disabled="sendingToTestIt"
          @click="$emit('send-to-testit')"
          :title="`Send to TestIt (${testItStatus.project_name || 'Connected'})`"
        >
          {{ sendingToTestIt ? 'Sending...' : 'Send to TestIt' }}
        </button>
        <a
          v-else-if="session.testit_url"
          :href="session.testit_url"
          target="_blank"
          class="btn btn-testit-view"
        >
          Open in TestIt
        </a>
        <button class="btn btn-secondary" @click="$emit('export', 'testit', 'json')">
          Export TestIt
        </button>
        <button class="btn btn-secondary" @click="$emit('export', 'postman')">
          Export Postman
        </button>
        <button class="btn btn-secondary" @click="$emit('export', 'pytest')">
          Export pytest
        </button>
        <button class="btn btn-danger" @click="$emit('delete')">
          Delete
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  session: {
    type: Object,
    required: true
  },
  testItStatus: {
    type: Object,
    default: () => ({ enabled: false, connected: false })
  },
  sendingToTestIt: {
    type: Boolean,
    default: false
  }
})

defineEmits(['close', 'analyze', 'export', 'delete', 'send-to-testit', 'generate-tests'])

function formatTime(isoDate) {
  if (!isoDate) return ''
  const date = new Date(isoDate)
  return date.toLocaleString()
}

function getStatusClass(status) {
  if (!status) return ''
  if (status >= 500) return 'error-500'
  if (status >= 400) return 'error-400'
  if (status >= 300) return 'redirect'
  return 'success'
}
</script>

<style scoped>
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

.severity-badge.critical {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.severity-badge.high {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.severity-badge.medium {
  background: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
}

.severity-badge.low {
  background: rgba(107, 114, 128, 0.2);
  color: #9ca3af;
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

.btn-generate {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.btn-generate:hover {
  filter: brightness(1.1);
  transform: translateY(-1px);
}
</style>
