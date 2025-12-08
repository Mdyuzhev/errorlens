<template>
  <div class="input-tabs">
    <div class="tabs-header">
      <button
        :class="{ active: modelValue === 'swagger' }"
        @click="selectTab('swagger')"
      >
        📄 Swagger/OpenAPI
      </button>
      <button
        :class="{ active: modelValue === 'session' }"
        @click="selectTab('session')"
      >
        📹 Из сессии
      </button>
      <button
        :class="{ active: modelValue === 'url' }"
        @click="selectTab('url')"
      >
        🔗 URL endpoint
      </button>
    </div>

    <div class="tab-content">
      <SwaggerUpload
        v-if="modelValue === 'swagger'"
        @file-selected="handleSwaggerFile"
        @file-removed="handleClear"
      />
      <SessionSelector
        v-if="modelValue === 'session'"
        @session-selected="handleSessionSelected"
      />
      <UrlInput
        v-if="modelValue === 'url'"
        @endpoints-added="handleEndpointsAdded"
        @cleared="handleClear"
      />
    </div>

    <div v-if="hasInput" class="input-ready-indicator">
      ✓ Входные данные готовы
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import SwaggerUpload from './SwaggerUpload.vue'
import SessionSelector from './SessionSelector.vue'
import UrlInput from './UrlInput.vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: 'swagger'
  }
})

const emit = defineEmits(['update:modelValue', 'input-ready', 'input-cleared'])

const hasInput = ref(false)

onMounted(() => {
  const savedTab = localStorage.getItem('generator_input_tab')
  if (savedTab && ['swagger', 'session', 'url'].includes(savedTab)) {
    emit('update:modelValue', savedTab)
  }
})

function selectTab(tab) {
  emit('update:modelValue', tab)
  localStorage.setItem('generator_input_tab', tab)
  hasInput.value = false
  emit('input-cleared')
}

function handleSwaggerFile(file) {
  hasInput.value = true
  emit('input-ready', { type: 'swagger', data: file })
}

function handleSessionSelected(session) {
  hasInput.value = true
  emit('input-ready', { type: 'session', data: session })
}

function handleEndpointsAdded(endpoints) {
  hasInput.value = true
  emit('input-ready', { type: 'url', data: endpoints })
}

function handleClear() {
  hasInput.value = false
  emit('input-cleared')
}
</script>

<style scoped>
.input-tabs {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tabs-header {
  display: flex;
  gap: 8px;
  border-bottom: 2px solid var(--border-color);
  padding-bottom: 8px;
}

.tabs-header button {
  flex: 1;
  padding: 12px 16px;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s;
}

.tabs-header button:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.tabs-header button.active {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  font-weight: 600;
}

.tab-content {
  min-height: 200px;
}

.input-ready-indicator {
  padding: 10px 16px;
  background: rgba(76, 175, 80, 0.1);
  color: #4CAF50;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  text-align: center;
}
</style>
