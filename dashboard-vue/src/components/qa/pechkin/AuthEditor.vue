<template>
  <div class="auth-editor">
    <select v-model="auth.type" class="auth-type-select" @change="emitUpdate">
      <option value="none">No Auth</option>
      <option value="bearer">Bearer Token</option>
      <option value="basic">Basic Auth</option>
      <option value="api_key">API Key</option>
    </select>

    <div v-if="auth.type === 'bearer'" class="auth-fields">
      <label class="auth-label">Token</label>
      <input v-model="auth.token" class="auth-input" placeholder="{{token}} or paste" @input="emitUpdate" />
    </div>

    <div v-if="auth.type === 'basic'" class="auth-fields">
      <label class="auth-label">Username</label>
      <input v-model="auth.username" class="auth-input" @input="emitUpdate" />
      <label class="auth-label">Password</label>
      <input v-model="auth.password" class="auth-input" type="password" @input="emitUpdate" />
    </div>

    <div v-if="auth.type === 'api_key'" class="auth-fields">
      <label class="auth-label">Key</label>
      <input v-model="auth.key" class="auth-input" placeholder="X-API-Key" @input="emitUpdate" />
      <label class="auth-label">Value</label>
      <input v-model="auth.value" class="auth-input" @input="emitUpdate" />
      <label class="auth-label">Add to</label>
      <select v-model="auth.in" class="auth-type-select" @change="emitUpdate">
        <option value="header">Header</option>
        <option value="query">Query</option>
      </select>
    </div>
  </div>
</template>

<script setup>
import { reactive, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Object, default: () => ({ type: 'none' }) }
})
const emit = defineEmits(['update:modelValue'])

const auth = reactive({ type: 'none', ...props.modelValue })

watch(() => props.modelValue, (val) => {
  Object.assign(auth, { type: 'none', ...val })
}, { deep: true })

function emitUpdate() {
  emit('update:modelValue', { ...auth })
}
</script>

<style scoped>
.auth-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 8px 0;
}
.auth-type-select {
  padding: 6px 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  max-width: 200px;
}
.auth-type-select:focus {
  border-color: var(--accent);
}
.auth-fields {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}
.auth-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}
.auth-input {
  padding: 6px 10px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
}
.auth-input:focus {
  border-color: var(--accent);
}
</style>
