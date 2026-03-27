<template>
  <div class="spec-input">
    <div class="input-tabs">
      <button
        v-for="t in ['paste', 'file', 'url']"
        :key="t"
        class="input-tab"
        :class="{ active: tab === t }"
        @click="tab = t"
      >{{ t.charAt(0).toUpperCase() + t.slice(1) }}</button>
    </div>

    <!-- Paste tab -->
    <div v-if="tab === 'paste'" class="tab-content">
      <textarea
        v-model="pasteText"
        class="spec-textarea"
        placeholder="Paste OpenAPI YAML or JSON..."
        rows="8"
      />
      <button v-if="pasteText" class="btn-clear" @click="clearPaste">Clear</button>
    </div>

    <!-- File tab -->
    <div v-else-if="tab === 'file'" class="tab-content">
      <div
        class="drop-zone"
        :class="{ dragging }"
        @dragover.prevent="dragging = true"
        @dragleave="dragging = false"
        @drop.prevent="onDrop"
      >
        <input
          type="file"
          ref="fileInput"
          accept=".yaml,.yml,.json"
          @change="onFileChange"
          hidden
        />
        <template v-if="!fileName">
          <span class="drop-text">Drop YAML/JSON or </span>
          <button class="btn-browse" @click="$refs.fileInput.click()">Browse</button>
        </template>
        <template v-else>
          <span class="file-name">{{ fileName }}</span>
          <button class="btn-clear-sm" @click="clearFile">&times;</button>
        </template>
      </div>
    </div>

    <!-- URL tab -->
    <div v-else-if="tab === 'url'" class="tab-content">
      <div class="url-row">
        <input
          type="text"
          v-model="specUrl"
          class="url-input"
          placeholder="https://api.example.com/openapi.yaml"
          @keydown.enter="loadFromUrl"
        />
        <button
          class="btn-load"
          :disabled="!specUrl || loading"
          @click="loadFromUrl"
        >{{ loading ? 'Loading...' : 'Load' }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const emit = defineEmits(['spec-ready', 'spec-cleared'])

const tab = ref('paste')
const pasteText = ref('')
const specUrl = ref('')
const fileName = ref('')
const loading = ref(false)
const dragging = ref(false)
const fileInput = ref(null)

let debounceTimer = null

watch(pasteText, (val) => {
  clearTimeout(debounceTimer)
  if (!val || val.length < 50) return
  debounceTimer = setTimeout(() => {
    emit('spec-ready', val)
  }, 300)
})

function clearPaste() {
  pasteText.value = ''
  emit('spec-cleared')
}

function onFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  readFile(file)
}

function onDrop(e) {
  dragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (!file) return
  readFile(file)
}

function readFile(file) {
  fileName.value = file.name
  const reader = new FileReader()
  reader.onload = (e) => {
    emit('spec-ready', e.target.result)
  }
  reader.readAsText(file)
}

function clearFile() {
  fileName.value = ''
  if (fileInput.value) fileInput.value.value = ''
  emit('spec-cleared')
}

function loadFromUrl() {
  if (!specUrl.value) return
  loading.value = true
  // Backend will fetch the URL — just emit the URL
  emit('spec-ready', specUrl.value)
  loading.value = false
}
</script>

<style scoped>
.spec-input {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-tabs {
  display: flex;
  gap: 4px;
}

.input-tab {
  padding: 6px 14px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}
.input-tab:hover {
  color: var(--text-primary);
}
.input-tab.active {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}

.tab-content {
  position: relative;
}

.spec-textarea {
  width: 100%;
  min-height: 200px;
  padding: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-family: monospace;
  font-size: 12px;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
}
.spec-textarea:focus {
  border-color: var(--accent);
}
.spec-textarea::placeholder {
  color: var(--text-secondary);
}

.btn-clear {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 4px 10px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
}
.btn-clear:hover {
  color: var(--error);
}

.drop-zone {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 120px;
  border: 2px dashed var(--border-color);
  border-radius: 8px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 13px;
  transition: border-color 0.15s;
}
.drop-zone.dragging {
  border-color: var(--accent);
  background: var(--accent-muted);
}

.btn-browse {
  padding: 4px 12px;
  background: var(--accent);
  border: none;
  border-radius: 4px;
  color: white;
  font-size: 12px;
  cursor: pointer;
}

.file-name {
  color: var(--text-primary);
  font-weight: 500;
}

.btn-clear-sm {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 18px;
  cursor: pointer;
  padding: 2px 6px;
}
.btn-clear-sm:hover {
  color: var(--error);
}

.url-row {
  display: flex;
  gap: 8px;
}

.url-input {
  flex: 1;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
}
.url-input:focus {
  border-color: var(--accent);
}
.url-input::placeholder {
  color: var(--text-secondary);
}

.btn-load {
  padding: 8px 16px;
  background: var(--accent);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
}
.btn-load:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
