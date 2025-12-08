<template>
  <div class="url-input">
    <div v-if="endpoints.length === 0" class="empty-state">
      <div style="font-size:48px">🔗</div>
      <p>Добавьте endpoints для генерации тестов</p>
    </div>

    <div v-else class="endpoints-container">
      <div v-for="(ep, i) in endpoints" :key="i" class="endpoint-row">
        <select v-model="ep.method" class="method-select">
          <option value="GET">GET</option>
          <option value="POST">POST</option>
          <option value="PUT">PUT</option>
          <option value="PATCH">PATCH</option>
          <option value="DELETE">DELETE</option>
        </select>
        <input
          v-model="ep.url"
          class="url-input-field"
          placeholder="https://api.example.com/users/{id}"
          @blur="validateUrl(i)"
        />
        <button
          class="remove-btn"
          @click="removeEndpoint(i)"
          title="Удалить endpoint"
        >
          ✕
        </button>
      </div>
      <div v-if="hasErrors" class="validation-errors">
        Исправьте ошибки в URL (должен начинаться с http:// или https://)
      </div>
    </div>

    <button class="add-btn" @click="addEndpoint">
      + Добавить endpoint
    </button>

    <div v-if="endpoints.length > 0" class="actions">
      <button class="clear-btn" @click="clearAll">
        Очистить всё
      </button>
      <button
        class="submit-btn"
        :disabled="!canSubmit"
        @click="submitEndpoints"
      >
        ✓ Готово ({{ endpoints.length }})
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const emit = defineEmits(['endpoints-added', 'cleared'])

const endpoints = ref([])
const errors = ref([])

const hasErrors = computed(() => errors.value.some(e => e))

const canSubmit = computed(() => {
  return endpoints.value.length > 0 &&
    endpoints.value.every(ep => ep.url && isValidUrl(ep.url)) &&
    !hasErrors.value
})

function addEndpoint() {
  endpoints.value.push({
    method: 'GET',
    url: ''
  })
}

function removeEndpoint(index) {
  endpoints.value.splice(index, 1)
  errors.value.splice(index, 1)

  if (endpoints.value.length === 0) {
    emit('cleared')
  }
}

function clearAll() {
  endpoints.value = []
  errors.value = []
  emit('cleared')
}

function isValidUrl(url) {
  if (!url) return false
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'http:' || parsed.protocol === 'https:'
  } catch {
    return false
  }
}

function validateUrl(index) {
  const ep = endpoints.value[index]
  errors.value[index] = ep.url && !isValidUrl(ep.url)
}

function parsePathParams(url) {
  const matches = url.match(/\{([^}]+)\}/g)
  return matches ? matches.map(m => m.slice(1, -1)) : []
}

function submitEndpoints() {
  if (!canSubmit.value) return

  const specs = endpoints.value.map(ep => {
    const url = new URL(ep.url)
    const pathParams = parsePathParams(url.pathname)

    return {
      method: ep.method,
      url: ep.url,
      path: url.pathname,
      pathParams
    }
  })

  emit('endpoints-added', specs)
}

watch(endpoints, () => {
  if (canSubmit.value) {
    submitEndpoints()
  }
}, { deep: true })

// Add initial endpoint
if (endpoints.value.length === 0) {
  addEndpoint()
}
</script>

<style scoped>
.url-input {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}

.empty-state p {
  color: var(--text-primary);
  font-weight: 600;
  margin-top: 12px;
}

.endpoints-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.endpoint-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.method-select {
  padding: 10px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  min-width: 100px;
}

.url-input-field {
  flex: 1;
  padding: 10px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 13px;
  font-family: monospace;
}

.url-input-field:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.url-input-field::placeholder {
  color: var(--text-secondary);
}

.remove-btn {
  padding: 10px 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--error);
  cursor: pointer;
  transition: all 0.2s;
}

.remove-btn:hover {
  background: rgba(244, 67, 54, 0.1);
  border-color: var(--error);
}

.validation-errors {
  padding: 8px 12px;
  background: rgba(244, 67, 54, 0.1);
  color: var(--error);
  border-radius: 6px;
  font-size: 13px;
}

.add-btn {
  padding: 12px 16px;
  background: var(--bg-secondary);
  border: 1px dashed var(--border-color);
  border-radius: 8px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}

.add-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(102, 126, 234, 0.05);
}

.actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.clear-btn {
  padding: 10px 16px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.clear-btn:hover {
  border-color: var(--error);
  color: var(--error);
}

.submit-btn {
  padding: 10px 20px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.submit-btn:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}
</style>
