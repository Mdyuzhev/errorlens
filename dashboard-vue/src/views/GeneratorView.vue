<template>
  <div class="generator-page">
    <h1>🔧 Генератор тестов</h1>

    <!-- Step 1: Upload -->
    <div v-if="step === 'upload'" class="settings-card">
      <h2>Загрузите Swagger/OpenAPI</h2>
      <SwaggerUpload @file-selected="file = $event" @file-removed="file = null" />

      <div v-if="file" style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:20px">
        <div>
          <label>Фреймворк</label>
          <select v-model="framework">
            <option value="pytest">pytest</option>
            <option value="restassured">REST Assured</option>
          </select>
        </div>
        <div>
          <label>LLM Provider</label>
          <select v-model="provider">
            <option value="anthropic">Anthropic</option>
            <option value="openai">OpenAI</option>
            <option value="groq">Groq</option>
            <option value="ollama">Ollama</option>
          </select>
        </div>
      </div>

      <button v-if="file" class="generate-btn" @click="startGeneration" :disabled="store.loading">
        🚀 Генерировать
      </button>
    </div>

    <!-- Step 2: Progress -->
    <div v-if="step === 'progress'" class="settings-card">
      <h2>Генерация тестов</h2>
      <GenerationProgress
        :progress="socket?.progress.value"
        :total="socket?.total.value"
        :current-endpoint="socket?.currentEndpoint.value"
        :logs="socket?.logs.value"
        :status="socket?.status.value"
      />
    </div>

    <!-- Step 3: Results -->
    <div v-if="step === 'results'" class="settings-card">
      <h2>✅ Результаты</h2>
      <div style="display:flex;gap:24px;margin-bottom:20px">
        <div>
          <span style="font-size:32px;font-weight:bold">{{ store.result?.total_endpoints }}</span><br>
          <span style="color:var(--text-secondary)">Эндпоинтов</span>
        </div>
        <div>
          <span style="font-size:32px;font-weight:bold;color:#4CAF50">{{ store.result?.successful }}</span><br>
          <span style="color:var(--text-secondary)">Успешно</span>
        </div>
      </div>
      <div style="display:flex;gap:12px">
        <a :href="downloadUrl" class="download-btn" download>📥 Скачать ZIP</a>
        <button @click="reset" style="padding:12px 24px;background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:8px;cursor:pointer">
          Новая генерация
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useGenerationStore } from '@/stores/generation'
import { useGenerationSocket } from '@/composables/useGenerationSocket'
import SwaggerUpload from '@/components/generator/SwaggerUpload.vue'
import GenerationProgress from '@/components/generator/GenerationProgress.vue'

const props = defineProps({
  sessionId: {
    type: String,
    default: null
  }
})

const store = useGenerationStore()
const step = ref('upload')
const file = ref(null)
const framework = ref('pytest')
const provider = ref('anthropic')
let socket = null

const downloadUrl = computed(() =>
  socket?.resultId.value ? store.getDownloadUrl(socket.resultId.value) : ''
)

onMounted(async () => {
  if (props.sessionId) {
    await startFromSession(props.sessionId)
  }
})

async function startGeneration() {
  try {
    const response = await store.startFromSwagger(file.value, {
      framework: framework.value,
      provider: provider.value
    })
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
      provider: provider.value
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
    step.value = 'results'
  }
})

function reset() {
  step.value = 'upload'
  file.value = null
  store.reset()
  socket = null
}
</script>

<style scoped>
.generator-page h1 {
  margin-bottom: 24px;
}

.settings-card {
  background: var(--bg-card);
  padding: 24px;
  border-radius: 12px;
  max-width: 800px;
}

.settings-card h2 {
  font-size: 18px;
  margin: 0 0 20px;
}

.settings-card label {
  display: block;
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.settings-card select {
  width: 100%;
  padding: 10px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
}

.generate-btn {
  width: 100%;
  margin-top: 20px;
  padding: 14px 24px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
}

.generate-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.download-btn {
  padding: 12px 24px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 600;
  display: inline-block;
}
</style>
