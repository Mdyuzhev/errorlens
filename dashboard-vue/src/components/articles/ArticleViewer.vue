<template>
  <div class="article-viewer">
    <!-- TOPBAR -->
    <div class="viewer-topbar" data-testid="viewer-topbar">
      <button class="btn-back" data-testid="viewer-back" @click="emit('close')">← Назад</button>
      <div class="topbar-sep"></div>
      <span class="topbar-path">Articles</span>
      <div class="topbar-gap"></div>
      <button class="btn-action" data-testid="viewer-history" @click="openHistory">История</button>
      <button class="btn-action" data-testid="viewer-pdf" @click="handleExportPdf">PDF</button>
      <button class="btn-action btn-edit" data-testid="viewer-edit" @click="emit('edit')">Edit</button>
    </div>

    <!-- ARTICLE HEAD -->
    <div class="viewer-article-head">
      <div class="viewer-crumbs" data-testid="viewer-crumbs" v-if="breadcrumbs.length">
        <template v-for="(crumb, idx) in breadcrumbs" :key="crumb.id">
          <span v-if="idx > 0" class="crumb-sep">›</span>
          <span
            v-if="crumb.type !== 'article'"
            class="crumb-link"
            @click="handleBreadcrumbClick(crumb)"
          >{{ crumb.name }}</span>
          <span v-else>{{ crumb.name }}</span>
        </template>
      </div>
      <div class="viewer-title-row">
        <span class="viewer-title">{{ article.title }}</span>
        <span class="viewer-badge" :class="article.status">{{ article.status }}</span>
      </div>
      <div class="viewer-meta">
        <div class="viewer-meta-author" v-if="article.author">
          <div class="viewer-avatar">{{ authorInitial }}</div>
          <span>{{ article.author }}</span>
        </div>
        <span class="viewer-dot" v-if="article.author">·</span>
        <span>{{ formatDate(article.updated_at || article.created_at) }}</span>
        <span class="viewer-dot">·</span>
        <span>{{ article.views || 0 }} просмотров</span>
      </div>
      <div class="viewer-tags" v-if="article.category || articleTags.length">
        <span v-if="article.category" class="viewer-tag category">{{ article.category }}</span>
        <span v-for="tag in articleTags" :key="tag" class="viewer-tag">{{ tag }}</span>
      </div>
    </div>

    <!-- BODY -->
    <div class="viewer-body">
      <div class="viewer-content">
        <div class="viewer-document">
          <GridEditor :modelValue="gridContent" :readonly="true" />
        </div>
        <div class="child-pages" data-testid="child-pages" v-if="folderArticles.length">
          <div class="child-pages-label">В этой папке</div>
          <div
            v-for="a in folderArticles"
            :key="a.id"
            class="child-page-item"
            data-testid="child-page-item"
            @click="emit('open-article', a.id)"
          >📄 {{ a.title }}</div>
        </div>

        <!-- Links Section -->
        <div class="viewer-links-section">
          <div class="viewer-links-header" @click="linksExpanded = !linksExpanded">
            <span class="viewer-links-title">
              Связанные материалы
              <span v-if="linkedItems.length" class="links-count">({{ linkedItems.length }})</span>
            </span>
            <span class="links-toggle">{{ linksExpanded ? '▲' : '▼' }}</span>
          </div>

          <div v-if="linksExpanded" class="viewer-links-body">
            <div v-if="linkedItemsLoading" class="links-loading">Loading...</div>
            <LinkSearch
              v-else
              title=""
              empty-text="Нет связанных материалов. Введите EL-123 или название для поиска."
              placeholder="EL-123, TC-45, или название..."
              :items="linkedItems"
              :entity-types="['task', 'testcase']"
              :exclude-ids="linkedItems.map(e => e.id)"
              @add="addLinkedToArticle"
              @remove="removeLinkedFromArticle"
              @click-item="navigateFromArticle"
            />
          </div>
        </div>
      </div>

      <div class="viewer-toc" v-if="tocItems.length">
        <div class="toc-label">Содержание</div>
        <ul class="toc-list">
          <li
            v-for="item in tocItems"
            :key="item.id"
            :class="['toc-item', `toc-h${item.level}`, { active: activeTocId === item.id }]"
            @click="scrollToHeading(item.id)"
          >{{ item.text }}</li>
        </ul>
      </div>
    </div>

    <!-- HISTORY PANEL -->
    <div class="viewer-history" data-testid="viewer-history-panel" :class="{ open: showHistory }">
      <div class="history-header">
        <span>История версий</span>
        <button class="history-close" data-testid="history-close" @click="showHistory = false; selectedVersion = null">✕</button>
      </div>
      <div v-if="historyLoading" class="history-loading">Загрузка...</div>
      <template v-else>
        <div
          v-for="v in store.versions[article.id] || []"
          :key="v.id"
          class="history-item"
          :class="{ active: selectedVersion?.id === v.id }"
          @click="loadVersion(v.id)"
        >
          <div class="history-date">{{ formatDate(v.created_at) }}</div>
          <div class="history-title">{{ v.title }}</div>
        </div>
      </template>
      <div v-if="selectedVersion" class="version-preview">
        <GridEditor :modelValue="versionGridContent" :readonly="true" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import GridEditor from './GridEditor.vue'
