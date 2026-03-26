<template>
  <div class="articles-page">
    <!-- Hidden file inputs -->
    <input
      ref="importFileInput"
      type="file"
      accept=".md,.docx"
      style="display: none"
      @change="handleQuickImport"
    />
    <input
      ref="editorFileInput"
      type="file"
      accept=".md,.docx"
      style="display: none"
      @change="handleEditorImport"
    />

    <div class="articles-layout">
      <!-- Sidebar: Folder Tree -->
      <aside class="sidebar">
        <FolderTree
          :folders="folders"
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
        <!-- Header with filters and actions -->
        <div class="list-header">
          <div class="list-filters">
            <select v-model="filters.category" @change="loadArticles">
              <option value="">All Categories</option>
              <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
            </select>
            <select v-model="filters.status" @change="loadArticles">
              <option value="">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="published">Published</option>
            </select>
          </div>
          <div class="list-actions">
            <button class="btn btn-secondary btn-sm" @click="triggerImport" :disabled="importing">
              {{ importing ? 'Importing...' : 'Import' }}
            </button>
            <button class="btn btn-primary btn-sm" @click="createArticle">
              + New Article
            </button>
          </div>
        </div>

        <!-- Articles List -->
        <div v-if="loading" class="loading">
          <div class="spinner"></div>
        </div>

        <div v-else-if="articles.length === 0" class="empty-state">
          <p>No articles yet</p>
          <p class="hint">Create your first article</p>
        </div>

        <div v-else class="articles-list" data-testid="articles-list">
          <div
            v-for="article in articles"
            :key="article.id"
            class="article-row"
            :draggable="true"
            @click="openArticle(article)"
            @dragstart="onArticleDragStart($event, article)"
          >
            <span class="row-icon"><AppIcon name="file" :size="16" /></span>
            <span v-if="article.human_id" class="human-id-badge">{{ article.human_id }}</span>
            <span class="row-title">{{ article.title }}</span>
            <span class="row-status" :class="article.status">{{ article.status }}</span>
            <span class="row-category">{{ article.category || '—' }}</span>
            <span class="row-date">{{ formatDate(article.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Fullscreen Viewer (read mode) -->
    <ArticleViewer
      v-if="showViewer && viewingArticle"
      :article="viewingArticle"
      @close="showViewer = false; viewingArticle = null"
      @edit="editFromViewer"
    />

    <!-- Fullscreen Editor -->
    <div v-if="showEditor" class="editor-fullscreen">
      <div class="editor-header">
        <button class="btn-back" @click="closeEditor">← Назад</button>
        <EditorToolbar
          :editor="gridEditorRef?.activeEditor"
          :uploadEnabled="true"
          @upload-image="gridEditorRef?.triggerImageUpload()"
        />
        <input
          v-model="form.title"
          class="title-input"
          placeholder="Article title"
          required
        />
        <select v-model="form.status" class="status-select">
          <option value="draft">Draft</option>
          <option value="published">Published</option>
        </select>
        <span v-if="autosaveStatus === 'saving'" class="autosave-indicator autosave-saving">Сохранение...</span>
        <span v-else-if="autosaveStatus === 'saved'" class="autosave-indicator autosave-saved">✓ Сохранено {{ autosaveTime }}</span>
        <span v-else-if="autosaveStatus === 'error'" class="autosave-indicator autosave-error">⚠ Не сохранено</span>
        <button v-if="editingArticle" type="button" class="btn btn-danger btn-sm" @click="deleteArticle">
          Delete
        </button>
        <button
          type="button"
          class="btn-subheader-toggle"
          @click="showSubheader = !showSubheader"
          :title="showSubheader ? 'Скрыть метаданные' : 'Категория и теги'"
        >
          {{ showSubheader ? '▲' : '▼' }} Meta
        </button>
        <button type="button" class="btn btn-primary btn-sm" @click="saveArticle">Save</button>
      </div>

      <div v-show="showSubheader" class="editor-subheader">
        <input v-model="form.category" class="subheader-input" placeholder="Category" />
        <input v-model="tagsInput" class="subheader-input" placeholder="Tags (comma-separated)" />
        <button type="button" class="btn-import-small" @click="triggerEditorImport" :disabled="importing">
          {{ importing ? 'Loading...' : 'Import from file' }}
        </button>
      </div>

      <div class="editor-body">
        <GridEditor
          ref="gridEditorRef"
          v-model="form.gridContent"
          :uploadEnabled="true"
        />
      </div>
    </div>



  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { useArticlesStore } from '@/stores/articles'
import { articlesApi } from '@/services/api'
import FolderTree from '@/components/articles/FolderTree.vue'
import GridEditor from '@/components/articles/GridEditor.vue'
import EditorToolbar from '@/components/common/EditorToolbar.vue'
import ArticleViewer from '@/components/articles/ArticleViewer.vue'
import AppIcon from '@/components/common/AppIcon.vue'

const route = useRoute()
const store = useArticlesStore()

const showEditor = ref(false)
const showViewer = ref(false)
const showSubheader = ref(false)
const viewingArticle = ref(null)
const editingArticle = ref(null)
const gridEditorRef = ref(null)
const importing = ref(false)
const importFileInput = ref(null)
const editorFileInput = ref(null)

const autosaveStatus = ref('idle')
const autosaveTime = ref('')
const isDirty = ref(false)
let autosaveTimer = null

const filters = ref({
  category: '',
  status: ''
})

const form = ref({
  title: '',
  content: '',
  contentJson: null,
  gridContent: { version: 'grid-1', rows: [] },
  category: '',
  status: 'draft'
})

function parseContent(raw) {
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw)
    if (parsed && parsed.type === 'doc') return parsed
  } catch {}
  return { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: raw }] }] }
}

