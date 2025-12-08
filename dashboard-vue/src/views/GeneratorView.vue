<template>
  <div class="generator-page">
    <h1>Генератор тестов</h1>

    <div class="generator-layout">
      <!-- Left Panel: Settings -->
      <div class="settings-panel">
        <h2>Настройки генерации</h2>

        <InputTabs
          v-model="inputType"
          @input-ready="onInputReady"
          @input-cleared="onInputCleared"
        />

        <FrameworkSelector v-model="framework" />

        <ProviderSelector
          v-model="provider"
          v-model:model="model"
        />

        <button
          class="generate-btn"
          :disabled="!canGenerate || isGenerating"
          @click="startGeneration"
        >
          <span v-if="isGenerating">Генерация...</span>
          <span v-else>Генерировать тесты</span>
        </button>
      </div>

      <!-- Right Panel: Status & History -->
      <div class="status-panel">
        <!-- Current Generation Status -->
        <div v-if="step === 'progress'" class="status-section">
          <h2>Статус генерации</h2>
          <GenerationProgress
            :progress="socket?.progress.value"
            :total="socket?.total.value"
            :current-endpoint="socket?.currentEndpoint.value"
            :logs="socket?.logs.value"
            :status="socket?.status.value"
          />
        </div>

        <!-- Results -->
        <div v-else-if="step === 'results'" class="status-section">
          <h2>Результаты</h2>
          <div class="results-stats">
            <div class="stat-card">
              <span class="stat-value">{{ store.result?.total_endpoints || 0 }}</span>
              <span class="stat-label">Эндпоинтов</span>
            </div>
            <div class="stat-card success">
              <span class="stat-value">{{ store.result?.successful || 0 }}</span>
              <span class="stat-label">Успешно</span>
            </div>
            <div class="stat-card" v-if="store.result?.failed">
              <span class="stat-value error">{{ store.result?.failed }}</span>
              <span class="stat-label">Ошибок</span>
            </div>
          </div>

          <CodePreview
            title="Сгенерированный код"
            :code="generatedCode"
            :language="getCodeLanguage(framework)"
          />

          <div class="results-actions">
            <a :href="downloadUrl" class="btn btn-primary" download>
              Скачать ZIP
            </a>
            <button class="btn btn-secondary" @click="reset">
              Новая генерация
            </button>
          </div>
        </div>

        <!-- Empty State -->
        <div v-else class="empty-status">
          <p>Выберите входные данные и нажмите "Генерировать"</p>
        </div>

        <!-- Generation History -->
        <div class="history-section">
          <h2>История генераций</h2>
          <div v-if="history.length === 0" class="empty-history">
            Нет сохраненных генераций
          </div>
          <div v-else class="history-list">
            <div
              v-for="item in history"
              :key="item.id"
              class="history-item"
            >
              <div class="history-info">
                <span class="history-framework">{{ item.framework }}</span>
                <span class="history-date">{{ formatDate(item.timestamp) }}</span>
              </div>
              <div class="history-meta">
                {{ item.endpoints }} endpoints
              </div>
              <div class="history-actions">
                <button class="btn-icon" @click="downloadHistory(item)" title="Скачать">
                  📥
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useGenerationStore } from '@/stores/generation'
import { useGenerationSocket } from '@/composables/useGenerationSocket'
import InputTabs from '@/components/generator/InputTabs.vue'
import FrameworkSelector from '@/components/generator/FrameworkSelector.vue'
import ProviderSelector from '@/components/generator/ProviderSelector.vue'
import GenerationProgress from '@/components/generator/GenerationProgress.vue'
import CodePreview from '@/components/generator/CodePreview.vue'

const props = defineProps({
  sessionId: {
    type: String,
    default: null
  }
})

const store = useGenerationStore()

const step = ref('input')
const inputType = ref('swagger')
const inputData = ref(null)
const framework = ref('pytest')
const provider = ref('ollama')
const model = ref('')
const generatedCode = ref('')
const isGenerating = ref(false)
const history = ref([])
let socket = null

const HISTORY_KEY = 'errorlens_generation_history'

const canGenerate = computed(() => {
  return inputData.value !== null && framework.value && provider.value
})

const downloadUrl = computed(() =>
  socket?.resultId.value ? store.getDownloadUrl(socket.resultId.value) : ''
)

onMounted(async () => {
  loadHistory()
  if (props.sessionId) {
    await startFromSession(props.sessionId)
  }
})

function loadHistory() {
  try {
    const saved = localStorage.getItem(HISTORY_KEY)
    if (saved) {
      history.value = JSON.parse(saved)
    }
  } catch (e) {
    console.error('Failed to load history:', e)
  }
}

function saveHistory() {
  try {
    // Keep max 20 items
    const toSave = history.value.slice(0, 20)
    localStorage.setItem(HISTORY_KEY, JSON.stringify(toSave))
  } catch (e) {
    console.error('Failed to save history:', e)
  }
}