import LinkSearch from '@/components/qa/LinkSearch.vue'
import { useArticlesStore } from '@/stores/articles'
import { entityLinksApi } from '@/services/api'

const props = defineProps({
  article: { type: Object, required: true }
})

const emit = defineEmits(['close', 'edit', 'navigate-to-folder', 'open-article'])

const store = useArticlesStore()
const router = useRouter()

// Links state
const linkedItems = ref([])
const linkedItemsLoading = ref(false)
const linksExpanded = ref(true)
const pendingLinkedIssueIds = ref([])
const pendingLinkedTcIds = ref([])

async function loadLinkedItems() {
  if (!props.article?.id) return
  linkedItemsLoading.value = true
  try {
    const article = props.article
    const issueIds = article.linked_issue_ids || []
    const tcIds = article.linked_testcase_ids || []

    pendingLinkedIssueIds.value = [...issueIds]
    pendingLinkedTcIds.value = [...tcIds]

    const all = []

    await Promise.all([
      ...issueIds.map(id =>
        entityLinksApi.getPreview('task', id)
          .then(r => all.push({ id: r.data.id, type: 'task', badge: r.data.human_id, label: r.data.title, status: r.data.status }))
          .catch(() => all.push({ id, type: 'task', badge: null, label: id.slice(0, 8), status: null }))
      ),
      ...tcIds.map(id =>
        entityLinksApi.getPreview('testcase', id)
          .then(r => all.push({ id: r.data.id, type: 'testcase', badge: r.data.human_id, label: r.data.title, status: r.data.status }))
          .catch(() => all.push({ id, type: 'testcase', badge: null, label: id.slice(0, 8), status: null }))
      ),
    ])

    linkedItems.value = all
  } finally {
    linkedItemsLoading.value = false
  }
}

async function addLinkedToArticle(item) {
  if (linkedItems.value.some(e => e.id === item.id)) return
  linkedItems.value.push(item)

  if (item.type === 'task') {
    pendingLinkedIssueIds.value.push(item.id)
    await store.updateArticle(props.article.id, { linked_issue_ids: pendingLinkedIssueIds.value })
  } else if (item.type === 'testcase') {
    pendingLinkedTcIds.value.push(item.id)
    await store.updateArticle(props.article.id, { linked_testcase_ids: pendingLinkedTcIds.value })
  }
}

