<template>
  <div class="article-viewer">
    <div class="viewer-header">
      <button class="btn-back" @click="emit('close')">← Назад</button>
      <span class="viewer-title">{{ article.title }}</span>
      <span class="viewer-status" :class="article.status">{{ article.status }}</span>
      <button class="btn btn-secondary btn-sm" @click="handleExportPdf">PDF</button>
      <button class="btn btn-secondary btn-sm" @click="openHistory">История</button>
      <button class="btn btn-primary btn-sm" @click="emit('edit')">Edit</button>
    </div>

    <nav class="viewer-breadcrumbs" v-if="breadcrumbs.length">
      <template v-for="(crumb, idx) in breadcrumbs" :key="crumb.id">
        <span v-if="idx > 0" class="crumb-sep">›</span>
        <span
          v-if="crumb.type !== 'article'"
          class="crumb-link"
          @click="handleBreadcrumbClick(crumb)"
        >{{ crumb.name }}</span>
        <span v-else class="crumb-current">{{ crumb.name }}</span>
      </template>
    </nav>

    <div v-if="article.category || articleTags.length" class="viewer-subheader">
      <span v-if="article.category" class="viewer-category">{{ article.category }}</span>
      <span v-for="tag in articleTags" :key="tag" class="viewer-tag">{{ tag }}</span>
    </div>

    <div class="viewer-meta">
      <span v-if="article.author">{{ article.author }}</span>
      <span class="meta-sep" v-if="article.author">·</span>
      <span>{{ formatDate(article.updated_at || article.created_at) }}</span>
      <span class="meta-sep">·</span>
      <span>{{ article.views || 0 }} просмотров</span>
    </div>

    <div class="viewer-body">
      <div class="viewer-content-area">
        <div class="viewer-document">
          <GridEditor :modelValue="gridContent" :readonly="true" />
        </div>
        <div class="child-pages" v-if="folderArticles.length">
          <h3>Статьи в этой папке</h3>
          <ul>
            <li v-for="a in folderArticles" :key="a.id">
              <a href="#" @click.prevent="emit('open-article', a.id)">{{ a.title }}</a>
            </li>
          </ul>
        </div>
      </div>

      <aside class="viewer-toc" v-if="tocItems.length">
        <div class="toc-title">Содержание</div>
        <ul>
          <li
            v-for="item in tocItems"
            :key="item.id"
            :class="['toc-item', `toc-h${item.level}`, { active: activeTocId === item.id }]"
            @click="scrollToHeading(item.id)"
          >{{ item.text }}</li>
        </ul>
      </aside>
    </div>

    <div class="history-panel" v-if="showHistory">
      <div class="history-header">
        <span>История версий</span>
        <button class="history-close" @click="showHistory = false; selectedVersion = null">✕</button>
      </div>
      <div v-if="historyLoading" class="history-loading">Загрузка...</div>
      <ul v-else class="history-list">
        <li
          v-for="v in store.versions[article.id] || []"
          :key="v.id"
          @click="loadVersion(v.id)"
          :class="{ active: selectedVersion?.id === v.id }"
        >
          {{ formatDate(v.created_at) }} — {{ v.title }}
        </li>
      </ul>
      <div v-if="selectedVersion" class="version-preview">
        <GridEditor :modelValue="versionGridContent" :readonly="true" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import GridEditor from './GridEditor.vue'
import { useArticlesStore } from '@/stores/articles'

const props = defineProps({
  article: { type: Object, required: true }
})

const emit = defineEmits(['close', 'edit', 'navigate-to-folder', 'open-article'])

