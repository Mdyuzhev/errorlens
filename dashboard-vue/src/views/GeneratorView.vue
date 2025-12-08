<template>
  <div class="generator-page">
    <h1>🔧 Генератор тестов</h1>

    <div class="generator-layout">
      <!-- Left + Center: Main Content -->
      <div class="generator-main">
        <!-- Left: Input Section -->
        <div class="input-section">
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
            :disabled="!canGenerate"
            @click="startGeneration"
          >
            🚀 Генерировать
          </button>
        </div>

        <!-- Center: Output Section -->
        <div class="output-section">
          <GenerationProgress
            v-if="step === 'progress'"
            :progress="socket?.progress.value"
            :total="socket?.total.value"
            :current-endpoint="socket?.currentEndpoint.value"
            :logs="socket?.logs.value"
            :status="socket?.status.value"
          />

          <div v-else-if="step === 'results'" class="results-container">
            <div class="results-stats">
              <div class="stat-card">
                <span class="stat-value">{{ store.result?.total_endpoints }}</span>
                <span class="stat-label">Эндпоинтов</span>
              </div>
              <div class="stat-card">
                <span class="stat-value success">{{ store.result?.successful }}</span>
                <span class="stat-label">Успешно</span>
              </div>
            </div>

            <CodePreview
              title="Сгенерированные тесты"
              :code="generatedCode"
              :language="getCodeLanguage(framework)"
            />

            <div class="results-actions">
              <a :href="downloadUrl" class="download-btn" download>📥 Скачать ZIP</a>
              <button class="reset-btn" @click="reset">Новая генерация</button>
            </div>
          </div>

          <div v-else class="empty-output">
            <div style="font-size:64px">🚀</div>
            <p>Выберите входные данные и нажмите "Генерировать"</p>
          </div>
        </div>
      </div>

      <!-- Right: History Sidebar -->
      <GenerationHistory
        ref="historyRef"
        class="history-sidebar"
        @regenerate="onRegenerate"
        @redownload="onRedownload"
      />
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
import GenerationHistory from '@/components/generator/GenerationHistory.vue'

const props = defineProps({
  sessionId: {
    type: String,
    default: null
  }
})

const store = useGenerationStore()
const historyRef = ref(null)

const step = ref('input')
const inputType = ref('swagger')
const inputData = ref(null)
const framework = ref('pytest')
const provider = ref('ollama')
const model = ref('')
const generatedCode = ref('')
let socket = null

const canGenerate = computed(() => {
  return inputData.value !== null && framework.value && provider.value
})

const downloadUrl = computed(() =>
  socket?.resultId.value ? store.getDownloadUrl(socket.resultId.value) : ''
)

onMounted(async () => {
  if (props.sessionId) {
    await startFromSession(props.sessionId)
  }
})

function onInputReady(data) {
  inputData.value = data
}

function onInputCleared() {
  inputData.value = null
}

async function startGeneration() {
  if (!canGenerate.value) return

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
  }
}

async function startFromSession(sessionId) {
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
  }
}

watch(() => socket?.status.value, async (s) => {
  if (s === 'completed' && socket?.resultId.value) {
    await store.fetchResult(socket.resultId.value)
    generatedCode.value = store.result?.generated_code || ''

    if (historyRef.value) {
      historyRef.value.addToHistory({
        framework: framework.value,
        endpoints: store.result?.total_endpoints || 0,
        result_id: socket.resultId.value
      })
    }

    step.value = 'results'
  }
})

function reset() {
  step.value = 'input'
  inputData.value = null
  generatedCode.value = ''
  store.reset()
  socket = null
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

function onRegenerate(item) {
  framework.value = item.framework
  startGeneration()
}

function onRedownload(resultId) {
  const url = store.getDownloadUrl(resultId)
  window.open(url, '_blank')
}
</script>

<style scoped>
.generator-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.generator-page h1 {
  margin-bottom: 24px;
}

.generator-layout {
  display: flex;
  gap: 24px;
  flex: 1;
  min-height: 0;
}

.generator-main {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 24px;
  flex: 1;
}

.input-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  height: fit-content;
}

.output-section {
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  min-height: 500px;
}

.history-sidebar {
  width: 320px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  overflow-y: auto;
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
}

.generate-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.generate-btn:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.empty-output {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--text-secondary);
  text-align: center;
  padding: 60px 20px;
}

.empty-output p {
  margin-top: 20px;
  font-size: 16px;
}

.results-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}

.results-stats {
  display: flex;
  gap: 16px;
}

.stat-card {
  display: flex;
  flex-direction: column;
  padding: 16px 24px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  min-width: 140px;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: var(--text-primary);
}

.stat-value.success {
  color: #4CAF50;
}

.stat-label {
  font-size: 14px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.results-actions {
  display: flex;
  gap: 12px;
}

.download-btn {
  padding: 12px 24px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 600;
  display: inline-block;
  transition: all 0.2s;
}

.download-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.reset-btn {
  padding: 12px 24px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.reset-btn:hover {
  border-color: var(--accent);
  background: rgba(102, 126, 234, 0.05);
}

@media (max-width: 1400px) {
  .generator-layout {
    flex-direction: column;
  }

  .history-sidebar {
    width: 100%;
  }
}

@media (max-width: 1024px) {
  .generator-main {
    grid-template-columns: 1fr;
  }
}
</style>
