<template>
  <div class="testcases-page">
    <div class="page-header">
      <h1>Test Cases</h1>
      <button class="btn btn-primary" @click="showEditor = true; editingTestCase = null">
        + New Test Case
      </button>
    </div>

    <div class="testcases-layout">
      <!-- Sidebar: Folder Tree -->
      <aside class="sidebar">
        <FolderTree
          :folders="treeFolders"
          :selected-folder-id="store.selectedFolderId"
          :expanded-ids="store.expandedFolders"
          @select="handleSelectFolder"
          @toggle="store.toggleFolder($event)"
          @create="handleCreateFolder"
          @rename="handleRenameFolder"
          @delete="handleDeleteFolder"
          @drop="handleDrop"
        />
      </aside>

      <!-- Main Area -->
      <div class="main-area">
        <!-- Filters -->
        <div class="filters">
          <select v-model="filters.status" @change="loadTestCases">
            <option value="">All Statuses</option>
            <option value="Draft">Draft</option>
            <option value="Ready">Ready</option>
            <option value="Approved">Approved</option>
          </select>

          <select v-model="filters.priority" @change="loadTestCases">
            <option value="">All Priorities</option>
            <option value="Critical">Critical</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
        </div>

        <!-- Test Cases Grid -->
        <div v-if="loading" class="loading">
          <div class="spinner"></div>
        </div>

        <div v-else-if="testCases.length === 0" class="empty-state">
          <p>No test cases yet</p>
          <p class="hint">Create from session or manually</p>
        </div>

        <div v-else class="testcases-grid" data-testid="testcases-list">
          <div
            v-for="tc in testCases"
            :key="tc.id"
            class="testcase-card"
            :draggable="true"
            @click="openTestCase(tc)"
            @dragstart="onTestCaseDragStart($event, tc)"
          >
            <div class="tc-header">
              <span class="tc-priority" :class="tc.priority?.toLowerCase()">
                {{ tc.priority }}
              </span>
              <span class="tc-status" :class="tc.status?.toLowerCase()">
                {{ tc.status }}
              </span>
            </div>
            <h3 class="tc-title">{{ tc.title }}</h3>
            <p class="tc-description">{{ tc.description || 'No description' }}</p>
            <div class="tc-footer">
              <span class="tc-steps">{{ tc.steps?.length || 0 }} steps</span>
              <span class="tc-automation" :class="tc.automation_status?.toLowerCase().replace(' ', '-')">
                {{ tc.automation_status }}
              </span>
            </div>
            <div v-if="tc.tags?.length" class="tc-tags">
              <span v-for="tag in tc.tags.slice(0, 3)" :key="tag" class="tag">{{ tag }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Editor Modal -->
    <div v-if="showEditor" class="modal-overlay" @click.self="closeEditor">
      <div class="modal-content modal-large">
        <button class="modal-close" @click="closeEditor">&times;</button>

        <h2>{{ editingTestCase ? 'Edit Test Case' : 'New Test Case' }}</h2>

        <form @submit.prevent="saveTestCase">
          <div class="form-group">
            <label>Title *</label>
            <input v-model="form.title" required placeholder="Test case title" />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>Priority</label>
              <select v-model="form.priority">
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
                <option value="Critical">Critical</option>
              </select>
            </div>

            <div class="form-group">
              <label>Status</label>
              <select v-model="form.status">
                <option value="Draft">Draft</option>
                <option value="Ready">Ready</option>
                <option value="Approved">Approved</option>
              </select>
            </div>

            <div class="form-group">
              <label>Automation</label>
              <select v-model="form.automation_status">
                <option value="Manual">Manual</option>
                <option value="Automated">Automated</option>
                <option value="NotAutomatable">Not Automatable</option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label>Description</label>
            <textarea v-model="form.description" rows="2" placeholder="Brief description"></textarea>
          </div>

          <div class="form-group">
            <label>Preconditions</label>
            <textarea v-model="form.preconditions" rows="2" placeholder="What needs to be set up before test"></textarea>
          </div>

          <div class="form-group">
            <label>Steps</label>
            <div v-for="(step, idx) in form.steps" :key="idx" class="step-row">
              <span class="step-num">{{ idx + 1 }}</span>
              <input v-model="step.action" placeholder="Action" class="step-action" />
              <input v-model="step.expected" placeholder="Expected result" class="step-expected" />
              <button type="button" class="btn-icon" @click="removeStep(idx)">x</button>
            </div>
            <button type="button" class="btn btn-secondary btn-sm" @click="addStep">+ Add Step</button>
          </div>

          <div class="form-group">
            <label>Postconditions</label>
            <textarea v-model="form.postconditions" rows="2" placeholder="Expected state after test"></textarea>
          </div>

          <div class="form-group">
            <label>Tags (comma-separated)</label>
            <input v-model="tagsInput" placeholder="api, smoke, regression" />
          </div>

          <div class="form-actions">
            <button v-if="editingTestCase" type="button" class="btn btn-danger" @click="deleteTestCase">
              Delete
            </button>
            <button type="button" class="btn btn-secondary" @click="closeEditor">Cancel</button>
            <button type="submit" class="btn btn-primary">Save</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useTestCasesStore } from '@/stores/testcases'
import FolderTree from '@/components/testcases/FolderTree.vue'

const store = useTestCasesStore()

const showEditor = ref(false)
const editingTestCase = ref(null)

const filters = ref({
  status: '',
  priority: ''
})