function gridUuid() {
  return crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2, 10)
}

function parseArticleContent(raw) {
  if (!raw) {
    return { version: 'grid-1', rows: [] }
  }
  try {
    const parsed = JSON.parse(raw)
    if (parsed && parsed.version === 'grid-1') return parsed
    // Legacy TipTap doc → wrap in grid
    return {
      version: 'grid-1',
      rows: [{
        id: gridUuid(),
        columns: [{ id: gridUuid(), span: 12, content: parsed }]
      }]
    }
  } catch {
    return { version: 'grid-1', rows: [] }
  }
}

const tagsInput = ref('')

const loading = computed(() => store.loading)
const articles = computed(() => store.articles)
const categories = computed(() => store.categories)
const folders = computed(() => store.folders)

async function loadArticles() {
  store.filters = { ...filters.value }
  await store.fetchArticles()
}

function createArticle() {
  editingArticle.value = null
  resetForm()
  showEditor.value = true
}

async function openArticle(article) {
  const full = await store.fetchArticle(article.id)
  const a = full || article
  viewingArticle.value = a
  showViewer.value = true
}

function editFromViewer() {
  const a = viewingArticle.value
  if (!a) return
  editingArticle.value = a
  form.value = {
    title: a.title || '',
    content: a.content || '',
    contentJson: parseContent(a.content),
    gridContent: parseArticleContent(a.content),
    category: a.category || '',
    status: a.status || 'draft'
  }
  tagsInput.value = a.tags?.join(', ') || ''
  showViewer.value = false
  showEditor.value = true
  isDirty.value = false
  startAutosave()
}

function openEditorDirect(article) {
  editingArticle.value = article
  form.value = {
    title: article.title || '',
    content: article.content || '',
    contentJson: parseContent(article.content),
    gridContent: parseArticleContent(article.content),
    category: article.category || '',
    status: article.status || 'draft'
  }
  tagsInput.value = article.tags?.join(', ') || ''
  showEditor.value = true
  isDirty.value = false
  startAutosave()
}

