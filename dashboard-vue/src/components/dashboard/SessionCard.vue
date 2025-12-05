<template>
  <div class="session-card" @click="$emit('select', session)">
    <div class="session-header">
      <span class="session-type" :class="sessionType">
        {{ sessionType }}
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
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  session: {
    type: Object,
    required: true
  }
})

defineEmits(['select'])

const sessionType = computed(() => {
  if (props.session.analysis?.severity === 'critical' || props.session.analysis?.severity === 'high') {
    return 'bug'
  }
  if (props.session.recorded_requests?.length > 0) {
    return 'chain'
  }
  return 'log'
})

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
</script>

<style scoped>
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
</style>
