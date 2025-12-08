<template>
  <div class="session-selector">
    <div v-if="loading" class="loading">
      Загрузка сессий...
    </div>

    <div v-else-if="error" class="error">
      {{ error }}
    </div>

    <div v-else-if="sessions.length === 0" class="empty">
      <div style="font-size:48px">📹</div>
      <p>Нет сессий с записанными запросами</p>
      <p style="color:var(--text-secondary);font-size:13px">
        Запустите ErrorLens SDK для записи HTTP-запросов
      </p>
    </div>

    <div v-else>
      <select v-model="selectedSessionId" class="session-select">
        <option value="">Выберите сессию...</option>
        <option v-for="s in sessions" :key="s.id" :value="s.id">
          {{ s.url }} ({{ s.recorded_requests.length }} requests)
        </option>
      </select>

      <div v-if="selectedSession" class="session-preview">
        <h4>Endpoints в сессии:</h4>
        <div class="endpoints-list">
          <div
            v-for="(ep, idx) in endpoints"
            :key="idx"
            class="endpoint-item"
          >
            <span class="method" :class="ep.method.toLowerCase()">
              {{ ep.method }}
            </span>
            <span class="path">{{ ep.path }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'

const emit = defineEmits(['session-selected'])

const sessions = ref([])
const selectedSessionId = ref('')
const loading = ref(true)
const error = ref('')

const selectedSession = computed(() =>
  sessions.value.find(s => s.id === selectedSessionId.value)
)

const endpoints = computed(() => {
  if (!selectedSession.value) return []

  const uniqueEndpoints = new Map()

  selectedSession.value.recorded_requests.forEach(req => {
    const method = req.method || 'GET'
    const path = req.path || req.url || ''
    const key = `${method}:${path}`

    if (!uniqueEndpoints.has(key)) {
      uniqueEndpoints.set(key, { method, path })
    }
  })

  return Array.from(uniqueEndpoints.values())
})

watch(selectedSessionId, () => {
  if (selectedSession.value) {
    emit('session-selected', selectedSession.value)
  }
})

onMounted(async () => {
  try {
    const token = localStorage.getItem('access_token')
    if (!token) {
      error.value = 'Требуется авторизация'
      loading.value = false
      return
    }

    const apiUrl = import.meta.env.VITE_API_URL || ''
    const response = await fetch(`${apiUrl}/sessions?limit=100`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (!response.ok) {
      throw new Error(`Ошибка загрузки: ${response.status}`)
    }

    const data = await response.json()

    sessions.value = (data.items || []).filter(
      s => s.recorded_requests && s.recorded_requests.length > 0
    )
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.session-selector {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.loading,
.error,
.empty {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}

.error {
  color: var(--error);
}

.empty p:first-of-type {
  color: var(--text-primary);
  font-weight: 600;
  margin: 12px 0 4px;
}

.session-select {
  width: 100%;
  padding: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.session-select:hover {
  border-color: var(--accent);
}

.session-select:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.session-preview {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
}

.session-preview h4 {
  margin: 0 0 12px;
  font-size: 14px;
  color: var(--text-secondary);
}

.endpoints-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;
}

.endpoint-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: var(--bg-card);
  border-radius: 6px;
  font-size: 13px;
}

.method {
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  font-size: 11px;
}

.method.get {
  background: rgba(76, 175, 80, 0.2);
  color: #4CAF50;
}

.method.post {
  background: rgba(33, 150, 243, 0.2);
  color: #2196F3;
}

.method.put,
.method.patch {
  background: rgba(255, 152, 0, 0.2);
  color: #FF9800;
}

.method.delete {
  background: rgba(244, 67, 54, 0.2);
  color: #f44336;
}

.path {
  color: var(--text-primary);
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
