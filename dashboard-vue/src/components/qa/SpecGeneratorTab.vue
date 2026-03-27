<template>
  <div class="spec-generator">

    <!-- Mode switcher -->
    <div class="mode-switcher">
      <button
        class="mode-btn"
        :class="{ active: mode === 'static' }"
        @click="mode = 'static'"
      >
        Static
        <span class="mode-hint">instant, no LLM</span>
      </button>
      <button
        class="mode-btn"
        :class="{ active: mode === 'llm' }"
        @click="mode = 'llm'"
      >
        LLM
        <span class="mode-hint">smarter, slower</span>
      </button>
      <button
        class="mode-btn"
        :class="{ active: mode === 'eva' }"
        @click="mode = 'eva'"
      >
        EVA
        <span class="mode-hint">test quality score</span>
      </button>
      <button
        class="mode-btn"
        :class="{ active: mode === 'pechkin' }"
        @click="mode = 'pechkin'"
      >
        Pechkin
        <span class="mode-hint">HTTP client</span>
      </button>
    </div>

    <!-- Pechkin mode -->
    <PechkinTab v-if="mode === 'pechkin' && currentProjectId" :project-id="currentProjectId" />

    <!-- LLM mode: existing generator -->
    <component v-else-if="mode === 'llm'" :is="GeneratorView" />

    <!-- Static mode -->
    <EvaTab v-else-if="mode === 'eva'" />


    <div v-else-if="mode === 'static'" class="static-mode">
      <div class="generator-layout">

        <!-- Left panel -->
        <div class="left-panel">
          <section class="panel-section">
            <h3 class="section-title">Specification</h3>
            <SpecInput @spec-ready="onSpecReady" @spec-cleared="onSpecCleared" />
          </section>

          <section v-if="endpoints.length > 0" class="panel-section">
            <h3 class="section-title">Endpoints</h3>
            <EndpointSelector
              :endpoints="endpoints"
              :loading="parsing"
              @selection-changed="selectedIds = $event"
            />
          </section>

          <section class="panel-section">
            <h3 class="section-title">Options</h3>
            <div class="config-grid">
              <label class="config-label">Framework</label>
              <select v-model="config.framework" class="config-select">
                <option value="pytest">pytest</option>
                <option value="rest-assured">REST Assured</option>
                <option value="postman">Postman</option>
              </select>

              <label class="config-label">Base URL</label>
              <input
                v-model="config.baseUrl"
                class="config-input"
                placeholder="https://api.example.com"
              />

              <label class="config-label">Negative tests</label>
              <label class="toggle">
                <input type="checkbox" v-model="config.generateNegativeTests" />
                <span class="slider"></span>
              </label>

              <label class="config-label">Placeholders</label>
              <label class="toggle">
                <input type="checkbox" v-model="config.usePlaceholders" />
                <span class="slider"></span>
              </label>
            </div>
          </section>

          <div v-if="error" class="error-box">{{ error }}</div>

          <button
            class="btn-generate"
            :disabled="!canGenerate || generating"
            @click="generate"
          >
            <span v-if="generating">Generating...</span>
            <span v-else>Generate Tests</span>
          </button>
        </div>

        <!-- Right panel -->
        <div class="right-panel">
          <!-- Empty state -->
          <div v-if="!result && !generating" class="empty-result">
            <div class="empty-icon">⚡</div>
            <p>Paste an OpenAPI spec and select endpoints to generate tests instantly</p>
          </div>

          <!-- Generating spinner -->
          <div v-else-if="generating" class="generating-state">
            <div class="spinner"></div>
            <p>Generating tests...</p>
          </div>

          <!-- Results -->
          <div v-else-if="result" class="results">
            <!-- Stats row -->
            <div class="stats-row">
              <div class="stat">
                <span class="stat-num">{{ result.stats.total_endpoints }}</span>
                <span class="stat-lbl">endpoints</span>
              </div>
              <div class="stat">
                <span class="stat-num">{{ result.stats.total_tests }}</span>
                <span class="stat-lbl">tests</span>
              </div>
              <div class="stat stat-success">
                <span class="stat-num">{{ result.stats.positive_tests }}</span>
                <span class="stat-lbl">positive</span>
              </div>
              <div class="stat stat-warning">
                <span class="stat-num">{{ result.stats.negative_tests }}</span>
                <span class="stat-lbl">negative</span>
              </div>
              <div class="stat stat-accent">
                <span class="stat-num">{{ result.stats.assertions }}</span>
                <span class="stat-lbl">assertions</span>
              </div>
            </div>

            <!-- File tabs -->
            <div class="file-tabs" v-if="result.files.length > 1">
              <button
                v-for="f in result.files"
                :key="f.filename"
                class="file-tab"
                :class="{ active: activeFile === f.filename }"
                @click="activeFile = f.filename"
              >{{ f.filename }}</button>
            </div>

            <!-- Code preview -->
            <div class="code-wrapper">
              <div class="code-toolbar">
                <span class="code-filename">{{ currentFile?.filename }}</span>
                <button class="btn-toolbar" @click="copyCode">
                  {{ copied ? 'Copied!' : 'Copy' }}
                </button>
                <button class="btn-toolbar" @click="downloadFile">Download</button>
              </div>
              <pre class="code-block"><code>{{ currentFile?.content }}</code></pre>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, defineAsyncComponent, onMounted } from 'vue'
import SpecInput from '@/components/qa/SpecInput.vue'
import EndpointSelector from '@/components/qa/EndpointSelector.vue'
import EvaTab from '@/components/qa/EvaTab.vue'
import PechkinTab from '@/components/qa/PechkinTab.vue'
import { specGenApi, projectsApi } from '@/services/api'

const GeneratorView = defineAsyncComponent(() => import('@/views/GeneratorView.vue'))

