<template>
  <div class="vars-overlay" @click.self="$emit('close')">
    <div class="vars-panel">
      <div class="vars-header">
        <h3 class="vars-title">Variables &amp; Environments</h3>
        <button class="vars-close" @click="$emit('close')">&times;</button>
      </div>

      <div class="vars-body">
        <!-- Left: scopes -->
        <div class="vars-scopes">
          <div class="vars-scopes-title">Scopes</div>
          <div
            v-for="scope in scopes"
            :key="scope"
            class="vars-scope-item"
            :class="{ active: selectedScope === scope }"
            @click="selectedScope = scope"
          >
            {{ scopeLabel(scope) }}
          </div>
          <button class="vars-add-env" @click="addEnvironment">+ Add Environment</button>
        </div>

        <!-- Right: variables table -->
        <div class="vars-table-wrap">
          <div class="vars-table-header">
            <span class="vars-col-check"></span>
            <span class="vars-col-name">Name</span>
            <span class="vars-col-value">Value</span>
            <span class="vars-col-type">Type</span>
            <span class="vars-col-del"></span>
          </div>
          <div class="vars-rows">
            <div v-for="(v, i) in scopeVars" :key="i" class="vars-row">
              <input
                type="checkbox"
                :checked="v.is_enabled"
                class="vars-check"
                @change="v.is_enabled = $event.target.checked; save(v)"
              />
              <input
                v-model="v.name"
                class="vars-input vars-name"
                placeholder="variable_name"
                @blur="save(v)"
              />
              <input
                v-model="v.value"
                class="vars-input vars-value"
                :type="v.is_secret ? 'password' : 'text'"
                placeholder="value"
                @blur="save(v)"
              />
              <select v-model="v.is_secret" class="vars-type-select" @change="save(v)">
                <option :value="false">Default</option>
                <option :value="true">Secret</option>
              </select>
              <button class="vars-del-btn" @click="remove(v, i)" title="Delete">&times;</button>
            </div>
            <button class="vars-add-row" @click="addVariable">+ Add Variable</button>
          </div>
        </div>
      </div>

      <!-- Bottom: resolved preview -->
      <div class="vars-preview">
        <div class="vars-preview-title">Resolved Variables (merged)</div>
        <div class="vars-preview-list">
          <span v-for="(val, key) in store.resolvedVariables" :key="key" class="vars-preview-tag">
            {{ key }}={{ val }}
          </span>
          <span v-if="!Object.keys(store.resolvedVariables).length" class="vars-preview-empty">
            No variables resolved
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { usePechkinStore } from '@/stores/pechkin'

const props = defineProps({
  collectionId: { type: String, required: true }
})

defineEmits(['close'])

const store = usePechkinStore()
const selectedScope = ref('global')
const rawVars = ref([])

onMounted(async () => {
  try {
    const data = await store.listRawVariables(props.collectionId)
    rawVars.value = data.map(v => ({ ...v }))
  } catch {
    rawVars.value = []
  }
})

const scopes = computed(() => {
  const set = new Set(['global', 'collection'])
  for (const v of rawVars.value) {
    if (v.scope) set.add(v.scope)
  }
  return Array.from(set)
})

const scopeVars = computed(() => {
  return rawVars.value.filter(v => v.scope === selectedScope.value)
})

function scopeLabel(scope) {
  if (scope === 'global') return 'Global'
  if (scope === 'collection') return 'Collection'
  return scope.charAt(0).toUpperCase() + scope.slice(1)
}

function addEnvironment() {
  const name = prompt('Environment name (e.g. dev, staging, prod):')
  if (!name || !name.trim()) return
  const normalized = name.trim().toLowerCase()
  if (scopes.value.includes(normalized)) return
  rawVars.value.push({
    scope: normalized,
    name: '',
    value: '',
    is_secret: false,
    is_enabled: true
  })
  selectedScope.value = normalized
}

