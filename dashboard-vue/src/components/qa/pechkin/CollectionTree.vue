<template>
  <div class="collection-tree">
    <div class="tree-header">
      <span class="tree-title">Collections</span>
      <div class="tree-header-actions">
        <button class="tree-add-btn" @click="triggerImport" title="Import Postman JSON">&#8593;</button>
        <button class="tree-add-btn" @click="addCollection" title="New Collection">+</button>
      </div>
      <input
        ref="importInput"
        type="file"
        accept=".json"
        style="display: none"
        @change="handleImportFile"
      />
    </div>

    <div v-if="store.loading" class="tree-loading">Loading...</div>

    <div v-else class="tree-list">
      <div v-for="col in store.collections" :key="col.id" class="tree-collection">
        <!-- Collection row -->
        <div class="tree-row collection-row" @contextmenu.prevent="openCtx($event, 'collection', col)">
          <button class="expand-btn" @click="toggle(col.id)">
            {{ expanded[col.id] ? '\u25BE' : '\u25B8' }}
          </button>
          <span class="collection-name" @click="toggle(col.id)">{{ col.name }}</span>
          <button class="tree-add-btn small" @click.stop="addFolder(col.id)" title="Add folder">+</button>
          <button class="tree-add-btn small" @click.stop="addRequest(col.id)" title="Add request">R</button>
        </div>

        <!-- Children (folders + requests) -->
        <div v-if="expanded[col.id]" class="tree-children">
          <!-- Folders -->
          <div v-for="folder in (col.folders || [])" :key="'f-'+folder.id" class="tree-folder">
            <div class="tree-row folder-row" @contextmenu.prevent="openCtx($event, 'folder', folder)">
              <button class="expand-btn" @click="toggleFolder(folder.id)">
                {{ expandedFolders[folder.id] ? '\u25BE' : '\u25B8' }}
              </button>
              <span class="folder-name">{{ folder.name }}</span>
              <button class="tree-add-btn small" @click.stop="addRequest(col.id, folder.id)" title="Add request">R</button>
            </div>
            <!-- Folder requests -->
            <div v-if="expandedFolders[folder.id]" class="tree-children">
              <div
                v-for="req in (folder.requests || [])" :key="'r-'+req.id"
                class="tree-row request-row"
                :class="{ active: store.activeRequestId === req.id }"
                @click="store.openRequest(req.id)"
                @contextmenu.prevent="openCtx($event, 'request', req)"
              >
                <span class="method-badge" :class="methodClass(req.method)">{{ req.method }}</span>
                <span class="request-name">{{ req.name || req.url || 'Untitled' }}</span>
              </div>
              <!-- Sub-folders -->
              <div v-for="sub in (folder.children || [])" :key="'sf-'+sub.id" class="tree-subfolder">
                <div class="tree-row folder-row" @contextmenu.prevent="openCtx($event, 'folder', sub)">
                  <span class="folder-indent">{{ sub.name }}</span>
                </div>
                <div v-for="req in (sub.requests || [])" :key="'sr-'+req.id"
                  class="tree-row request-row sub"
                  :class="{ active: store.activeRequestId === req.id }"
                  @click="store.openRequest(req.id)"
                  @contextmenu.prevent="openCtx($event, 'request', req)"
                >
                  <span class="method-badge" :class="methodClass(req.method)">{{ req.method }}</span>
                  <span class="request-name">{{ req.name || req.url || 'Untitled' }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Root-level requests -->
          <div
            v-for="req in (col.requests || [])" :key="'r-'+req.id"
            class="tree-row request-row"
            :class="{ active: store.activeRequestId === req.id }"
            @click="store.openRequest(req.id)"
            @contextmenu.prevent="openCtx($event, 'request', req)"
          >
            <span class="method-badge" :class="methodClass(req.method)">{{ req.method }}</span>
            <span class="request-name">{{ req.name || req.url || 'Untitled' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Context menu -->
    <Teleport to="body">
      <div v-if="ctx.show" class="ctx-menu" :style="{ top: ctx.y + 'px', left: ctx.x + 'px' }" @click="ctx.show = false">
        <template v-if="ctx.type === 'request'">
          <button class="ctx-item" @click="duplicateReq(ctx.item.id)">Duplicate</button>
          <button class="ctx-item ctx-danger" @click="deleteReq(ctx.item.id)">Delete</button>
        </template>
        <template v-else-if="ctx.type === 'folder'">
          <button class="ctx-item ctx-danger" @click="deleteFolder(ctx.item.id)">Delete Folder</button>
        </template>
        <template v-else-if="ctx.type === 'collection'">
          <button class="ctx-item ctx-danger" @click="deleteCollection(ctx.item.id)">Delete Collection</button>
        </template>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { usePechkinStore } from '@/stores/pechkin'

const props = defineProps({ projectId: { type: String, required: true } })
const store = usePechkinStore()

const importInput = ref(null)
const expanded = reactive({})
const expandedFolders = reactive({})
const ctx = reactive({ show: false, x: 0, y: 0, type: '', item: null })

onMounted(() => {
  store.fetchCollections(props.projectId)
  document.addEventListener('click', closeCtx)
})
onUnmounted(() => document.removeEventListener('click', closeCtx))

function methodClass(m) {
  const map = { GET: 'method-get', POST: 'method-post', PUT: 'method-put', PATCH: 'method-patch', DELETE: 'method-delete' }
  return map[m?.toUpperCase()] || 'method-get'
}

function toggle(id) { expanded[id] = !expanded[id] }
function toggleFolder(id) { expandedFolders[id] = !expandedFolders[id] }

async function addCollection() {
  const name = prompt('Collection name:')
  if (!name) return
  const col = await store.createCollection(props.projectId, name)
  expanded[col.id] = true
}

async function addFolder(colId) {
  const name = prompt('Folder name:')
  if (!name) return
  await store.createFolder(colId, name)
}

async function addRequest(colId, folderId = null) {
  await store.createRequest(colId, { name: 'New Request', method: 'GET', url: '', folder_id: folderId })
}

function openCtx(e, type, item) {
  ctx.show = true
  ctx.x = e.clientX
  ctx.y = e.clientY
  ctx.type = type
  ctx.item = item
}
function closeCtx() { ctx.show = false }

async function duplicateReq(id) { await store.duplicateRequest(id) }
async function deleteReq(id) { if (confirm('Delete request?')) await store.deleteRequest(id) }
async function deleteFolder(id) { if (confirm('Delete folder?')) await store.deleteFolder(id) }
async function deleteCollection(id) { if (confirm('Delete collection?')) await store.deleteCollection(id) }

function triggerImport() {
  importInput.value?.click()
}

async function handleImportFile(e) {
  const file = e.target.files?.[0]
  if (!file) return
  // Pick first collection or create one
  let col = store.collections[0]
  if (!col) {
    col = await store.createCollection(props.projectId, 'Imported')
    expanded[col.id] = true
  }
  const formData = new FormData()
  formData.append('file', file)
  try {
    await store.importPostmanFile(col.id, formData)
  } catch (err) {
    alert('Import failed: ' + (err?.response?.data?.detail || err.message))
  }
  // Reset input so same file can be re-imported
  if (importInput.value) importInput.value.value = ''
}
</script>

<style scoped>
.collection-tree {
  background: var(--bg-secondary);
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.tree-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-color);
}
.tree-title { font-size: 13px; font-weight: 600; color: var(--text-primary); flex: 1; }
.tree-header-actions { display: flex; gap: 4px; }
.tree-add-btn {
  width: 24px; height: 24px; border: 1px solid var(--border-color); border-radius: 4px;
  background: var(--bg-tertiary); color: var(--text-secondary); cursor: pointer; font-size: 14px;
  display: flex; align-items: center; justify-content: center;
}
.tree-add-btn:hover { color: var(--accent); border-color: var(--accent); }
.tree-add-btn.small { width: 20px; height: 20px; font-size: 11px; }
.tree-loading { padding: 20px; text-align: center; color: var(--text-secondary); font-size: 12px; }
.tree-list { flex: 1; overflow-y: auto; padding: 4px 0; }
.tree-row {
  display: flex; align-items: center; gap: 6px; padding: 4px 14px; cursor: pointer;
  font-size: 12px; color: var(--text-primary); transition: background 0.1s;
}
.tree-row:hover { background: var(--bg-tertiary); }
.tree-row.active { background: var(--accent-subtle); }
.tree-children { padding-left: 12px; }
.expand-btn {
  background: none; border: none; color: var(--text-secondary); cursor: pointer;
  font-size: 10px; width: 16px; padding: 0;
}
.collection-name { font-weight: 600; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.folder-name { flex: 1; color: var(--text-secondary); font-weight: 500; }
.folder-indent { padding-left: 8px; color: var(--text-secondary); font-size: 12px; }
.request-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.request-row.sub { padding-left: 26px; }
.method-badge {
  font-size: 9px; font-weight: 700; padding: 1px 4px; border-radius: 3px;
  text-transform: uppercase; flex-shrink: 0; min-width: 32px; text-align: center;
}
.method-get { color: var(--success); background: rgba(16, 185, 129, 0.12); }
.method-post { color: var(--accent); background: var(--accent-muted); }
.method-put { color: var(--warning); background: rgba(245, 158, 11, 0.12); }
.method-patch { color: var(--warning); background: rgba(245, 158, 11, 0.08); }
.method-delete { color: var(--error); background: rgba(239, 68, 68, 0.12); }
.ctx-menu {
  position: fixed; z-index: 9999; background: var(--bg-card); border: 1px solid var(--border-color);
  border-radius: 6px; box-shadow: var(--shadow-dropdown); padding: 4px 0; min-width: 140px;
}
.ctx-item {
  display: block; width: 100%; text-align: left; padding: 6px 14px; border: none;
  background: none; color: var(--text-primary); font-size: 12px; cursor: pointer;
}
.ctx-item:hover { background: var(--bg-tertiary); }
.ctx-danger { color: var(--error); }
</style>
