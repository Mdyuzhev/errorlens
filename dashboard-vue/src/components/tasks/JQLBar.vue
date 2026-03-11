<template>
  <div class="jql-bar">
    <div class="jql-input-wrapper">
      <svg class="jql-icon" viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
        <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
      </svg>

      <input
        ref="inputRef"
        v-model="jqlInput"
        class="jql-input"
        :class="{ invalid: !isValid && jqlInput.trim() }"
        placeholder="JQL: status = todo AND priority = high"
        @input="onInput"
        @keydown="onKeydown"
        @focus="showSuggestions = true"
        @blur="hideSuggestions"
      />

      <div class="jql-status" :class="statusClass" :title="statusTitle">
        <span class="status-dot"></span>
      </div>

      <button v-if="jqlInput" class="jql-btn-clear" title="Clear" @click="onClear">
        &times;
      </button>

      <button class="jql-btn-ai" title="Smart Search (AI)" @click="onAI">
        ✨
      </button>

      <button class="jql-btn-search" :disabled="!isValid || !jqlInput.trim()" @click="onSearch">
        Search
      </button>

      <button class="jql-btn-save" title="Save Filter" @click="onSave" :disabled="!jqlInput.trim()">
        <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14">
          <path d="M5 4a2 2 0 012-2h6a2 2 0 012 2v14l-5-2.5L5 18V4z" />
        </svg>
      </button>
    </div>

    <!-- Autocomplete dropdown -->
    <div v-if="showSuggestions && suggestions.length" class="jql-autocomplete">
      <div
        v-for="(s, i) in suggestions"
        :key="s.value"
        class="suggestion-item"
        :class="{ active: i === activeSuggestion }"
        @mousedown.prevent="applySuggestion(s)"
      >
        <span class="suggestion-value">{{ s.value }}</span>
        <span v-if="s.label && s.label !== s.value" class="suggestion-label">{{ s.label }}</span>
      </div>
    </div>

    <!-- Context hint -->
    <div v-if="contextHint && !syntaxError && jqlInput" class="jql-hint">
      {{ contextHint }}
    </div>

    <!-- Error message -->
    <div v-if="syntaxError && jqlInput.trim()" class="jql-error">
      {{ displayError }}
    </div>

    <!-- Save filter modal -->
    <div v-if="showSaveModal" class="save-modal-overlay" @click.self="showSaveModal = false">
      <div class="save-modal">
        <h3>Save Filter</h3>
        <input v-model="filterName" placeholder="Filter name" @keydown.enter="confirmSave" />
        <label class="shared-check">
          <input type="checkbox" v-model="filterShared" /> Share with project
        </label>
        <div class="save-actions">
          <button class="btn btn-secondary" @click="showSaveModal = false">Cancel</button>
          <button class="btn btn-primary" @click="confirmSave" :disabled="!filterName.trim()">Save</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useJqlStore } from '@/stores/jql'

const props = defineProps({
  projectId: { type: String, default: null },
})

const emit = defineEmits(['search', 'clear'])

const jqlStore = useJqlStore()

const FIELD_OPERATOR_MAP = {
  priority: ['=', '!=', 'in', 'not in', 'IS EMPTY'],
  status:   ['=', '!=', 'in', 'not in', 'IS EMPTY'],
  type:     ['=', '!=', 'in', 'not in'],
  severity: ['=', '!=', 'in', 'not in', 'IS EMPTY'],
  assignee: ['=', '!=', 'in', 'IS EMPTY', 'IS NOT EMPTY'],
  reporter: ['=', '!=', 'in', 'IS EMPTY', 'IS NOT EMPTY'],
  labels:   ['=', 'in', 'not in', 'IS EMPTY', 'IS NOT EMPTY'],
  created:  ['>', '<', '>=', '<=', '=', 'WAS', 'CHANGED'],
  updated:  ['>', '<', '>=', '<=', '=', 'CHANGED'],
  due:      ['>', '<', '>=', '<=', '=', 'IS EMPTY'],
  title:    ['~', '!~', '=', '!=', 'IS EMPTY'],
}