function addVariable() {
  rawVars.value.push({
    scope: selectedScope.value,
    name: '',
    value: '',
    is_secret: false,
    is_enabled: true
  })
}

async function save(v) {
  if (!v.name) return
  try {
    const result = await store.upsertVariable(props.collectionId, {
      scope: v.scope,
      name: v.name,
      value: v.value,
      is_secret: v.is_secret,
      is_enabled: v.is_enabled
    })
    if (result?.id) v.id = result.id
  } catch {
    // silent — variable may be incomplete
  }
}

async function remove(v, index) {
  if (v.id) {
    try {
      await store.deleteVariable(props.collectionId, v.id)
    } catch {
      // silent
    }
  }
  rawVars.value.splice(index, 1)
}
</script>

<style scoped>
.vars-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.vars-panel {
  width: 800px;
  max-height: 500px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.vars-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-color);
}

.vars-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.vars-close {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 20px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}

.vars-close:hover {
  color: var(--error);
}

.vars-body {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.vars-scopes {
  width: 200px;
  border-right: 1px solid var(--border-color);
  padding: 10px 0;
  overflow-y: auto;
  flex-shrink: 0;
}

.vars-scopes-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--text-secondary);
  padding: 4px 14px 8px;
  letter-spacing: 0.5px;
}

.vars-scope-item {
  padding: 8px 14px;
  font-size: 13px;
  color: var(--text-primary);
  cursor: pointer;
  transition: background 0.12s;
}

.vars-scope-item:hover {
  background: var(--bg-tertiary);
}

.vars-scope-item.active {
  background: var(--accent-muted, rgba(124, 58, 237, 0.1));
  color: var(--accent);
  font-weight: 600;
}

.vars-add-env {
  display: block;
  width: calc(100% - 20px);
  margin: 8px 10px 0;
  padding: 6px;
  background: none;
  border: 1px dashed var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  text-align: center;
}

.vars-add-env:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.vars-table-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.vars-table-header {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--text-secondary);
  letter-spacing: 0.5px;
  gap: 8px;
}

.vars-col-check { width: 24px; flex-shrink: 0; }
.vars-col-name { flex: 1; }
.vars-col-value { flex: 1.5; }
.vars-col-type { width: 80px; flex-shrink: 0; }
.vars-col-del { width: 28px; flex-shrink: 0; }

.vars-rows {
  flex: 1;
  overflow-y: auto;
  padding: 6px 12px;
}

.vars-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.vars-check {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  accent-color: var(--accent);
  cursor: pointer;
}

.vars-input {
  padding: 5px 8px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 13px;
  font-family: monospace;
  outline: none;
}

.vars-input:focus {
  border-color: var(--accent);
}

.vars-name { flex: 1; min-width: 0; }
.vars-value { flex: 1.5; min-width: 0; }

.vars-type-select {
  width: 80px;
  padding: 5px 4px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 12px;
  cursor: pointer;
  flex-shrink: 0;
}

.vars-type-select option {
  background: var(--bg-card);
  color: var(--text-primary);
}

.vars-del-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;
  border-radius: 4px;
  flex-shrink: 0;
}

.vars-del-btn:hover {
  background: var(--bg-tertiary);
  color: var(--error);
}

.vars-add-row {
  display: block;
  width: 100%;
  margin-top: 6px;
  padding: 6px;
  background: none;
  border: 1px dashed var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  text-align: center;
}

.vars-add-row:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.vars-preview {
  border-top: 1px solid var(--border-color);
  padding: 10px 14px;
}

.vars-preview-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--text-secondary);
  margin-bottom: 6px;
  letter-spacing: 0.5px;
}

.vars-preview-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.vars-preview-tag {
  padding: 2px 8px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  font-size: 12px;
  font-family: monospace;
  color: var(--text-primary);
}

.vars-preview-empty {
  font-size: 12px;
  color: var(--text-secondary);
  font-style: italic;
}
</style>
