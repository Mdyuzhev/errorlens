<template>
  <div class="progress-container">
    <div style="display:flex;justify-content:space-between;margin-bottom:12px">
      <span style="font-weight:600">{{ statusText }}</span>
      <span style="color:var(--text-secondary)">{{ progress }} / {{ total }}</span>
    </div>
    <div class="progress-bar">
      <div class="progress-fill" :style="{ width: percent + '%' }" :class="statusClass"></div>
    </div>
    <div v-if="currentEndpoint" style="font-family:monospace;font-size:13px;color:var(--text-secondary);margin:12px 0">
      {{ currentEndpoint }}
    </div>
    <div class="logs" v-if="logs && logs.length > 0">
      <div v-for="(log, i) in logs" :key="i" class="log-item">{{ log }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  progress: Number,
  total: Number,
  currentEndpoint: String,
  logs: Array,
  status: String
})

const percent = computed(() => props.total ? Math.round((props.progress / props.total) * 100) : 0)

const statusText = computed(() => {
  const statuses = {
    idle: 'Ожидание...',
    connecting: 'Подключение...',
    running: 'Генерация...',
    completed: 'Завершено!',
    error: 'Ошибка'
  }
  return statuses[props.status] || ''
})

const statusClass = computed(() => {
  if (props.status === 'completed') return 'success'
  if (props.status === 'error') return 'error'
  return ''
})
</script>

<style scoped>
.progress-container {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 20px;
}

.progress-bar {
  height: 8px;
  background: #2a2a4a;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  transition: width 0.3s;
}

.progress-fill.success {
  background: linear-gradient(135deg, #4CAF50, #45a049);
}

.progress-fill.error {
  background: linear-gradient(135deg, #f44336, #d32f2f);
}

.logs {
  max-height: 200px;
  overflow-y: auto;
  background: #1a1a2e;
  border-radius: 8px;
  padding: 12px;
  margin-top: 12px;
  font-family: monospace;
  font-size: 12px;
}

.log-item {
  padding: 4px 0;
  border-bottom: 1px solid #333;
  color: var(--text-secondary);
}

.log-item:last-child {
  border-bottom: none;
}
</style>