const props = defineProps({
  projectId: { type: String, default: null }
})

const currentProjectId = ref(props.projectId)

onMounted(async () => {
  if (!currentProjectId.value) {
    try {
      const res = await projectsApi.list()
      if (res.data.length > 0) currentProjectId.value = res.data[0].id
    } catch (e) {
      // no projects
    }
  }
})

const mode = ref('static')
const parsing = ref(false)
const generating = ref(false)
const specText = ref(null)
const endpoints = ref([])
const selectedIds = ref([])
const config = ref({
  framework: 'pytest',
  baseUrl: '',
  generateNegativeTests: true,
  usePlaceholders: true,
})
const result = ref(null)
const activeFile = ref(null)
const copied = ref(false)
const error = ref(null)

const canGenerate = computed(() =>
  specText.value && selectedIds.value.length > 0 && !parsing.value
)

const currentFile = computed(() =>
  result.value?.files.find(f => f.filename === activeFile.value)
  || result.value?.files[0]
)

async function onSpecReady(text) {
  specText.value = text
  parsing.value = true
  error.value = null
  try {
    const isUrl = text.startsWith('http://') || text.startsWith('https://')
    const payload = isUrl ? { spec_url: text } : { spec: text }
    const resp = await specGenApi.parseSpec(payload)
    endpoints.value = resp.data.endpoints
    config.value.baseUrl = config.value.baseUrl || resp.data.base_url
    selectedIds.value = resp.data.endpoints.map(e => e.id)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to parse spec'
    endpoints.value = []
  } finally {
    parsing.value = false
  }
}

function onSpecCleared() {
  specText.value = null
  endpoints.value = []
  selectedIds.value = []
  result.value = null
  error.value = null
}

async function generate() {
  generating.value = true
  error.value = null
  try {
    const isUrl = specText.value?.startsWith('http://') || specText.value?.startsWith('https://')
    const payload = {
      ...(isUrl ? { spec_url: specText.value } : { spec: specText.value }),
      endpoint_ids: selectedIds.value,
      config: {
        framework: config.value.framework,
        base_url: config.value.baseUrl,
        generate_negative_tests: config.value.generateNegativeTests,
        use_placeholders: config.value.usePlaceholders,
      }
    }
    const resp = await specGenApi.generateTests(payload)
    result.value = resp.data
    activeFile.value = resp.data.files[0]?.filename || null
  } catch (e) {
    error.value = e.response?.data?.detail || 'Generation failed'
  } finally {
    generating.value = false
  }
}

function copyCode() {
  navigator.clipboard.writeText(currentFile.value?.content || '')
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

function downloadFile() {
  const f = currentFile.value
  if (!f) return
  const blob = new Blob([f.content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = f.filename
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.spec-generator {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mode-switcher {
  display: flex;
  gap: 8px;
}

.mode-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 24px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.mode-btn:hover {
  color: var(--text-primary);
}
.mode-btn.active {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}
.mode-btn.active .mode-hint {
  color: rgba(255, 255, 255, 0.7);
}

.mode-hint {
  font-size: 11px;
  font-weight: 400;
  color: var(--text-secondary);
  margin-top: 2px;
}

.generator-layout {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 24px;
  min-height: 500px;
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-section {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 16px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px;
}

.config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 12px;
  align-items: center;
}

.config-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.config-select,
.config-input {
  padding: 6px 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 12px;
  outline: none;
}
.config-select:focus,
.config-input:focus {
  border-color: var(--accent);
}

/* Toggle switch */
.toggle {
  position: relative;
  display: inline-block;
  width: 36px;
  height: 20px;
  cursor: pointer;
}
.toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  inset: 0;
  background: var(--bg-tertiary);
  border-radius: 20px;
  transition: 0.2s;
}
.slider::before {
  content: '';
  position: absolute;
  height: 14px;
  width: 14px;
  left: 3px;
  bottom: 3px;
  background: var(--text-secondary);
  border-radius: 50%;
  transition: 0.2s;
}
.toggle input:checked + .slider {
  background: var(--accent);
}
.toggle input:checked + .slider::before {
  transform: translateX(16px);
  background: white;
}

.error-box {
  background: var(--accent-muted);
  border: 1px solid var(--error);
  border-radius: 8px;
  padding: 12px;
  color: var(--error);
  font-size: 13px;
}

.btn-generate {
  padding: 10px 20px;
  background: var(--accent);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
}
.btn-generate:hover {
  opacity: 0.85;
}
.btn-generate:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.right-panel {
  min-height: 400px;
}

.empty-result,
.generating-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 300px;
  color: var(--text-secondary);
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-color);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 12px;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.stats-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.stat {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 10px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 70px;
}

.stat-num {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}

.stat-lbl {
  font-size: 11px;
  color: var(--text-secondary);
}

.stat-success .stat-num { color: var(--success); }
.stat-warning .stat-num { color: var(--warning); }
.stat-accent .stat-num { color: var(--accent); }

.file-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 8px;
}

.file-tab {
  padding: 6px 14px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px 6px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
}
.file-tab.active {
  background: var(--bg-card);
  color: var(--text-primary);
  border-bottom-color: var(--bg-card);
}

.code-wrapper {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.code-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.code-filename {
  flex: 1;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
  font-family: monospace;
}

.btn-toolbar {
  padding: 4px 10px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
}
.btn-toolbar:hover {
  color: var(--text-primary);
}

.code-block {
  margin: 0;
  padding: 16px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: monospace;
  font-size: 12px;
  line-height: 1.6;
  overflow-x: auto;
  max-height: 600px;
  overflow-y: auto;
  white-space: pre;
}

@media (max-width: 900px) {
  .generator-layout {
    grid-template-columns: 1fr;
  }
}
</style>