function closeEditor() {
  if (isDirty.value && !confirm('Есть несохранённые изменения. Закрыть без сохранения?')) {
    return
  }
  stopAutosave()
  showEditor.value = false
  editingArticle.value = null
  isDirty.value = false
  resetForm()
}

function resetForm() {
  form.value = {
    title: '',
    content: '',
    contentJson: null,
    gridContent: { version: 'grid-1', rows: [] },
    category: '',
    status: 'draft'
  }
  tagsInput.value = ''
}

function buildArticleData() {
  return {
    title: form.value.title,
    content: JSON.stringify(form.value.gridContent),
    category: form.value.category,
    status: form.value.status,
    tags: tagsInput.value.split(',').map(t => t.trim()).filter(Boolean)
  }
}

async function saveArticle() {
  const data = buildArticleData()

  if (editingArticle.value) {
    await store.updateArticle(editingArticle.value.id, data)
  } else {
    await store.createArticle(data)
  }

  isDirty.value = false
  stopAutosave()
  showEditor.value = false
  editingArticle.value = null
  resetForm()
  await loadArticles()
}

async function deleteArticle() {
  if (editingArticle.value && confirm('Delete this article?')) {
    await store.deleteArticle(editingArticle.value.id)
    closeEditor()
  }
}

// Autosave
function startAutosave() {
  stopAutosave()
  if (editingArticle.value) {
    autosaveTimer = setInterval(performAutosave, 60000)
  }
}

function stopAutosave() {
  if (autosaveTimer) {
    clearInterval(autosaveTimer)
    autosaveTimer = null
  }
  autosaveStatus.value = 'idle'
}

async function performAutosave() {
  if (!editingArticle.value) return
  autosaveStatus.value = 'saving'
  try {
    const data = buildArticleData()
    await store.updateArticle(editingArticle.value.id, data)
    isDirty.value = false
    autosaveStatus.value = 'saved'
    autosaveTime.value = new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
    setTimeout(() => {
      if (autosaveStatus.value === 'saved') {
        autosaveStatus.value = 'idle'
      }
    }, 3000)
  } catch {
    autosaveStatus.value = 'error'
  }
}

// Watch form changes for isDirty
watch(form, () => {
  if (showEditor.value) {
    isDirty.value = true
  }
}, { deep: true })

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
  } else if (payload.itemType === 'article') {
    await store.moveArticleToFolder(payload.itemId, payload.targetFolderId)
  }
}

// Import handlers
function triggerImport() {
  importFileInput.value?.click()
}

function triggerEditorImport() {
  editorFileInput.value?.click()
}

function validateFile(file) {
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!['md', 'docx'].includes(ext)) {
    alert('Unsupported format. Allowed: .md, .docx')
    return false
  }
  if (file.size > 5 * 1024 * 1024) {
    alert('File too large. Max: 5 MB')
    return false
  }
  return true
}

async function handleQuickImport(event) {
  const file = event.target.files?.[0]
  if (!file || !validateFile(file)) {
    event.target.value = ''
    return
  }

  importing.value = true
  const formData = new FormData()
  formData.append('file', file)
  if (store.selectedFolderId) {
    formData.append('folder_id', store.selectedFolderId)
  }
  formData.append('status', 'draft')

  try {
    const response = await articlesApi.importFile(formData)
    const { title, warnings } = response.data
    let msg = `Article imported: "${title}"`
    if (warnings?.length) msg += `\nWarnings: ${warnings.join(', ')}`
    alert(msg)
    await loadArticles()
    await store.fetchFoldersTree()
  } catch (err) {
    alert(err.response?.data?.detail || 'Import failed')
  } finally {
    importing.value = false
    event.target.value = ''
  }
}

