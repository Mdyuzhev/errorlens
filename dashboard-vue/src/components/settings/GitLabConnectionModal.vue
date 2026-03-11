<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2>{{ isEdit ? 'Edit' : 'Add' }} GitLab Connection</h2>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <form @submit.prevent="handleSave">
        <div class="form-group">
          <label>Name</label>
          <input
            v-model="form.name"
            type="text"
            placeholder="Production GitLab"
            required
          />
        </div>

        <div class="form-group">
          <label>URL</label>
          <input
            v-model="form.url"
            type="text"
            placeholder="https://gitlab.company.com"
            required
          />
        </div>

        <div class="form-group">
          <label>Personal Access Token</label>
          <input
            v-model="form.token"
            type="password"
            :placeholder="isEdit ? 'Leave empty to keep current' : 'glpat-...'"
            :required="!isEdit"
          />
          <span class="hint">Scope: api, read_repository</span>
        </div>

        <div class="form-group toggle-group">
          <label>Verify SSL</label>
          <label class="toggle-switch">
            <input type="checkbox" v-model="form.verify_ssl" />
            <span class="toggle-slider"></span>
          </label>
          <span class="hint">Disable for self-hosted with self-signed certs</span>
        </div>

        <!-- Test Connection -->
        <div class="test-section" v-if="testResult !== null">
          <div :class="['test-result', testResult.ok ? 'success' : 'error']">
            <span v-if="testResult.ok">Connected as {{ testResult.username }}</span>
            <span v-else>{{ testResult.error }}</span>
          </div>
        </div>

        <div class="modal-actions">
          <button
            type="button"
            class="btn btn-secondary"
            @click="handleTest"
            :disabled="testing || !form.url || (!form.token && !isEdit)"
          >
            {{ testing ? 'Testing...' : 'Test Connection' }}
          </button>
          <div class="spacer"></div>
          <button type="button" class="btn btn-ghost" @click="$emit('close')">Cancel</button>
          <button type="submit" class="btn btn-primary" :disabled="saving">
            {{ saving ? 'Saving...' : 'Save' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { gitlabApi } from '@/services/api'
import { useGitLabStore } from '@/stores/gitlab'

const props = defineProps({
  connection: { type: Object, default: null },
  projectId: { type: String, required: true },
})

const emit = defineEmits(['close', 'saved'])

const store = useGitLabStore()
const isEdit = !!props.connection

const form = reactive({
  name: props.connection?.name || '',
  url: props.connection?.url || '',
  token: '',
  verify_ssl: props.connection?.verify_ssl ?? true,
})

const saving = ref(false)
const testing = ref(false)
const testResult = ref(null)

async function handleTest() {
  testing.value = true
  testResult.value = null
  try {
    if (isEdit && !form.token) {
      // Test existing connection
      const { data } = await gitlabApi.checkConnection(props.connection.id)
      testResult.value = data
    } else {
      // Create temp connection, test, then delete — or just save and test
      // For simplicity: save first then test, or test inline
      // We'll create, test, and use the result
      testResult.value = { ok: false, error: 'Save the connection first, then use Check' }
    }
  } catch (err) {
    testResult.value = { ok: false, error: err.response?.data?.detail || 'Connection failed' }
  } finally {
    testing.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    const payload = {
      name: form.name,
      url: form.url,
      verify_ssl: form.verify_ssl,
    }
    if (form.token) {
      payload.token = form.token
    }

    if (isEdit) {
      await store.updateConnection(props.connection.id, payload, props.projectId)
    } else {
      payload.token = form.token
      await store.createConnection(props.projectId, payload)
    }
    emit('saved')
    emit('close')
  } catch (err) {
    testResult.value = { ok: false, error: err.response?.data?.detail || 'Failed to save' }
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-card);
  border-radius: 12px;
  width: 480px;
  max-width: 90vw;
  max-height: 90vh;
  overflow-y: auto;
  padding: 24px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.modal-header h2 {
  margin: 0;
  font-size: 18px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: var(--text-secondary);
  cursor: pointer;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.form-group input[type="text"],
.form-group input[type="password"] {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color, rgba(255,255,255,0.1));
  border-radius: 8px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 14px;
  box-sizing: border-box;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
}

.hint {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-secondary);
  opacity: 0.7;
}

.toggle-group {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.toggle-group label:first-child {
  margin-bottom: 0;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  cursor: pointer;
}

.toggle-switch input {
  display: none;
}

.toggle-slider {
  display: inline-block;
  width: 40px;
  height: 22px;
  background: var(--bg-secondary);
  border-radius: 11px;
  position: relative;
  transition: all 0.3s;
  border: 1px solid var(--border-color, rgba(255,255,255,0.1));
}

.toggle-slider::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 14px;
  height: 14px;
  background: var(--text-secondary);
  border-radius: 50%;
  transition: all 0.3s;
}

.toggle-switch input:checked + .toggle-slider {
  background: #667eea;
}

.toggle-switch input:checked + .toggle-slider::after {
  left: 21px;
  background: white;
}

.test-section {
  margin-bottom: 16px;
}

.test-result {
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
}

.test-result.success {
  background: rgba(76, 175, 80, 0.15);
  color: #4caf50;
}

.test-result.error {
  background: rgba(244, 67, 54, 0.15);
  color: #f44336;
}

.modal-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 20px;
}

.spacer {
  flex: 1;
}

.btn {
  padding: 10px 18px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color, rgba(255,255,255,0.1));
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
}
</style>
