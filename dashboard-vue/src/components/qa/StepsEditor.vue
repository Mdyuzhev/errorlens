<template>
  <div class="steps-editor">
    <table class="steps-table">
      <thead>
        <tr>
          <th class="col-num">#</th>
          <th class="col-action">Action</th>
          <th class="col-expected">Expected Result</th>
          <th class="col-data">Data</th>
          <th class="col-del"></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(step, idx) in localSteps"
          :key="step._key"
          class="step-row"
          :class="{ 'drag-over': dragOverIdx === idx }"
          draggable="true"
          @dragstart="onDragStart(idx, $event)"
          @dragover.prevent="onDragOver(idx)"
          @dragleave="onDragLeave"
          @drop="onDrop(idx)"
          @dragend="onDragEnd"
        >
          <td class="col-num">
            <span class="step-num">{{ idx + 1 }}</span>
          </td>
          <td class="col-action">
            <textarea
              v-model="step.action"
              class="cell-input"
              placeholder="Step action..."
              rows="1"
              @input="autoResize($event); emitUpdate()"
              @keydown.tab="handleTab(idx, 'action', $event)"
            />
          </td>
          <td class="col-expected">
            <textarea
              v-model="step.expected"
              class="cell-input"
              placeholder="Expected result..."
              rows="1"
              @input="autoResize($event); emitUpdate()"
              @keydown.tab="handleTab(idx, 'expected', $event)"
            />
          </td>
          <td class="col-data">
            <div
              v-if="looksLikeCode(step.data) && focusedDataIdx !== idx"
              class="data-code-preview"
              @click="focusedDataIdx = idx"
            >
              <pre class="data-pre"><code ref="codeRefs" v-text="step.data"></code></pre>
            </div>
            <textarea
              v-else
              v-model="step.data"
              class="cell-input"
              placeholder="Test data..."
              rows="1"
              @input="autoResize($event); emitUpdate()"
              @keydown.tab="handleTab(idx, 'data', $event)"
              @blur="focusedDataIdx = null"
              @vue:mounted="focusedDataIdx === idx && $el.focus()"
            />
          </td>
          <td class="col-del">
            <button class="btn-del" @click="removeStep(idx)" title="Delete step">&times;</button>
          </td>
        </tr>
      </tbody>
    </table>

    <button class="btn-add-step" @click="addStep">+ Step</button>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'

let keyCounter = 0

const props = defineProps({
  modelValue: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue'])

const focusedDataIdx = ref(null)

function makeStep(s = {}) {
  return {
    _key: ++keyCounter,
    action: s.action || '',
    expected: s.expected || '',
    data: s.data || ''
  }
}

const localSteps = ref(props.modelValue.map(makeStep))

watch(() => props.modelValue, (val) => {
  if (JSON.stringify(stripKeys(localSteps.value)) !== JSON.stringify(val)) {
    localSteps.value = val.map(makeStep)
  }
}, { deep: true })

watch(() => props.modelValue, async () => {
  await nextTick()
  document.querySelectorAll('.steps-editor .cell-input').forEach(el => {
    el.style.height = 'auto'
    el.style.height = el.scrollHeight + 'px'
  })
  highlightAllPreviews()
}, { deep: true })

function stripKeys(steps) {
  return steps.map(({ action, expected, data }) => ({ action, expected, data }))
}

function emitUpdate() {
  emit('update:modelValue', stripKeys(localSteps.value))
}

function addStep() {
  localSteps.value.push(makeStep())
  emitUpdate()
}

function removeStep(idx) {
  localSteps.value.splice(idx, 1)
  emitUpdate()
}

function handleTab(idx, field, e) {
  if (field === 'data' && idx === localSteps.value.length - 1 && !e.shiftKey) {
    e.preventDefault()
    addStep()
  }
}

function autoResize(e) {
  const el = e.target
  el.style.height = 'auto'
  el.style.height = el.scrollHeight + 'px'
}

function looksLikeCode(value) {
  if (!value || value.length < 4) return false
  const trimmed = value.trim()
  return (
    (trimmed.startsWith('{') && trimmed.endsWith('}')) ||
    (trimmed.startsWith('[') && trimmed.endsWith(']')) ||
    (trimmed.includes('\n') && (trimmed.includes('=') || trimmed.includes(':')))
  )
}

// --- highlight.js (same pattern as CodeBlock.vue) ---
let hljsLoaded = null

function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve()
      return
    }
    const script = document.createElement('script')
    script.src = src
    script.onload = resolve
    script.onerror = reject
    document.head.appendChild(script)
  })
}

