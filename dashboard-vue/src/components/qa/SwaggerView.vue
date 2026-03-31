<template>
  <div class="swagger-view">
    <!-- Toolbar -->
    <div class="swagger-toolbar">
      <div class="swagger-toolbar-left">
        <span class="swagger-label">⚡ API Explorer</span>
        <span class="swagger-count">{{ endpointCount }} endpoints</span>
        <select v-model="activeTag" class="swagger-tag-select" @change="applyFilter">
          <option value="">All API</option>
          <option value="pechkin">Pechkin (HTTP Client)</option>
          <option value="tasks">Tasks / Issues</option>
          <option value="articles">Articles</option>
          <option value="testcases">Test Cases</option>
          <option value="sprints">Sprints</option>
          <option value="qa">QA Dashboard</option>
          <option value="auth">Auth</option>
          <option value="entities">Entity Links</option>
        </select>
      </div>
      <div class="swagger-toolbar-right">
        <span v-if="authStatus" class="swagger-auth-badge" :class="authStatus">
          {{ authStatus === 'ok' ? '🔒 Авторизован' : '🔓 Не авторизован' }}
        </span>
        <button class="swagger-ext-btn" @click="openExternal" title="Открыть в новой вкладке">
          ↗ Открыть
        </button>
      </div>
    </div>

    <!-- Swagger UI container -->
    <div id="swagger-ui-container" class="swagger-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  projectId: { type: String, default: null }
})

const activeTag = ref('')
const authStatus = ref(null)
const endpointCount = ref(0)
let swaggerInstance = null

const OPENAPI_URL = '/api/openapi.json'
const SWAGGER_CDN_JS = 'https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.11.0/swagger-ui-bundle.min.js'
const SWAGGER_CDN_CSS = 'https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.11.0/swagger-ui.min.css'

function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) { resolve(); return }
    const s = document.createElement('script')
    s.src = src
    s.onload = resolve
    s.onerror = reject
    document.head.appendChild(s)
  })
}

function loadStyle(href) {
  if (document.querySelector(`link[href="${href}"]`)) return
  const l = document.createElement('link')
  l.rel = 'stylesheet'
  l.href = href
  document.head.appendChild(l)
}

function getToken() {
  return localStorage.getItem('access_token')
}

async function initSwagger() {
  await loadScript(SWAGGER_CDN_JS)
  loadStyle(SWAGGER_CDN_CSS)

  const token = getToken()
  authStatus.value = token ? 'ok' : 'none'

  const container = document.getElementById('swagger-ui-container')
  if (!container || !window.SwaggerUIBundle) return

  swaggerInstance = window.SwaggerUIBundle({
    url: OPENAPI_URL,
    dom_id: '#swagger-ui-container',
    presets: [
      window.SwaggerUIBundle.presets.apis,
      window.SwaggerUIBundle.SwaggerUIStandalonePreset,
    ],
    layout: 'BaseLayout',
    deepLinking: true,
    displayRequestDuration: true,
    defaultModelsExpandDepth: 0,
    defaultModelExpandDepth: 2,
    docExpansion: 'list',      // collapsed by default
    filter: activeTag.value || true,  // show all or filter by tag

    // Auto-authorize with JWT
    requestInterceptor: (request) => {
      const t = getToken()
      if (t && !request.headers['Authorization']) {
        request.headers['Authorization'] = `Bearer ${t}`
      }
      return request
    },

    onComplete: () => {
      // Pre-authorize in UI
      const t = getToken()
      if (t && swaggerInstance) {
        swaggerInstance.preauthorizeApiKey('Bearer', t)
      }
      // Count endpoints
      try {
        const spec = swaggerInstance.getState()?.spec?.json
        if (spec?.paths) {
          let count = 0
          for (const path of Object.values(spec.paths)) {
            count += Object.keys(path).filter(m =>
              ['get','post','put','patch','delete'].includes(m)
            ).length
          }
          endpointCount.value = count
        }
      } catch { /* silent */ }
    },
  })
}

function applyFilter() {
  if (!swaggerInstance) return
  // Reload with filter
  if (swaggerInstance.layoutActions?.updateFilter) {
    swaggerInstance.layoutActions.updateFilter(activeTag.value)
  } else {
    // Fallback: re-init with filter
    initSwagger()
  }
}

function openExternal() {
  window.open('/api/docs', '_blank')
}

onMounted(() => {
  initSwagger()
})

onBeforeUnmount(() => {
  swaggerInstance = null
})

watch(activeTag, applyFilter)
</script>

<style scoped>
.swagger-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-primary);
}

.swagger-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
  gap: 12px;
}

.swagger-toolbar-left,
.swagger-toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.swagger-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.swagger-count {
  font-size: 11px;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  padding: 2px 8px;
  border-radius: 10px;
}

.swagger-tag-select {
  padding: 5px 10px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 12px;
  outline: none;
  cursor: pointer;
}
.swagger-tag-select:focus { border-color: var(--accent); }

.swagger-auth-badge {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 10px;
  font-weight: 500;
}
.swagger-auth-badge.ok {
  background: rgba(16, 185, 129, 0.15);
  color: var(--success);
}
.swagger-auth-badge.none {
  background: rgba(245, 158, 11, 0.15);
  color: var(--warning);
}

.swagger-ext-btn {
  padding: 5px 12px;
  background: none;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.swagger-ext-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.swagger-container {
  flex: 1;
  overflow-y: auto;
  background: white;  /* Swagger UI requires white background */
}

/* Override Swagger UI minimum styles for dark container */
:global(.swagger-ui .topbar) { display: none !important; }
:global(.swagger-ui) { font-size: 13px; }
</style>
