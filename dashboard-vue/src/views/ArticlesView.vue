<template>
  <div class="articles-page">
    <div class="page-header">
      <h1>Articles</h1>
      <button class="btn btn-primary" @click="createArticle">
        + New Article
      </button>
    </div>

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

    <!-- Editor Modal -->
    <div v-if="showEditor" class="modal-overlay" @click.self="closeEditor">
      <div class="modal-content modal-large">
        <button class="modal-close" @click="closeEditor">&times;</button>

        <h2>{{ editingArticle ? 'Edit Article' : 'New Article' }}</h2>

        <form @submit.prevent="saveArticle">
          <div class="form-group">
            <label>Title *</label>
            <input v-model="form.title" required placeholder="Article title" />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>Category</label>
              <input v-model="form.category" placeholder="e.g., API Testing" />
            </div>

            <div class="form-group">
              <label>Status</label>
              <select v-model="form.status">
                <option value="draft">Draft</option>
                <option value="published">Published</option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label>Content (Markdown)</label>
            <textarea
              v-model="form.content"
              rows="15"
              placeholder="Write your article in Markdown..."
              class="content-editor"
            ></textarea>
          </div>

          <div class="form-group">
            <label>Tags (comma-separated)</label>
            <input v-model="tagsInput" placeholder="api, testing, guide" />
          </div>

          <div class="form-actions">
            <button v-if="editingArticle" type="button" class="btn btn-danger" @click="deleteArticle">
              Delete
            </button>
            <button type="button" class="btn btn-secondary" @click="closeEditor">Cancel</button>
            <button type="submit" class="btn btn-primary">Save</button>
          </div>
        </form>
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

          <div class="article-content" v-html="renderedContent"></div>

          <div class="article-actions">
            <button class="btn btn-secondary" @click="editFromView">Edit</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useArticlesStore } from '@/stores/articles'
import FolderTree from '@/components/articles/FolderTree.vue'

const store = useArticlesStore()

const showEditor = ref(false)
const editingArticle = ref(null)
const viewingArticle = ref(null)

const filters = ref({
  category: '',
  status: ''
})

const form = ref({
  title: '',
  content: '',
  category: '',
  status: 'draft'
})

const tagsInput = ref('')

const loading = computed(() => store.loading)
const articles = computed(() => store.articles)
const categories = computed(() => store.categories)
const folders = computed(() => store.folders)

// Simple markdown renderer
const renderedContent = computed(() => {
  if (!viewingArticle.value?.content) return ''

  return viewingArticle.value.content
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em>$1</em>')
    .replace(/`([^`]+)`/gim, '<code>$1</code>')
    .replace(/```(\w*)\n([\s\S]*?)```/gim, '<pre><code>$2</code></pre>')
    .replace(/\n/gim, '<br>')
})

async function loadArticles() {
  store.filters = { ...filters.value }
  await store.fetchArticles()
}

function createArticle() {
  editingArticle.value = null
  resetForm()
  showEditor.value = true
}

function openArticle(article) {
  viewingArticle.value = article
}

function closeViewer() {
  viewingArticle.value = null
}

function editFromView() {
  editingArticle.value = viewingArticle.value
  form.value = {
    title: viewingArticle.value.title || '',
    content: viewingArticle.value.content || '',
    category: viewingArticle.value.category || '',
    status: viewingArticle.value.status || 'draft'
  }
  tagsInput.value = viewingArticle.value.tags?.join(', ') || ''
  viewingArticle.value = null
  showEditor.value = true
}

function closeEditor() {
  showEditor.value = false
  editingArticle.value = null
  resetForm()
}

function resetForm() {
  form.value = {
    title: '',
    content: '',
    category: '',
    status: 'draft'
  }
  tagsInput.value = ''
}

async function saveArticle() {
  const data = {
    ...form.value,
    tags: tagsInput.value.split(',').map(t => t.trim()).filter(Boolean)
  }

  if (editingArticle.value) {
    await store.updateArticle(editingArticle.value.id, data)
  } else {
    await store.createArticle(data)
  }

  closeEditor()
  await loadArticles()
}

async function deleteArticle() {
  if (editingArticle.value && confirm('Delete this article?')) {
    await store.deleteArticle(editingArticle.value.id)
    closeEditor()
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
  } else if (payload.itemType === 'article') {
    await store.moveArticleToFolder(payload.itemId, payload.targetFolderId)
  }
}

function onArticleDragStart(e, article) {
  e.dataTransfer.setData('application/json', JSON.stringify({
    itemId: article.id,
    itemType: 'article',
  }))
  e.dataTransfer.effectAllowed = 'move'
}

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

/* Editor */
.content-editor {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
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
</style>