const store = useArticlesStore()
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
  const docEl = document.querySelector('.viewer-document')
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
.article-viewer { position: fixed; inset: 0; z-index: 1000; display: flex; flex-direction: column; background: var(--bg-primary); }
.viewer-header { display: flex; align-items: center; gap: 12px; height: 48px; padding: 0 16px; background: var(--bg-card); border-bottom: 1px solid var(--bg-secondary); flex-shrink: 0; }
.btn-back { background: none; border: none; color: var(--text-secondary); cursor: pointer; font-size: 14px; padding: 4px 8px; border-radius: 6px; white-space: nowrap; }
.btn-back:hover { background: var(--bg-secondary); color: var(--text-primary); }
.viewer-title { flex: 1; font-size: 18px; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.viewer-status { padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase; flex-shrink: 0; }
.viewer-status.published { background: rgba(16, 185, 129, 0.2); color: #10b981; }
.viewer-status.draft { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
.btn-sm { padding: 4px 12px !important; font-size: 13px !important; }
.viewer-breadcrumbs { display: flex; align-items: center; gap: 6px; padding: 6px 16px; background: var(--bg-card); border-bottom: 1px solid var(--bg-secondary); font-size: 13px; flex-shrink: 0; }
.crumb-sep { color: var(--text-secondary); }
.crumb-link { color: var(--accent); cursor: pointer; }
.crumb-link:hover { text-decoration: underline; }
.crumb-current { color: var(--text-secondary); }
.viewer-subheader { display: flex; align-items: center; gap: 8px; padding: 6px 16px; background: var(--bg-card); border-bottom: 1px solid var(--bg-secondary); flex-shrink: 0; }
.viewer-category { font-size: 13px; color: var(--accent); font-weight: 500; }
.viewer-tag { font-size: 12px; color: var(--text-secondary); background: var(--bg-secondary); padding: 2px 8px; border-radius: 10px; }
.viewer-meta { display: flex; align-items: center; gap: 6px; padding: 6px 16px; background: var(--bg-card); border-bottom: 1px solid var(--bg-secondary); font-size: 12px; color: var(--text-secondary); flex-shrink: 0; }
.meta-sep { color: var(--text-secondary); opacity: 0.5; }
.viewer-body { flex: 1; overflow-y: auto; background: var(--bg-secondary); padding: 40px 20px; display: flex; gap: 24px; }
.viewer-content-area { flex: 1; min-width: 0; }
.viewer-document { background: var(--bg-card); max-width: 860px; margin: 0 auto; padding: 60px 80px; border-radius: 8px; box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3); min-height: calc(100vh - 180px); }
.viewer-document :deep(.grid-editor) { height: auto; }
.viewer-document :deep(.grid-body) { padding: 0; overflow: visible; }
.viewer-toc { width: 200px; flex-shrink: 0; position: sticky; top: 0; max-height: calc(100vh - 100px); overflow-y: auto; }
.toc-title { font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 8px; }
.viewer-toc ul { list-style: none; padding: 0; margin: 0; }
.toc-item { font-size: 13px; color: var(--text-secondary); cursor: pointer; padding: 4px 8px; border-radius: 4px; }
.toc-item:hover { color: var(--text-primary); background: var(--bg-tertiary); }
.toc-item.active { color: var(--accent); border-left: 2px solid var(--accent); }
.toc-h2 { padding-left: 16px; }
.toc-h3 { padding-left: 28px; }
@media (max-width: 1280px) { .viewer-toc { display: none; } }
.child-pages { max-width: 860px; margin: 24px auto 0; padding: 20px 24px; background: var(--bg-card); border-radius: 8px; border: 1px solid var(--border-color); }
.child-pages h3 { font-size: 14px; font-weight: 600; color: var(--text-primary); margin: 0 0 12px; }
.child-pages ul { list-style: none; padding: 0; margin: 0; }
.child-pages li { padding: 6px 0; border-bottom: 1px solid var(--bg-secondary); }
.child-pages li:last-child { border-bottom: none; }
.child-pages a { color: var(--accent); text-decoration: none; font-size: 14px; }
.child-pages a:hover { text-decoration: underline; }
.history-panel { position: fixed; top: 0; right: 0; width: 360px; height: 100vh; background: var(--bg-card); border-left: 1px solid var(--border-color); z-index: 1001; display: flex; flex-direction: column; box-shadow: -4px 0 24px rgba(0, 0, 0, 0.2); }
.history-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid var(--bg-secondary); font-weight: 600; color: var(--text-primary); }
.history-close { background: none; border: none; color: var(--text-secondary); cursor: pointer; font-size: 16px; padding: 4px 8px; border-radius: 4px; }
.history-close:hover { background: var(--bg-secondary); color: var(--text-primary); }
.history-loading { padding: 16px; color: var(--text-secondary); font-size: 13px; }
.history-list { list-style: none; padding: 0; margin: 0; overflow-y: auto; flex: 1; }
.history-list li { padding: 10px 16px; font-size: 13px; color: var(--text-secondary); cursor: pointer; border-bottom: 1px solid var(--bg-secondary); }
.history-list li:hover { background: var(--bg-secondary); }
.history-list li.active { background: var(--bg-tertiary); color: var(--accent); }
.version-preview { border-top: 1px solid var(--border-color); padding: 16px; overflow-y: auto; max-height: 50vh; }
</style>