async function removeLinkedFromArticle(id) {
  const item = linkedItems.value.find(e => e.id === id)
  if (!item) return
  linkedItems.value = linkedItems.value.filter(e => e.id !== id)

  if (item.type === 'task') {
    pendingLinkedIssueIds.value = pendingLinkedIssueIds.value.filter(i => i !== id)
    await store.updateArticle(props.article.id, { linked_issue_ids: pendingLinkedIssueIds.value })
  } else {
    pendingLinkedTcIds.value = pendingLinkedTcIds.value.filter(i => i !== id)
    await store.updateArticle(props.article.id, { linked_testcase_ids: pendingLinkedTcIds.value })
  }
}

function navigateFromArticle(item) {
  if (item.type === 'task' && item.badge) {
    router.push(`/issues/${item.badge}`)
  } else if (item.type === 'testcase') {
    router.push({ path: '/qa', query: { tab: 'tree', tcId: item.id } })
  }
}

const showHistory = ref(false)
const historyLoading = ref(false)
const selectedVersion = ref(null)
const tocItems = ref([])
const activeTocId = ref(null)
let observer = null

function gridUuid() {
  return crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2, 10)
}

const gridContent = computed(() => {
  const raw = props.article.content
  if (!raw) return { version: 'grid-1', rows: [] }
  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (parsed && parsed.version === 'grid-1') return parsed
    return {
      version: 'grid-1',
      rows: [{ id: gridUuid(), columns: [{ id: gridUuid(), span: 12, content: parsed }] }]
    }
  } catch (e) {
    return { version: 'grid-1', rows: [] }
  }
})

const articleTags = computed(() => props.article.tags || [])

const breadcrumbs = computed(() => store.breadcrumbs[props.article.id] || [])

const folderArticles = computed(() =>
  props.article.folder_id
    ? (store.folderArticles[props.article.folder_id] || [])
    : []
)

const authorInitial = computed(() =>
  (props.article.author || '?')[0].toUpperCase()
)