const inputRef = ref(null)
const jqlInput = ref('')
const showSuggestions = ref(false)
const activeSuggestion = ref(-1)
const showSaveModal = ref(false)
const filterName = ref('')
const filterShared = ref(false)
const suggestionRefs = ref([])

let debounceTimer = null

const isValid = computed(() => jqlStore.isValid)
const syntaxError = computed(() => jqlStore.syntaxError)
const suggestions = computed(() => jqlStore.suggestions)

const statusClass = computed(() => {
  if (!jqlInput.value.trim()) return 'neutral'
  return isValid.value ? 'valid' : 'invalid'
})

const displayError = computed(() => {
  if (!syntaxError.value) return null
  const msg = syntaxError.value.message || ''
  if (msg.includes('Expected one of') || msg.includes('Unexpected')) {
    return 'Invalid JQL syntax'
  }
  return msg
})

const statusTitle = computed(() => {
  if (!jqlInput.value.trim()) return 'Enter JQL query'
  return isValid.value ? 'Valid JQL' : displayError.value || 'Invalid JQL'
})

function onInput() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    jqlStore.validateJQL(jqlInput.value)
    analyzeContext()
  }, 800)
}

function analyzeContext() {
  const text = jqlInput.value
  const cursor = inputRef.value?.selectionStart || text.length
  const before = text.substring(0, cursor)
  const tokens = before.trim().split(/\s+/).filter(Boolean)

  if (!tokens.length) {
    jqlStore.fetchSuggestions('', '', props.projectId)
    return
  }

  const lastToken = tokens[tokens.length - 1]
  const prevToken = tokens[tokens.length - 2]
  const OPERATORS = ['=', '!=', '>', '<', '>=', '<=', '~', '!~', 'in', 'not', 'is']
  const CONJUNCTIONS = ['and', 'or', 'not']

  // After AND/OR — suggest fields
  if (CONJUNCTIONS.includes(lastToken.toLowerCase())) {
    jqlStore.fetchSuggestions('', '', props.projectId)
    return
  }

  // Last token is operator — suggest values for previous field
  if (OPERATORS.includes(lastToken.toLowerCase())) {
    const fieldToken = tokens[tokens.length - 2]
    if (fieldToken && !OPERATORS.includes(fieldToken.toLowerCase()) && !CONJUNCTIONS.includes(fieldToken.toLowerCase())) {
      jqlStore.fetchSuggestions(fieldToken, '', props.projectId)
    }
    return
  }

  // Previous token is operator — user is typing a value
  if (prevToken && OPERATORS.includes(prevToken.toLowerCase())) {
    const fieldToken = tokens[tokens.length - 3]
    if (fieldToken) {
      jqlStore.fetchSuggestions(fieldToken, lastToken, props.projectId)
    }
    return
  }

  // Otherwise — user is typing a field name
  jqlStore.fetchSuggestions('', lastToken, props.projectId)
}

function showOperatorsFor(field) {
  const ops = FIELD_OPERATOR_MAP[field.toLowerCase()] || ['=', '!=', 'in']
  jqlStore.suggestions = ops.map(op => ({ value: op, label: '', type: 'operator' }))
  showSuggestions.value = true
  activeSuggestion.value = -1
}

