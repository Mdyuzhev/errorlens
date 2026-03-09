<template>
  <div class="testcases-page">
    <div class="page-header">
      <h1>Test Cases</h1>
      <button class="btn btn-primary" @click="openNewTestCase">
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
        <!-- Header with filters -->
        <div class="list-header">
          <div class="list-filters">
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
        </div>

        <!-- Test Cases List -->
        <div v-if="loading" class="loading">
          <div class="spinner"></div>
        </div>

        <div v-else-if="testCases.length === 0" class="empty-state">
          <p>No test cases yet</p>
          <p class="hint">Create from session or manually</p>
        </div>

        <div v-else class="testcases-list" data-testid="testcases-list">
          <div
            v-for="tc in testCases"
            :key="tc.id"
            class="tc-row"
            :draggable="true"
            @click="handleCardClick(tc)"
            @dragstart="onTestCaseDragStart($event, tc)"
          >
            <span class="row-icon"><AppIcon name="flask" :size="16" /></span>
            <span v-if="tc.human_id" class="human-id-badge">{{ tc.human_id }}</span>
            <span class="row-title">{{ tc.title }}</span>
            <span class="row-priority" :class="tc.priority?.toLowerCase()">{{ tc.priority }}</span>
            <span class="row-status" :class="tc.status?.toLowerCase()">{{ tc.status }}</span>
            <span class="row-steps">{{ tc.steps?.length || 0 }} steps</span>
            <span class="row-date">{{ formatDate(tc.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Fullscreen Viewer (read mode) -->
    <TestCaseViewer
      v-if="showViewer && viewingTestCase"
      :testCase="viewingTestCase"
      :backlinks="backlinks"
      @close="showViewer = false; viewingTestCase = null"
      @edit="editFromViewer"
    />

    <!-- Fullscreen Editor -->
    <div v-if="showEditor" class="editor-fullscreen">
      <div class="editor-header">
        <button class="btn-back" @click="closeEditor">← Назад</button>
        <span class="editor-title">{{ editingTestCase ? 'Edit Test Case' : 'New Test Case' }}</span>
        <div class="editor-spacer"></div>
        <button v-if="editingTestCase" type="button" class="btn btn-danger btn-sm" @click="handleDelete(editingTestCase.id)">
          Delete
        </button>
        <button type="button" class="btn btn-secondary btn-sm" @click="closeEditor">Cancel</button>
        <button type="button" class="btn btn-primary btn-sm" @click="saveTestCase(form)">Save</button>
      </div>
      <div class="editor-body">
        <TestCasePanel
          :testCase="editingTestCase"
          :backlinks="backlinks"
          v-model="form"
          @save="saveTestCase"
          @delete="handleDelete"
          @close="closeEditor"
          @go-to-article="goToArticle"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useTestCasesStore } from '@/stores/testcases'
import { entityLinksApi } from '@/services/api'
import FolderTree from '@/components/testcases/FolderTree.vue'
import TestCasePanel from '@/components/testcases/TestCasePanel.vue'
import TestCaseViewer from '@/components/testcases/TestCaseViewer.vue'
import AppIcon from '@/components/common/AppIcon.vue'

const route = useRoute()
const store = useTestCasesStore()

const editingTestCase = ref(null)
const viewingTestCase = ref(null)
const showViewer = ref(false)
const showEditor = ref(false)
const backlinks = ref([])

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

async function loadTestCases() {
  store.filters = { ...filters.value, folder: '' }
  await store.fetchTestCases()
}

function handleCardClick(tc) {
  viewingTestCase.value = tc
  loadBacklinks(tc.id)
  showViewer.value = true
}

function editFromViewer() {
  const tc = viewingTestCase.value
  if (!tc) return
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
  showViewer.value = false
  showEditor.value = true
}

function openNewTestCase() {
  editingTestCase.value = null
  backlinks.value = []
  form.value = getEmptyForm()
  showEditor.value = true
}

function closeEditor() {
  showEditor.value = false
  editingTestCase.value = null
  backlinks.value = []
  form.value = getEmptyForm()
}

async function loadBacklinks(tcId) {
  try {
    const res = await entityLinksApi.getBacklinks('testcase', tcId)
    backlinks.value = res.data.items || []
  } catch {
    backlinks.value = []
  }
}

function goToArticle(bl) {
  const slug = bl.article_slug || bl.article_id
  window.open(`${window.location.origin}${window.location.pathname}#/articles/${slug}`, '_blank')
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

  closeEditor()
  await store.fetchFoldersTree()
}

async function handleDelete(id) {
  if (confirm('Delete this test case?')) {
    await store.deleteTestCase(id)
    closeEditor()
    showViewer.value = false
    viewingTestCase.value = null
    await store.fetchFoldersTree()
  }
}

function formatDate(date) {
  if (!date) return ''
  return new Date(date).toLocaleDateString()
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

async function openFromRoute() {
  const id = route.params.id
  if (id) {
    const tc = await store.fetchTestCase(id)
    if (tc) {
      viewingTestCase.value = tc
      loadBacklinks(tc.id)
      showViewer.value = true
    }
  }
}

watch(() => route.params.id, openFromRoute)

onMounted(async () => {
  await loadTestCases()
  store.fetchFoldersTree()
  await openFromRoute()
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

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  gap: 12px;
}

.list-filters {
  display: flex;
  gap: 8px;
}

.list-filters select {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color, rgba(255,255,255,0.1));
  color: var(--text-primary);
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 13px;
}

/* List rows */
.testcases-list {
  background: var(--bg-card);
  border-radius: 12px;
  overflow: hidden;
}

.tc-row {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 44px;
  padding: 0 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--bg-secondary);
  transition: background 0.15s;
}

.tc-row:last-child {
  border-bottom: none;
}

.tc-row:hover {
  background: var(--bg-secondary);
}

.row-icon {
  width: 24px;
  text-align: center;
  flex-shrink: 0;
}

.human-id-badge {
  font-size: 11px;
  font-family: monospace;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  padding: 1px 6px;
  border-radius: 4px;
  flex-shrink: 0;
}

.row-title {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.row-priority {
  width: 90px;
  flex-shrink: 0;
  text-align: center;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.row-priority.critical { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
.row-priority.high { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
.row-priority.medium { background: rgba(59, 130, 246, 0.2); color: #3b82f6; }
.row-priority.low { background: rgba(107, 114, 128, 0.2); color: #9ca3af; }

.row-status {
  width: 90px;
  flex-shrink: 0;
  text-align: center;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.row-status.draft { background: rgba(107, 114, 128, 0.2); color: #9ca3af; }
.row-status.ready { background: rgba(16, 185, 129, 0.2); color: #10b981; }
.row-status.approved { background: rgba(124, 58, 237, 0.2); color: #a78bfa; }

.row-steps {
  width: 80px;
  flex-shrink: 0;
  font-size: 13px;
  color: var(--text-secondary);
  text-align: center;
}

.row-date {
  width: 100px;
  flex-shrink: 0;
  font-size: 13px;
  color: var(--text-secondary);
  text-align: right;
}

/* Fullscreen Editor */
.editor-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

.editor-header {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 48px;
  padding: 0 16px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--bg-secondary);
  flex-shrink: 0;
}

.editor-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.editor-spacer {
  flex: 1;
}

.editor-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.btn-back {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 14px;
  padding: 4px 8px;
  border-radius: 6px;
  white-space: nowrap;
}

.btn-back:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.btn-sm {
  padding: 4px 12px !important;
  font-size: 13px !important;
}

.loading {
  display: flex;
  justify-content: center;
  padding: 60px;
}

@media (max-width: 768px) {
  .sidebar {
    display: none;
  }
}
</style>