const versionGridContent = computed(() => {
  if (!selectedVersion.value?.content) return { version: 'grid-1', rows: [] }
  try {
    const parsed = JSON.parse(selectedVersion.value.content)
    if (parsed?.version === 'grid-1') return parsed
    return {
      version: 'grid-1',
      rows: [{ id: 'v', columns: [{ id: 'vc', span: 12, content: parsed }] }]
    }
  } catch (e) {
    return { version: 'grid-1', rows: [] }
  }
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('ru-RU', {
    day: 'numeric', month: 'short', year: 'numeric'
  })
}

function handleBreadcrumbClick(crumb) {
  if (crumb.type === 'root') {
    emit('close')
  } else if (crumb.type === 'folder') {
    emit('navigate-to-folder', crumb.id)
  }
}

function handleExportPdf() {
  store.downloadPdf(props.article.id, props.article.slug)
}

async function openHistory() {
  showHistory.value = true
  historyLoading.value = true
  await store.fetchVersions(props.article.id)
  historyLoading.value = false
}

async function loadVersion(versionId) {
  const v = await store.fetchVersion(props.article.id, versionId)
  selectedVersion.value = v
}

function buildToc() {
  const docEl = document.querySelector('.viewer-content')
  if (!docEl) return
  const headings = docEl.querySelectorAll('h1, h2, h3')
  tocItems.value = []
  headings.forEach((el, idx) => {
    const id = `toc-heading-${idx}`
    el.id = id
    tocItems.value.push({ id, text: el.textContent, level: parseInt(el.tagName[1]) })
  })
  if (observer) observer.disconnect()
  observer = new IntersectionObserver(
    (entries) => {
      const visible = entries.find(e => e.isIntersecting)
      if (visible) activeTocId.value = visible.target.id
    },
    { threshold: 0.3 }
  )
  headings.forEach(el => observer.observe(el))
}

function scrollToHeading(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
}

async function loadArticleData() {
  await store.fetchBreadcrumbs(props.article.id)
  if (props.article.folder_id) {
    await store.fetchFolderArticles(props.article.folder_id, props.article.id)
  }
  loadLinkedItems()
  await nextTick()
  buildToc()
}

onMounted(loadArticleData)

watch(() => props.article.id, () => {
  showHistory.value = false
  selectedVersion.value = null
  loadArticleData()
})

onBeforeUnmount(() => {
  if (observer) observer.disconnect()
})
</script>

<style scoped>
.article-viewer {
  position: fixed; inset: 0; z-index: 1000;
  display: grid;
  grid-template-rows: auto auto 1fr;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  overflow: hidden;
}

/* topbar */
.viewer-topbar {
  display: flex; align-items: center; gap: 8px;
  height: 46px; padding: 0 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}
.btn-back { background: none; border: none; color: var(--text-secondary); cursor: pointer; font-size: 13px; padding: 5px 10px; border-radius: 6px; }
.btn-back:hover { background: var(--bg-tertiary); color: var(--text-primary); }
.topbar-sep { width: 1px; height: 18px; background: var(--border-color); margin: 0 4px; }
.topbar-path { font-size: 12px; color: var(--text-secondary); }
.topbar-gap { flex: 1; }
.btn-action { background: transparent; border: 1px solid var(--border-color); color: var(--text-secondary); cursor: pointer; font-size: 12px; padding: 5px 14px; border-radius: 6px; line-height: 1.4; }
.btn-action:hover { border-color: var(--border-color); color: var(--text-primary); background: var(--bg-tertiary); }
.btn-edit { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 500; }
.btn-edit:hover { background: var(--accent-hover); border-color: var(--accent-hover); }

/* article-head */
.viewer-article-head {
  padding: 24px 40px 18px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}
.viewer-crumbs { display: flex; align-items: center; gap: 6px; margin-bottom: 10px; font-size: 12px; color: var(--text-secondary); }
.crumb-link { color: var(--accent); cursor: pointer; }
.crumb-link:hover { text-decoration: underline; }
.crumb-sep { color: var(--text-secondary); font-size: 11px; }

.viewer-title-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 10px; }
.viewer-title { font-size: 26px; font-weight: 600; color: var(--text-primary); line-height: 1.3; }
.viewer-badge { display: inline-flex; align-items: center; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 600; letter-spacing: 0.4px; text-transform: uppercase; flex-shrink: 0; margin-top: 5px; }
.viewer-badge.published { background: rgba(16,185,129,0.12); color: #10b981; }
.viewer-badge.draft { background: rgba(245,158,11,0.12); color: #f59e0b; }

.viewer-meta { display: flex; align-items: center; gap: 14px; font-size: 12px; color: var(--text-secondary); }
.viewer-meta-author { display: flex; align-items: center; gap: 6px; }
.viewer-avatar { width: 22px; height: 22px; border-radius: 50%; background: var(--accent-muted); border: 1px solid var(--accent); display: flex; align-items: center; justify-content: center; font-size: 9px; font-weight: 600; color: var(--accent); }
.viewer-dot { color: var(--text-secondary); }

.viewer-tags { display: flex; gap: 6px; margin-top: 10px; flex-wrap: wrap; }
.viewer-tag { font-size: 11px; padding: 2px 9px; border-radius: 10px; background: var(--bg-tertiary); color: var(--text-secondary); border: 1px solid var(--border-color); }
.viewer-tag.category { color: var(--accent); background: var(--accent-muted); border-color: var(--accent); }

/* body grid */
.viewer-body {
  display: grid;
  grid-template-columns: 1fr 200px;
  align-items: start;
  overflow-y: auto;
}
.viewer-content { padding: 32px 40px 48px; min-width: 0; }
.viewer-document :deep(.grid-editor) { height: auto; }
.viewer-document :deep(.grid-body) { padding: 0; overflow: visible; }
.viewer-document :deep(.grid-col) { background: transparent !important; border: none !important; border-radius: 0 !important; padding: 0 !important; min-height: 0 !important; }
.viewer-document :deep(.grid-row-wrapper) { margin-bottom: 0; gap: 0; }
.viewer-document :deep(.grid-row) { gap: 32px; }

/* Убрать фон/рамку у rich-editor и ProseMirror в readonly */
.viewer-document :deep(.rich-editor) { background: transparent !important; }
.viewer-document :deep(.rich-editor__content) { background: transparent !important; }
.viewer-document :deep(.ProseMirror) { background: transparent !important; border: none !important; padding: 0 !important; min-height: 0 !important; outline: none !important; }
.viewer-document :deep(.rich-editor__counter) { display: none !important; }
.viewer-document :deep(.editor-toolbar) { display: none !important; }

/* ── Prose: heading sizes ── */
.viewer-document :deep(.ProseMirror h1) { font-size: 19px; font-weight: 600; color: var(--text-primary); padding-bottom: 8px; border-bottom: 1px solid var(--border-color); margin: 0 0 12px; line-height: 1.4; }
.viewer-document :deep(.ProseMirror h2) { font-size: 16px; font-weight: 600; color: var(--text-primary); margin: 24px 0 8px; line-height: 1.4; }
.viewer-document :deep(.ProseMirror h3) { font-size: 14px; font-weight: 600; color: var(--text-primary); margin: 16px 0 6px; line-height: 1.4; }

/* ── Prose: paragraphs ── */
.viewer-document :deep(.ProseMirror p) { font-size: 14px; color: var(--text-primary); line-height: 1.8; margin: 0 0 16px; opacity: 0.85; }

/* ── Prose: lists ── */
.viewer-document :deep(.ProseMirror ul) { list-style: disc; padding-left: 20px; margin: 0 0 16px; }
.viewer-document :deep(.ProseMirror ol) { list-style: decimal; padding-left: 20px; margin: 0 0 16px; }
.viewer-document :deep(.ProseMirror li) { font-size: 14px; line-height: 1.7; color: var(--text-primary); opacity: 0.85; }

/* ── Prose: inline code ── */
.viewer-document :deep(.ProseMirror code) { font-family: 'Consolas', 'Fira Code', monospace; font-size: 12px; background: var(--bg-tertiary); color: var(--accent); padding: 2px 6px; border-radius: 4px; }

/* ── Prose: blockquote ── */
.viewer-document :deep(.ProseMirror blockquote) { border-left: 3px solid var(--accent); padding-left: 16px; margin: 0 0 16px; color: var(--text-secondary); font-style: italic; }

/* ── Prose: horizontal rule ── */
.viewer-document :deep(.ProseMirror hr) { border: none; border-top: 1px solid var(--border-color); margin: 20px 0; }

/* ── Tables (TipTap table extension) ── */
.viewer-document :deep(.ProseMirror table) { width: 100%; border-collapse: collapse; font-size: 13px; margin: 0 0 20px; overflow-x: auto; display: table; }
.viewer-document :deep(.ProseMirror th) { text-align: left; padding: 8px 12px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; color: var(--text-secondary); border-bottom: 1px solid var(--border-color); }
.viewer-document :deep(.ProseMirror td) { padding: 10px 12px; border-bottom: 1px solid var(--border-color); color: var(--text-primary); opacity: 0.85; font-size: 13px; }
.viewer-document :deep(.ProseMirror tr:hover td) { background: var(--bg-tertiary); }

/* ── Code block (TipTap code block) ── */
.viewer-document :deep(.ProseMirror pre) { background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; overflow-x: auto; margin: 0 0 20px; }
.viewer-document :deep(.ProseMirror pre code) { background: none; padding: 0; color: var(--text-primary); font-size: 13px; line-height: 1.7; font-family: 'Consolas', 'Fira Code', monospace; }

/* ── Strong / em ── */
.viewer-document :deep(.ProseMirror strong) { font-weight: 600; color: var(--text-primary); opacity: 1; }
.viewer-document :deep(.ProseMirror em) { font-style: italic; }

/* ── Callout block in viewer ── */
.viewer-document :deep(.callout-block .ProseMirror) { background: transparent !important; border: none !important; padding: 0 !important; min-height: 0 !important; }
.viewer-document :deep(.callout-block .rich-editor) { background: transparent !important; }
.viewer-document :deep(.callout-block .rich-editor__content) { background: transparent !important; }

/* ── Expand block in viewer ── */
.viewer-document :deep(.expand-body .ProseMirror) { background: transparent !important; border: none !important; padding: 0 !important; min-height: 0 !important; }
.viewer-document :deep(.expand-body .rich-editor) { background: transparent !important; }

/* toc */
.viewer-toc { padding: 28px 16px 28px 0; border-left: 1px solid var(--border-color); position: sticky; top: 0; align-self: start; }
.toc-label { font-size: 11px; font-weight: 600; letter-spacing: 0.6px; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 10px; padding-left: 10px; }
.toc-list { list-style: none; padding: 0; margin: 0; }
.toc-item { display: block; font-size: 12px; color: var(--text-secondary); padding: 4px 10px; border-radius: 0 4px 4px 0; cursor: pointer; border-left: 2px solid transparent; margin-bottom: 1px; }
.toc-item:hover { color: var(--text-primary); background: var(--bg-tertiary); }
.toc-item.active { color: var(--accent); border-left-color: var(--accent); background: var(--accent-muted); }
.toc-h2 { padding-left: 18px; }
.toc-h3 { padding-left: 26px; }
@media (max-width: 1280px) {
  .viewer-body { grid-template-columns: 1fr; }
  .viewer-toc { display: none; }
}

/* links section */
.viewer-links-section {
  margin-top: 32px;
  border-top: 1px solid var(--border-color);
  padding-top: 16px;
}
.viewer-links-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  padding: 8px 0;
  user-select: none;
}
.viewer-links-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}
.links-count {
  font-weight: 400;
  color: var(--text-secondary);
  margin-left: 4px;
}
.links-toggle {
  color: var(--text-secondary);
  font-size: 11px;
}
.viewer-links-body {
  padding-top: 12px;
}
.links-loading {
  color: var(--text-secondary);
  font-size: 13px;
  padding: 8px 0;
}