function applySuggestion(s) {
  const text = jqlInput.value
  const cursor = inputRef.value?.selectionStart || text.length
  const before = text.substring(0, cursor)
  const after = text.substring(cursor)
  const tokens = before.trim().split(/\s+/).filter(Boolean)
  const OPERATORS = ['=', '!=', '>', '<', '>=', '<=', '~', '!~', 'in', 'not', 'is']
  const FIELDS = Object.keys(FIELD_OPERATOR_MAP)

  let value = s.value
  if (value.includes(' ') && !value.startsWith('IS ')) value = `"${value}"`

  const prevToken = tokens[tokens.length - 2]
  const lastToken = tokens[tokens.length - 1]

  let newBefore
  if (OPERATORS.includes(lastToken?.toLowerCase())) {
    // After operator — append value
    newBefore = before.trimEnd() + ' ' + value
  } else if (prevToken && OPERATORS.includes(prevToken.toLowerCase())) {
    // Replace partial value
    newBefore = tokens.slice(0, -1).join(' ') + ' ' + value
  } else {
    // Replace partial field name
    newBefore = tokens.slice(0, -1).join(' ')
    if (newBefore) newBefore += ' '
    newBefore += value
  }

  jqlInput.value = newBefore + ' ' + after.trimStart()
  showSuggestions.value = false
  jqlStore.suggestions = []

  // If we just inserted a field name, show operators for it
  const insertedField = value.toLowerCase()
  if (FIELDS.includes(insertedField)) {
    nextTick(() => showOperatorsFor(insertedField))
  } else {
    nextTick(() => analyzeContext())
  }
}

function onKeydown(e) {
  const hasSuggestions = showSuggestions.value && suggestions.value.length > 0

  if (e.key === 'ArrowDown' && hasSuggestions) {
    e.preventDefault()
    activeSuggestion.value = (activeSuggestion.value + 1) % suggestions.value.length
    scrollToActive()
  } else if (e.key === 'ArrowUp' && hasSuggestions) {
    e.preventDefault()
    activeSuggestion.value = activeSuggestion.value <= 0
      ? suggestions.value.length - 1
      : activeSuggestion.value - 1
    scrollToActive()
  } else if (e.key === 'Tab' && hasSuggestions) {
    e.preventDefault()
    const idx = activeSuggestion.value >= 0 ? activeSuggestion.value : 0
    applySuggestion(suggestions.value[idx])
  } else if (e.key === 'Enter') {
    if (hasSuggestions && activeSuggestion.value >= 0) {
      e.preventDefault()
      applySuggestion(suggestions.value[activeSuggestion.value])
    } else {
      onSearch()
    }
  } else if (e.key === 'Escape') {
    showSuggestions.value = false
    activeSuggestion.value = -1
  }
}

function scrollToActive() {
  nextTick(() => {
    const container = inputRef.value?.closest('.jql-bar')?.querySelector('.jql-autocomplete')
    if (!container) return
    const activeEl = container.querySelector('.suggestion-item.active')
    if (activeEl) activeEl.scrollIntoView({ block: 'nearest' })
  })
}

const contextHint = computed(() => {
  const tokens = jqlInput.value.trim().split(/\s+/).filter(Boolean)
  if (!tokens.length) return 'Например: priority = high AND type = bug'
  const last = tokens[tokens.length - 1]?.toLowerCase()
  const prev = tokens[tokens.length - 2]?.toLowerCase()
  const OPERATORS = ['=', '!=', '>', '<', '>=', '<=', '~', '!~', 'in', 'not']
  const CONJUNCTIONS = ['and', 'or']

  if (CONJUNCTIONS.includes(last)) return 'field = value'

  if (prev && OPERATORS.includes(prev)) {
    const field = tokens.length >= 3 ? tokens[tokens.length - 3]?.toLowerCase() : prev
    if (['priority', 'severity'].includes(field)) {
      return `${field} ${prev} high | medium | low | critical`
    }
    if (['status'].includes(field)) {
      return `${field} ${prev} todo | in_progress | review | done`
    }
    return `${field} ${prev} value`
  }

  const FIELDS = Object.keys(FIELD_OPERATOR_MAP)
  if (FIELDS.includes(last) && !OPERATORS.includes(last)) {
    return `${last} = value`
  }

  return ''
})

function hideSuggestions() {
  setTimeout(() => { showSuggestions.value = false }, 200)
}

function onSearch() {
  if (!jqlInput.value.trim() || !isValid.value) return
  jqlStore.executeJQL(jqlInput.value, props.projectId)
  emit('search', jqlInput.value)
  showSuggestions.value = false
}