function isDarkTheme() {
  return !document.body.classList.contains('theme-light')
}

const HLJS_CSS_DARK  = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css'
const HLJS_CSS_LIGHT = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css'
const HLJS_CSS_ID    = 'hljs-theme-css'

function applyHljsTheme() {
  const href = isDarkTheme() ? HLJS_CSS_DARK : HLJS_CSS_LIGHT
  let link = document.getElementById(HLJS_CSS_ID)
  if (!link) {
    link = document.createElement('link')
    link.id   = HLJS_CSS_ID
    link.rel  = 'stylesheet'
    document.head.appendChild(link)
  }
  if (link.href !== href) {
    link.href = href
  }
}

async function loadHljs() {
  if (window.hljs) {
    applyHljsTheme()
    return window.hljs
  }
  if (!hljsLoaded) {
    hljsLoaded = loadScript(
      'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js'
    )
  }
  await hljsLoaded
  applyHljsTheme()
  return window.hljs
}

async function highlightAllPreviews() {
  await nextTick()
  try {
    const hljs = await loadHljs()
    document.querySelectorAll('.steps-editor .data-pre code').forEach(el => {
      el.removeAttribute('data-highlighted')
      hljs.highlightElement(el)
    })
  } catch (err) {
    console.warn('[StepsEditor] highlight.js load failed:', err.message)
  }
}

// Drag & drop
const dragIdx = ref(null)
const dragOverIdx = ref(null)

function onDragStart(idx, e) {
  dragIdx.value = idx
  e.dataTransfer.effectAllowed = 'move'
}

function onDragOver(idx) {
  dragOverIdx.value = idx
}

function onDragLeave() {
  dragOverIdx.value = null
}

function onDrop(idx) {
  dragOverIdx.value = null
  if (dragIdx.value === null || dragIdx.value === idx) return
  const item = localSteps.value.splice(dragIdx.value, 1)[0]
  localSteps.value.splice(idx, 0, item)
  dragIdx.value = null
  emitUpdate()
}

function onDragEnd() {
  dragIdx.value = null
  dragOverIdx.value = null
}

onMounted(async () => {
  await nextTick()
  document.querySelectorAll('.steps-editor .cell-input').forEach(el => {
    el.style.height = 'auto'
    el.style.height = el.scrollHeight + 'px'
  })
  highlightAllPreviews()
})
</script>

<style scoped>
.steps-editor {
  width: 100%;
}

.steps-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.steps-table thead th {
  padding: 8px 10px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-secondary);
  text-align: left;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.col-num { width: 40px; }
.col-action { width: 35%; }
.col-expected { width: 30%; }
.col-data { width: 20%; }
.col-del { width: 36px; }

.step-row {
  cursor: grab;
  transition: background 0.1s;
}
.step-row:hover {
  background: var(--bg-tertiary);
}
.step-row.drag-over {
  border-top: 2px solid var(--accent);
}

.step-row td {
  padding: 6px 10px;
  vertical-align: top;
  border-bottom: 1px solid var(--border-color);
}

.step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 4px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
}

.cell-input {
  width: 100%;
  min-height: 28px;
  padding: 6px 8px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
  color: var(--text-primary);
  font-size: 13px;
  font-family: inherit;
  resize: none;
  overflow: hidden;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
}
.cell-input:focus {
  border-color: var(--accent);
  background: var(--bg-secondary);
}
.cell-input::placeholder {
  color: var(--text-secondary);
}

.btn-del {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 18px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  line-height: 1;
  transition: all 0.15s;
}
.btn-del:hover {
  color: var(--error-color, #ef4444);
  background: var(--error-bg, rgba(239, 68, 68, 0.15));
}

.btn-add-step {
  width: 100%;
  padding: 10px;
  margin-top: 4px;
  background: none;
  border: 1px dashed var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-add-step:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.data-code-preview {
  cursor: pointer;
  border-radius: 4px;
  padding: 2px;
  transition: background 0.15s;
}
.data-code-preview:hover {
  background: var(--bg-tertiary);
}

.data-pre {
  margin: 0;
  padding: 4px 6px;
  font-size: 12px;
  line-height: 1.4;
  background: var(--bg-secondary);
  border-radius: 4px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.data-pre code {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
  background: transparent;
  padding: 0;
}
</style>
