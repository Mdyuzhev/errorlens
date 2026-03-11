<template>
  <div class="gitlab-connections">
    <!-- Project selector -->
    <div class="section-header">
      <div class="project-select-group">
        <label>Project:</label>
        <select v-model="selectedProjectId" class="project-select">
          <option value="" disabled>Select project</option>
          <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
      </div>
      <button
        class="btn btn-primary"
        @click="showModal = true"
        :disabled="!selectedProjectId"
      >
        + Add GitLab Connection
      </button>
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="loading">Loading connections...</div>

    <!-- Empty state -->
    <div v-else-if="!store.connections.length && selectedProjectId" class="empty-state">
      <p>No GitLab connections configured for this project.</p>
      <p class="hint">Add a connection to integrate with your GitLab instance.</p>
    </div>

    <!-- Connection cards -->
    <div v-else class="connections-grid">
      <div v-for="conn in store.connections" :key="conn.id" class="connection-card">
        <div class="card-top">
          <div class="card-info">
            <div class="card-name">{{ conn.name }}</div>
            <div class="card-url">{{ conn.url }}</div>
          </div>
          <div class="card-status">
            <span
              class="status-dot"
              :class="{
                green: conn.last_check_ok === true,
                red: conn.last_check_ok === false,
                gray: conn.last_check_ok == null,
              }"
              :title="statusTitle(conn)"
            ></span>
          </div>
        </div>

        <div class="card-meta">
          <span v-if="conn.last_checked_at" class="meta-item">
            Checked: {{ formatDate(conn.last_checked_at) }}
          </span>
          <span v-else class="meta-item">Never checked</span>
          <span class="meta-item">Token: {{ conn.token_masked }}</span>
        </div>

        <div class="card-actions">
          <button
            class="btn btn-sm btn-secondary"
            @click="handleCheck(conn.id)"
            :disabled="store.checking.has(conn.id)"
          >
            {{ store.checking.has(conn.id) ? 'Checking...' : 'Check' }}
          </button>
          <button class="btn btn-sm btn-secondary" @click="editConnection(conn)">Edit</button>
          <button class="btn btn-sm btn-danger" @click="handleDelete(conn.id)">Delete</button>
        </div>
      </div>
    </div>

    <!-- Modal -->
    <GitLabConnectionModal
      v-if="showModal"
      :connection="editingConnection"
      :project-id="selectedProjectId"
      @close="closeModal"
      @saved="closeModal"
    />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { projectsApi } from '@/services/api'
import { useGitLabStore } from '@/stores/gitlab'
import GitLabConnectionModal from './GitLabConnectionModal.vue'

const store = useGitLabStore()

const projects = ref([])
const selectedProjectId = ref('')
const showModal = ref(false)
const editingConnection = ref(null)

onMounted(async () => {
  const { data } = await projectsApi.list()
  projects.value = data
  if (data.length) {
    selectedProjectId.value = data[0].id
  }
})

watch(selectedProjectId, async (id) => {
  if (id) {
    await store.fetchConnections(id)
  }
})

async function handleCheck(id) {
  await store.checkConnection(id)
}

async function handleDelete(id) {
  if (confirm('Delete this connection?')) {
    await store.deleteConnection(id, selectedProjectId.value)
  }
}

function editConnection(conn) {
  editingConnection.value = conn
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  editingConnection.value = null
}

function statusTitle(conn) {
  if (conn.last_check_ok === true) return 'Connection OK'
  if (conn.last_check_ok === false) return 'Connection failed'
  return 'Not checked'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleString()
}
</script>

<style scoped>
.gitlab-connections {
  max-width: 800px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  gap: 16px;
}

.project-select-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.project-select-group label {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
}

.project-select {
  padding: 8px 12px;
  border: 1px solid var(--border-color, rgba(255,255,255,0.1));
  border-radius: 8px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 14px;
  min-width: 200px;
}

.loading {
  padding: 40px;
  text-align: center;
  color: var(--text-secondary);
}

.empty-state {
  padding: 40px;
  text-align: center;
  color: var(--text-secondary);
}

.empty-state .hint {
  font-size: 13px;
  opacity: 0.7;
}

.connections-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.connection-card {
  background: var(--bg-card);
  border-radius: 12px;
  padding: 16px 20px;
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}

.card-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.card-url {
  font-size: 13px;
  color: var(--text-secondary);
  font-family: monospace;
  margin-top: 2px;
}

.status-dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-top: 4px;
}

.status-dot.green { background: #4caf50; }
.status-dot.red { background: #f44336; }
.status-dot.gray { background: #9e9e9e; }

.card-meta {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.meta-item {
  font-size: 12px;
  color: var(--text-secondary);
}

.card-actions {
  display: flex;
  gap: 8px;
}

.btn {
  padding: 8px 16px;
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

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color, rgba(255,255,255,0.1));
}

.btn-danger {
  background: transparent;
  color: #f44336;
  border: 1px solid rgba(244, 67, 54, 0.3);
}

.btn-danger:hover {
  background: rgba(244, 67, 54, 0.1);
}
</style>