/* child pages */
.child-pages { margin-top: 32px; padding: 18px 20px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 10px; }
.child-pages-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary); margin-bottom: 10px; }
.child-page-item { display: flex; align-items: center; gap: 8px; padding: 7px 0; border-bottom: 1px solid var(--border-color); color: var(--accent); font-size: 13px; cursor: pointer; }
.child-page-item:last-child { border-bottom: none; }
.child-page-item:hover { color: var(--accent-hover); }

/* history panel */
.viewer-history { position: fixed; top: 0; right: 0; bottom: 0; width: 280px; background: var(--bg-secondary); border-left: 1px solid var(--border-color); display: flex; flex-direction: column; transform: translateX(100%); transition: transform 0.22s ease; z-index: 1010; box-shadow: -8px 0 32px rgba(0,0,0,0.5); }
.viewer-history.open { transform: translateX(0); }
.history-header { display: flex; align-items: center; justify-content: space-between; padding: 13px 16px; border-bottom: 1px solid var(--border-color); }
.history-header span { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.history-close { background: none; border: none; color: var(--text-secondary); cursor: pointer; font-size: 16px; padding: 2px 6px; border-radius: 4px; line-height: 1; }
.history-close:hover { background: var(--bg-tertiary); color: var(--text-primary); }
.history-loading { padding: 16px; color: var(--text-secondary); font-size: 13px; }
.history-item { padding: 10px 16px; border-bottom: 1px solid var(--border-color); cursor: pointer; }
.history-item:hover { background: var(--bg-tertiary); }
.history-item.active { background: var(--accent-muted); }
.history-date { font-size: 11px; color: var(--text-secondary); }
.history-title { font-size: 13px; color: var(--text-primary); margin-top: 2px; }
.version-preview { border-top: 1px solid var(--border-color); padding: 16px; overflow-y: auto; max-height: 50vh; }
</style>