function onClear() {
  jqlInput.value = ''
  jqlStore.clearJQL()
  emit('clear')
}

async function onAI() {
  const text = jqlInput.value.trim()
  if (!text) return
  const result = await jqlStore.askAI(text, props.projectId)
  if (result) {
    jqlInput.value = result
    jqlStore.validateJQL(result)
  }
}

function onSave() {
  if (!jqlInput.value.trim()) return
  filterName.value = ''
  filterShared.value = false
  showSaveModal.value = true
}

async function confirmSave() {
  if (!filterName.value.trim()) return
  await jqlStore.saveFilter(filterName.value, jqlInput.value, props.projectId, filterShared.value)
  showSaveModal.value = false
}

// Apply external JQL (from saved filters)
function setJQL(jql) {
  jqlInput.value = jql
  jqlStore.validateJQL(jql)
  onSearch()
}

defineExpose({ setJQL })
</script>

<style scoped>
.jql-bar {
  position: relative;
  margin-bottom: 16px;
}

.jql-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-card);
  border: 1px solid var(--bg-secondary);
  border-radius: 8px;
  padding: 6px 12px;
  transition: border-color 0.2s;
}

.jql-input-wrapper:focus-within {
  border-color: var(--accent);
}

.jql-icon {
  color: var(--text-secondary);
  flex-shrink: 0;
}

.jql-input {
  flex: 1;
  border: none;
  background: none;
  outline: none;
  color: var(--text-primary);
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  padding: 4px 0;
}

.jql-input::placeholder {
  color: var(--text-secondary);
  opacity: 0.6;
}

.jql-input.invalid {
  color: #ef4444;
}

.jql-status {
  flex-shrink: 0;
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.jql-status.neutral .status-dot { background: var(--text-secondary); opacity: 0.3; }
.jql-status.valid .status-dot { background: #10b981; }
.jql-status.invalid .status-dot { background: #ef4444; }

.jql-btn-clear {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}

.jql-btn-ai {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 4px;
  border-radius: 4px;
  transition: background 0.2s;
}

.jql-btn-ai:hover { background: var(--bg-secondary); }

.jql-btn-search {
  background: var(--accent);
  color: white;
  border: none;
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}

.jql-btn-search:disabled { opacity: 0.5; cursor: not-allowed; }
.jql-btn-search:not(:disabled):hover { opacity: 0.9; }

.jql-btn-save {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  transition: background 0.2s;
  display: flex;
  align-items: center;
}

.jql-btn-save:hover { background: var(--bg-secondary); }
.jql-btn-save:disabled { opacity: 0.3; cursor: not-allowed; }

.jql-autocomplete {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--bg-card);
  border: 1px solid var(--bg-secondary);
  border-radius: 8px;
  margin-top: 4px;
  max-height: 200px;
  overflow-y: auto;
  z-index: 100;
  box-shadow: var(--shadow-dropdown);
}

.suggestion-item {
  padding: 8px 12px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  transition: background 0.1s;
}

.suggestion-item:hover,
.suggestion-item.active {
  background: var(--bg-secondary);
}

.suggestion-value { font-family: monospace; }
.suggestion-label { color: var(--text-secondary); font-size: 12px; }

.jql-hint {
  font-size: 11px;
  color: var(--text-secondary);
  opacity: 0.6;
  padding: 2px 36px;
  font-family: 'JetBrains Mono', monospace;
}

.jql-error {
  color: #ef4444;
  font-size: 12px;
  margin-top: 4px;
  padding-left: 36px;
}

.save-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1100;
}

.save-modal {
  background: var(--bg-card);
  border-radius: 12px;
  padding: 20px;
  width: 360px;
}

.save-modal h3 { margin: 0 0 12px; font-size: 16px; }

.save-modal input[type="text"],
.save-modal input:not([type]) {
  width: 100%;
  margin-bottom: 12px;
}

.shared-check {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.save-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
</style>
