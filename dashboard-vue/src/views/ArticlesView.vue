<template>
  <div class="articles-page">
    <div class="page-header">
      <h1>Articles</h1>
      <div class="header-actions">
        <button class="btn btn-secondary" @click="triggerImport" :disabled="importing">
          {{ importing ? 'Importing...' : 'Import' }}
        </button>
        <button class="btn btn-primary" @click="createArticle">
          + New Article
        </button>
      </div>
    </div>

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
        <!-- Filters -->
        <div class="filters">
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

        <!-- Articles Grid -->
        <div v-if="loading" class="loading">
          <div class="spinner"></div>
        </div>

        <div v-else-if="articles.length === 0" class="empty-state">
          <p>No articles yet</p>
          <p class="hint">Create your first article</p>
        </div>

        <div v-else class="articles-grid" data-testid="articles-list">
          <div
            v-for="article in articles"
            :key="article.id"
            class="article-card"
            :draggable="true"
            @click="openArticle(article)"
            @dragstart="onArticleDragStart($event, article)"
          >
            <div class="article-status" :class="article.status">
              {{ article.status }}
            </div>
            <h3>{{ article.title }}</h3>
            <p class="excerpt">{{ article.excerpt || 'No preview available' }}</p>
            <div class="article-meta">
              <span class="category">{{ article.category || 'Uncategorized' }}</span>
              <span class="views">{{ article.views }} views</span>
            </div>
            <div v-if="article.tags?.length" class="tags">
              <span v-for="tag in article.tags.slice(0, 3)" :key="tag" class="tag">
                {{ tag }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Fullscreen Editor -->
    <div v-if="showEditor" class="editor-fullscreen">
      <div class="editor-header">
        <button class="btn-back" @click="closeEditor">← Назад</button>
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
        <button type="button" class="btn btn-primary btn-sm" @click="saveArticle">Save</button>
      </div>

      <div class="editor-subheader">
        <input v-model="form.category" class="subheader-input" placeholder="Category" />
        <input v-model="tagsInput" class="subheader-input" placeholder="Tags (comma-separated)" />
        <button type="button" class="btn-import-small" @click="triggerEditorImport" :disabled="importing">
          {{ importing ? 'Loading...' : 'Import from file' }}
        </button>
      </div>

      <div class="editor-body">
        <div class="editor-content">
          <RichEditor
            v-model="form.contentJson"
            placeholder="Содержимое статьи..."
            :uploadEnabled="true"
          />
        </div>
      </div>
    </div>

    <!-- Article View Modal -->
    <div v-if="viewingArticle" class="modal-overlay" @click.self="closeViewer">
      <div class="modal-content modal-large">
        <button class="modal-close" @click="closeViewer">&times;</button>

        <div class="article-view">
          <div class="article-header">
            <span class="article-status" :class="viewingArticle.status">
              {{ viewingArticle.status }}
            </span>
            <span class="article-date">{{ formatDate(viewingArticle.created_at) }}</span>
          </div>

          <h1>{{ viewingArticle.title }}</h1>

          <div class="article-info">
            <span>By {{ viewingArticle.author }}</span>
            <span>{{ viewingArticle.views }} views</span>
            <span v-if="viewingArticle.category">{{ viewingArticle.category }}</span>
          </div>

          <div class="article-content">
            <RichEditor :modelValue="parseContent(viewingArticle.content)" :editable="false" />
          </div>

          <div class="article-actions">
            <button class="btn btn-secondary" @click="editFromView">Edit</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useArticlesStore } from '@/stores/articles'
import { articlesApi } from '@/services/api'
import FolderTree from '@/components/articles/FolderTree.vue'
import RichEditor from '@/components/common/RichEditor.vue'

const store = useArticlesStore()

const showEditor = ref(false)
const editingArticle = ref(null)
const viewingArticle = ref(null)
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
  // Fetch full article with content
  const full = await store.fetchArticle(article.id)
  viewingArticle.value = full || article
}

function closeViewer() {
  viewingArticle.value = null
}

function editFromView() {
  editingArticle.value = viewingArticle.value
  form.value = {
    title: viewingArticle.value.title || '',
    content: viewingArticle.value.content || '',
    contentJson: parseContent(viewingArticle.value.content),
    category: viewingArticle.value.category || '',
    status: viewingArticle.value.status || 'draft'
  }
  tagsInput.value = viewingArticle.value.tags?.join(', ') || ''
  viewingArticle.value = null
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
    category: '',
    status: 'draft'
  }
  tagsInput.value = ''
}

function buildArticleData() {
  return {
    title: form.value.title,
    content: form.value.contentJson ? JSON.stringify(form.value.contentJson) : form.value.content,
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

onMounted(() => {
  loadArticles()
  store.fetchCategories()
  store.fetchFoldersTree()
})
</script>

<style scoped>
.articles-layout {
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

.articles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.article-card {
  background: var(--bg-card);
  padding: 20px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.article-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

.article-status {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  margin-bottom: 12px;
}

.article-status.published {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.article-status.draft {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.article-card h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
}

.excerpt {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0 0 12px 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.article-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  background: var(--accent);
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
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
  border: 1px solid var(--border-color, rgba(255,255,255,0.1));
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
  overflow-y: auto;
}

.editor-content {
  max-width: 860px;
  margin: 0 auto;
  padding: 40px 20px 80px;
}

.editor-content :deep(.ProseMirror) {
  min-height: 60vh;
}

/* Article View */
.article-view h1 {
  font-size: 28px;
  margin: 16px 0;
}

.article-header {
  display: flex;
  gap: 12px;
  align-items: center;
}

.article-date {
  color: var(--text-secondary);
  font-size: 12px;
}

.article-info {
  display: flex;
  gap: 16px;
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--bg-secondary);
}

.article-content {
  font-size: 16px;
  line-height: 1.8;
}

.article-content :deep(h1),
.article-content :deep(h2),
.article-content :deep(h3) {
  margin-top: 24px;
  margin-bottom: 12px;
}

.article-content :deep(code) {
  background: var(--bg-secondary);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
}

.article-content :deep(pre) {
  background: var(--bg-secondary);
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
}

.article-content :deep(pre code) {
  background: none;
  padding: 0;
}

.article-content :deep(.article-image) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 16px 0;
  display: block;
}

.editor-toolbar-actions {
  display: flex;
  gap: 6px;
}

.article-actions {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--bg-secondary);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
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
  max-width: 800px;
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

.header-actions {
  display: flex;
  gap: 8px;
}

.content-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.content-label-row label {
  margin-bottom: 0;
}

.btn-import-small {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color, rgba(255,255,255,0.1));
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
