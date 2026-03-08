<template>
  <div class="testcases-page">
    <div class="page-header">
      <h1>Test Cases</h1>
      <button class="btn btn-primary" @click="openNewTestCase">
        + New Test Case
      </button>
    </div>

    <div class="testcases-split">
      <!-- Left: folder tree + test cases list -->
      <div class="split-list" :class="{ 'split-list--collapsed': panelOpen }">
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

            <div v-else class="testcases-grid" :class="{ 'grid-compact': panelOpen }" data-testid="testcases-list">
              <div
                v-for="tc in testCases"
                :key="tc.id"
                class="testcase-card"
                :class="{ 'card-selected': tc.id === store.selectedTestCaseId }"
                :draggable="true"
                @click="handleCardClick(tc)"
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
      </div>

      <!-- Right: Edit panel -->
      <div class="split-panel" :class="{ 'split-panel--hidden': !panelOpen }">
        <div v-if="panelOpen" class="panel-inner">
          <TestCasePanel
            :testCase="editingTestCase"
            v-model="form"
            @save="saveTestCase"
            @delete="handleDelete"
            @close="closePanel"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useTestCasesStore } from '@/stores/testcases'
import FolderTree from '@/components/testcases/FolderTree.vue'
import TestCasePanel from '@/components/testcases/TestCasePanel.vue'

const store = useTestCasesStore()

const editingTestCase = ref(null)

const filters = ref({
  status: '',
  priority: ''
})

const form = ref(getEmptyForm())

function getEmptyForm() {
  return {
    title: '',
    description: '',
    descriptionJson: null,
    preconditions: '',
    preconditionsJson: null,
    postconditions: '',
    postconditionsJson: null,
    priority: 'Medium',
    status: 'Draft',
    automation_status: 'Manual',
    steps: [{ action: '', expected: '', testData: '' }],
    tags: []
  }
}

function parseContent(raw) {
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw)
    if (parsed && parsed.type === 'doc') return parsed
  } catch {}
  return { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: raw }] }] }
}

const loading = computed(() => store.loading)
const testCases = computed(() => store.testCases)
const treeFolders = computed(() => store.treeFolders)
const panelOpen = computed(() => store.panelMode !== null)

async function loadTestCases() {
  store.filters = { ...filters.value, folder: '' }
  await store.fetchTestCases()
}

function handleCardClick(tc) {
  editingTestCase.value = tc
  form.value = {
    title: tc.title || '',
    description: tc.description || '',
    descriptionJson: parseContent(tc.description),
    preconditions: tc.preconditions || '',
    preconditionsJson: parseContent(tc.preconditions),
    postconditions: tc.postconditions || '',
    postconditionsJson: parseContent(tc.postconditions),
    priority: tc.priority || 'Medium',
    status: tc.status || 'Draft',
    automation_status: tc.automation_status || 'Manual',
    steps: tc.steps?.length ? [...tc.steps] : [{ action: '', expected: '', testData: '' }],
    tags: tc.tags || []
  }
  store.openTestCase(tc.id)
}

function openNewTestCase() {
  editingTestCase.value = null
  form.value = getEmptyForm()
  store.selectedTestCaseId = null
  store.panelMode = 'edit'
}

function closePanel() {
  store.closePanel()
  editingTestCase.value = null
  form.value = getEmptyForm()
}

async function saveTestCase(formData) {
  const data = {
    title: formData.title,
    description: formData.descriptionJson ? JSON.stringify(formData.descriptionJson) : formData.description,
    preconditions: formData.preconditionsJson ? JSON.stringify(formData.preconditionsJson) : formData.preconditions,
    postconditions: formData.postconditionsJson ? JSON.stringify(formData.postconditionsJson) : formData.postconditions,
    priority: formData.priority,
    status: formData.status,
    automation_status: formData.automation_status,
    steps: (formData.steps || []).map(s => ({
      action: typeof s.action === 'object' ? JSON.stringify(s.action) : (s.action || ''),
      expected: typeof s.expected === 'object' ? JSON.stringify(s.expected) : (s.expected || ''),
      testData: s.testData || ''
    })),
    tags: formData.tags || []
  }

  if (editingTestCase.value) {
    await store.updateTestCase(editingTestCase.value.id, data)
  } else {
    await store.createTestCase(data)
  }

  closePanel()
  await store.fetchFoldersTree()
}

async function handleDelete(id) {
  if (confirm('Delete this test case?')) {
    await store.deleteTestCase(id)
    closePanel()
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
/* Split layout */
.testcases-split {
  display: flex;
  gap: 0;
  margin-top: 16px;
  height: calc(100vh - 120px);
}

.split-list {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  transition: flex 0.3s ease;
}

.split-list--collapsed {
  flex: 0 0 40%;
  max-width: 40%;
}

.split-panel {
  flex: 0 0 60%;
  max-width: 60%;
  border-left: 1px solid rgba(255, 255, 255, 0.08);
  overflow-y: auto;
  transition: flex 0.3s ease, max-width 0.3s ease;
}

.split-panel--hidden {
  flex: 0;
  max-width: 0;
  overflow: hidden;
  border-left: none;
}

.panel-inner {
  padding: 20px 24px;
  height: 100%;
}

/* Selected card */
.card-selected {
  outline: 2px solid var(--accent, #6366f1);
  outline-offset: -2px;
}

/* Existing layout (sidebar + main-area inside split-list) */
.testcases-layout {
  display: flex;
  gap: 20px;
}

.sidebar {
  width: 250px;
  min-width: 250px;
  background: var(--bg-card);
  border-radius: 12px;
  padding: 12px;
  align-self: flex-start;
  position: sticky;
  top: 0;
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

.grid-compact {
  grid-template-columns: 1fr;
}

.testcase-card {
  background: var(--bg-card);
  padding: 20px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.testcase-card:hover {
  transform: translateY(-2px);
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

.tc-priority.critical { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
.tc-priority.high { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
.tc-priority.medium { background: rgba(59, 130, 246, 0.2); color: #3b82f6; }
.tc-priority.low { background: rgba(107, 114, 128, 0.2); color: #9ca3af; }

.tc-status.draft { background: rgba(107, 114, 128, 0.2); color: #9ca3af; }
.tc-status.ready { background: rgba(16, 185, 129, 0.2); color: #10b981; }
.tc-status.approved { background: rgba(124, 58, 237, 0.2); color: #a78bfa; }

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

.tc-automation.automated { color: #10b981; }
.tc-automation.manual { color: #f59e0b; }

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

.loading {
  display: flex;
  justify-content: center;
  padding: 60px;
}

/* Mobile: panel overlays list */
@media (max-width: 768px) {
  .split-list--collapsed {
    display: none;
  }
  .split-panel {
    flex: 1;
    max-width: 100%;
  }
  .sidebar {
    display: none;
  }
}
</style>
