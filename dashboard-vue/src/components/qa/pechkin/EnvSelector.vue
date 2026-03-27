<template>
  <div class="env-selector">
    <span class="env-label">Env:</span>
    <select v-model="store.activeEnv" class="env-select">
      <option value="">No environment</option>
      <option value="collection">Collection</option>
      <option v-for="env in environments" :key="env" :value="env">{{ env }}</option>
    </select>
    <button class="env-manage-btn" @click="showPanel = true" title="Manage environments">
      &#9881;
    </button>
    <VariablesPanel
      v-if="showPanel"
      :collection-id="collectionId"
      @close="showPanel = false"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { usePechkinStore } from '@/stores/pechkin'
import VariablesPanel from './VariablesPanel.vue'

const props = defineProps({
  collectionId: { type: String, required: true }
})

const store = usePechkinStore()
const showPanel = ref(false)

const environments = computed(() => {
  const vars = store.variables[props.collectionId]
  if (!vars) return []
  const reserved = new Set(['global', 'collection'])
  return Object.keys(vars).filter(s => !reserved.has(s)).sort()
})
</script>

<style scoped>
.env-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.env-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.env-select {
  padding: 4px 8px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  min-width: 140px;
  outline: none;
}

.env-select:focus {
  border-color: var(--accent);
}

.env-select option {
  background: var(--bg-card);
  color: var(--text-primary);
}

.env-manage-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
}

.env-manage-btn:hover {
  background: var(--bg-tertiary);
  color: var(--accent);
  border-color: var(--accent);
}
</style>