async function handleEditorImport(event) {
  const file = event.target.files?.[0]
  if (!file || !validateFile(file)) {
    event.target.value = ''
    return
  }

  importing.value = true
  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await articlesApi.previewFile(formData)
    const { title, content, warnings } = response.data
    form.value.title = title || form.value.title
    if (content) {
      form.value.content = content
      form.value.contentJson = parseContent(content)
      form.value.gridContent = parseArticleContent(content)
    }
    if (warnings?.length) {
      alert(`Warnings: ${warnings.join(', ')}`)
    }
  } catch (err) {
    alert(err.response?.data?.detail || 'Preview failed')
  } finally {
    importing.value = false
    event.target.value = ''
  }
}

function onArticleDragStart(e, article) {
  e.dataTransfer.setData('application/json', JSON.stringify({
    itemId: article.id,
    itemType: 'article',
  }))
  e.dataTransfer.effectAllowed = 'move'
}

onBeforeUnmount(() => {
  stopAutosave()
})

async function openFromRoute() {
  const slug = route.params.slug
  if (slug) {
    const article = await store.fetchArticle(slug)
    if (article) {
      viewingArticle.value = article
      showViewer.value = true
    }
  }
}

watch(() => route.params.slug, openFromRoute)

onMounted(async () => {
  await loadArticles()
  store.fetchCategories()
  store.fetchFoldersTree()
  await openFromRoute()
})
</script>

<style scoped>
.articles-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 60px);
  overflow: hidden;
}

.articles-layout {
  display: flex;
  gap: 0;
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

.sidebar {
  width: 240px;
  min-width: 240px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  padding: 12px 8px;
  overflow-y: auto;
  flex-shrink: 0;
}

.main-area {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 16px 20px;
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
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 13px;
}

.list-actions {
  display: flex;
  gap: 8px;
}

.articles-list {
  background: var(--bg-card);
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid var(--border-color);
}

.article-row {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 44px;
  padding: 0 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--bg-secondary);
  transition: background 0.15s;
}

.article-row:last-child {
  border-bottom: none;
}

.article-row:hover {
  background: var(--bg-secondary);
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

.row-icon {
  width: 24px;
  text-align: center;
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

.row-status.published {
  background: rgba(0, 135, 90, 0.12);
  color: var(--success);
}

.row-status.draft {
  background: rgba(255, 139, 0, 0.12);
  color: var(--warning);
}

.row-category {
  width: 120px;
  flex-shrink: 0;
  font-size: 13px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
  min-height: 48px;
  padding: 4px 16px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--bg-secondary);
  flex-shrink: 0;
  flex-wrap: wrap;
}

.editor-header :deep(.editor-toolbar) {
  border: none;
  border-radius: 0;
  background: none;
  padding: 0;
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

.title-input {
  flex: 1;
  background: none;
  border: none;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  outline: none;
  min-width: 0;
}

.title-input::placeholder {
  color: var(--text-secondary);
  opacity: 0.5;
}

.status-select {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 13px;
}

.autosave-indicator {
  font-size: 12px;
  white-space: nowrap;
}

.autosave-saving {
  color: var(--text-secondary);
}

.autosave-saved {
  color: #10b981;
}

.autosave-error {
  color: #ef4444;
}

.btn-sm {
  padding: 4px 12px !important;
  font-size: 13px !important;
}

.editor-subheader {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 36px;
  padding: 0 16px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--bg-secondary);
  flex-shrink: 0;
}

.subheader-input {
  background: none;
  border: none;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  padding: 4px 0;
  min-width: 120px;
  max-width: 200px;
}

.subheader-input::placeholder {
  color: var(--text-secondary);
  opacity: 0.5;
}

.editor-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.editor-body :deep(.grid-editor) {
  flex: 1;
  overflow: hidden;
}

.editor-body :deep(.grid-body) {
  max-width: 1100px;
  margin: 0 auto;
}

.btn-subheader-toggle {
  background: none;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.btn-subheader-toggle:hover {
  border-color: var(--accent);
  color: var(--accent);
}


.loading {
  display: flex;
  justify-content: center;
  padding: 60px;
}


.btn-import-small {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-import-small:hover {
  background: var(--accent);
  color: white;
}

.btn-import-small:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