const form = ref({
  title: '',
  description: '',
  preconditions: '',
  postconditions: '',
  priority: 'Medium',
  status: 'Draft',
  automation_status: 'Manual',
  steps: [{ action: '', expected: '', testData: '' }]
})

const tagsInput = ref('')

const loading = computed(() => store.loading)
const testCases = computed(() => store.testCases)
const treeFolders = computed(() => store.treeFolders)

async function loadTestCases() {
  store.filters = { ...filters.value, folder: '' }
  await store.fetchTestCases()
}

function openTestCase(tc) {
  editingTestCase.value = tc
  form.value = {
    title: tc.title || '',
    description: tc.description || '',
    preconditions: tc.preconditions || '',
    postconditions: tc.postconditions || '',
    priority: tc.priority || 'Medium',
    status: tc.status || 'Draft',
    automation_status: tc.automation_status || 'Manual',
    steps: tc.steps?.length ? [...tc.steps] : [{ action: '', expected: '', testData: '' }]
  }
  tagsInput.value = tc.tags?.join(', ') || ''
  showEditor.value = true
}

function closeEditor() {
  showEditor.value = false
  editingTestCase.value = null
  resetForm()
}

function resetForm() {
  form.value = {
    title: '',
    description: '',
    preconditions: '',
    postconditions: '',
    priority: 'Medium',
    status: 'Draft',
    automation_status: 'Manual',
    steps: [{ action: '', expected: '', testData: '' }]
  }
  tagsInput.value = ''
}

function addStep() {
  form.value.steps.push({ action: '', expected: '', testData: '' })
}

function removeStep(idx) {
  if (form.value.steps.length > 1) {
    form.value.steps.splice(idx, 1)
  }
}

async function saveTestCase() {
  const data = {
    ...form.value,
    tags: tagsInput.value.split(',').map(t => t.trim()).filter(Boolean)
  }

  if (editingTestCase.value) {
    await store.updateTestCase(editingTestCase.value.id, data)
  } else {
    await store.createTestCase(data)
  }

  closeEditor()
  await store.fetchFoldersTree()
}

async function deleteTestCase() {
  if (editingTestCase.value && confirm('Delete this test case?')) {
    await store.deleteTestCase(editingTestCase.value.id)
    closeEditor()
    await store.fetchFoldersTree()
  }
}

// Folder handlers
function handleSelectFolder(folderId) {
  store.selectFolder(folderId)
}

async function handleCreateFolder({ parentId, name }) {
  await store.createFolder(name, parentId)
}

async function handleRenameFolder({ id, name }) {
  await store.updateFolder(id, name)
}

async function handleDeleteFolder(folderId) {
  await store.deleteFolder(folderId)
}

async function handleDrop(payload) {
  if (payload.itemType === 'folder') {
    await store.moveFolder(payload.itemId, payload.targetFolderId)
  } else if (payload.itemType === 'testcase') {
    await store.moveTestCaseToFolder(payload.itemId, payload.targetFolderId)
  }
}

function onTestCaseDragStart(e, tc) {
  e.dataTransfer.setData('application/json', JSON.stringify({
    itemId: tc.id,
    itemType: 'testcase',
  }))
  e.dataTransfer.effectAllowed = 'move'
}

onMounted(() => {
  loadTestCases()
  store.fetchFoldersTree()
})
</script>

<style scoped>
.testcases-layout {
  display: flex;
  gap: 20px;
  margin-top: 16px;
}

.sidebar {
  width: 250px;
  min-width: 250px;
  background: var(--bg-card);
  border-radius: 12px;
  padding: 12px;
  align-self: flex-start;
  position: sticky;
  top: 20px;
  max-height: calc(100vh - 160px);
  overflow-y: auto;
}

.main-area {
  flex: 1;
  min-width: 0;
}

.testcases-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.testcase-card {
  background: var(--bg-card);
  padding: 20px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.testcase-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

.tc-header {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.tc-priority,
.tc-status {
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.tc-priority.critical {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.tc-priority.high {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.tc-priority.medium {
  background: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
}

.tc-priority.low {
  background: rgba(107, 114, 128, 0.2);
  color: #9ca3af;
}

.tc-status.draft {
  background: rgba(107, 114, 128, 0.2);
  color: #9ca3af;
}

.tc-status.ready {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.tc-status.approved {
  background: rgba(124, 58, 237, 0.2);
  color: #a78bfa;
}

.tc-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 8px 0;
}

.tc-description {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0 0 12px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tc-footer {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-secondary);
}

.tc-automation.automated {
  color: #10b981;
}

.tc-automation.manual {
  color: #f59e0b;
}

.tc-tags {
  display: flex;
  gap: 6px;
  margin-top: 12px;
}

.tag {
  background: var(--accent);
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
}

/* Form styles */
.form-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  color: var(--text-secondary);
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
}

.step-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.step-num {
  min-width: 24px;
  height: 24px;
  background: var(--accent);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.step-action {
  flex: 2;
}

.step-expected {
  flex: 2;
}

.btn-icon {
  width: 28px;
  height: 28px;
  padding: 0;
  background: var(--error);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.form-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--bg-secondary);
}

.form-actions .btn-danger {
  margin-right: auto;
}

.loading {
  display: flex;
  justify-content: center;
  padding: 60px;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: var(--bg-card);
  border-radius: 16px;
  padding: 24px;
  max-width: 700px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
}

.modal-close {
  position: absolute;
  top: 16px;
  right: 16px;
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 24px;
  cursor: pointer;
}
</style>