function addToHistory(item) {
  const newItem = {
    id: Date.now().toString(),
    timestamp: new Date().toISOString(),
    framework: item.framework,
    endpoints: item.endpoints,
    result_id: item.result_id
  }
  history.value.unshift(newItem)
  saveHistory()
}

function onInputReady(data) {
  inputData.value = data
}

function onInputCleared() {
  inputData.value = null
}

async function startGeneration() {
  if (!canGenerate.value || isGenerating.value) return

  isGenerating.value = true

  try {
    let response

    if (inputData.value.type === 'swagger') {
      response = await store.startFromSwagger(inputData.value.data, {
        framework: framework.value,
        provider: provider.value,
        model: model.value
      })
    } else if (inputData.value.type === 'session') {
      response = await store.startFromSession(inputData.value.data.id, {
        framework: framework.value,
        provider: provider.value,
        model: model.value
      })
    } else if (inputData.value.type === 'url') {
      response = await store.startFromEndpoints(inputData.value.data, {
        framework: framework.value,
        provider: provider.value,
        model: model.value
      })
    }

    socket = useGenerationSocket(response.task_id)
    step.value = 'progress'
    socket.connect()
  } catch (err) {
    console.error('Generation failed:', err)
    isGenerating.value = false
  }
}

async function startFromSession(sessionId) {
  isGenerating.value = true
  try {
    const response = await store.startFromSession(sessionId, {
      framework: framework.value,
      provider: provider.value,
      model: model.value
    })
    socket = useGenerationSocket(response.task_id)
    step.value = 'progress'
    socket.connect()
  } catch (err) {
    console.error('Generation from session failed:', err)
    isGenerating.value = false
  }
}

watch(() => socket?.status.value, async (s) => {
  if (s === 'completed' && socket?.resultId.value) {
    await store.fetchResult(socket.resultId.value)
    generatedCode.value = store.result?.generated_code || ''

    addToHistory({
      framework: framework.value,
      endpoints: store.result?.total_endpoints || 0,
      result_id: socket.resultId.value
    })

    step.value = 'results'
    isGenerating.value = false
  } else if (s === 'error') {
    isGenerating.value = false
  }
})

function reset() {
  step.value = 'input'
  inputData.value = null
  generatedCode.value = ''
  store.reset()
  socket = null
  isGenerating.value = false
}

function getCodeLanguage(fw) {
  const languages = {
    pytest: 'python',
    restassured: 'java',
    postman: 'json',
    cypress: 'javascript',
    k6: 'javascript'
  }
  return languages[fw] || 'python'
}

function formatDate(dateStr) {
  const date = new Date(dateStr)
  return date.toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function downloadHistory(item) {
  if (item.result_id) {
    const url = store.getDownloadUrl(item.result_id)
    window.open(url, '_blank')
  }
}
</script>

<style scoped>
.generator-page {
  padding: 0;
}

.generator-page h1 {
  margin-bottom: 24px;
  font-size: 24px;
  font-weight: 700;
}

.generator-layout {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 24px;
  min-height: calc(100vh - 200px);
}

/* Left Panel */
.settings-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: fit-content;
}

.settings-panel h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: var(--text-primary);
}

.generate-btn {
  width: 100%;
  padding: 14px 24px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 8px;
}

.generate-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.generate-btn:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

/* Right Panel */
.status-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.status-section,
.history-section {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 24px;
}

.status-section h2,
.history-section h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 16px 0;
  color: var(--text-primary);
}

.empty-status {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 60px 24px;
  text-align: center;
  color: var(--text-secondary);
}

/* Results */
.results-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  flex-direction: column;
  padding: 16px 24px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  min-width: 120px;
}

.stat-card.success .stat-value {
  color: #4CAF50;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: var(--text-primary);
}

.stat-value.error {
  color: #f44336;
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.results-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.btn {
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
  display: inline-block;
  border: none;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-secondary {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}

.btn-secondary:hover {
  border-color: var(--accent);
}

/* History */
.empty-history {
  color: var(--text-secondary);
  text-align: center;
  padding: 24px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.history-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.history-framework {
  font-weight: 600;
  color: var(--text-primary);
  text-transform: uppercase;
  font-size: 12px;
}

.history-date {
  font-size: 12px;
  color: var(--text-secondary);
}

.history-meta {
  font-size: 13px;
  color: var(--text-secondary);
}

.history-actions {
  display: flex;
  gap: 8px;
}

.btn-icon {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: background 0.2s;
}

.btn-icon:hover {
  background: var(--bg-card);
}

@media (max-width: 1024px) {
  .generator-layout {
    grid-template-columns: 1fr;
  }

  .settings-panel {
    order: 1;
  }

  .status-panel {
    order: 2;
  }
}
</style>
