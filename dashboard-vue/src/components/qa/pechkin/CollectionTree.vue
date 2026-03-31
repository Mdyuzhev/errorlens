<template>
  <div class="collection-tree">
    <div class="tree-header">
      <span class="tree-title">Collections</span>
      <div class="tree-header-actions">
        <button class="tree-btn" @click="triggerImport" title="Import Postman collection (JSON)">
          <span class="tree-btn-icon">&#8593;</span>
        </button>
        <button class="tree-btn tree-btn-primary" @click="addCollection" title="New collection">
          <span class="tree-btn-icon">+</span>
        </button>
      </div>
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
          <!-- Кнопки появляются при hover -->
          <div class="row-actions">
            <button class="row-btn" @click.stop="openRunner(col)" title="Run collection">&#9654;</button>
            <button class="row-btn" @click.stop="addFolder(col.id)" title="New folder">&#128193;</button>
            <button class="row-btn" @click.stop="addRequest(col.id)" title="New request">+</button>
          </div>
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
        <template v-if="ctx.type === 'collection'">
          <button class="ctx-item" @click="renameCollection(ctx.item)">&#9998; Rename</button>
          <button class="ctx-item" @click="exportCollection(ctx.item.id)">&#8595; Export as Postman</button>
          <div class="ctx-divider"></div>
          <button class="ctx-item ctx-danger" @click="deleteCollection(ctx.item.id)">&#128465; Delete</button>
        </template>
        <template v-else-if="ctx.type === 'folder'">
          <button class="ctx-item" @click="renameFolder(ctx.item)">&#9998; Rename</button>
          <div class="ctx-divider"></div>
          <button class="ctx-item ctx-danger" @click="deleteFolder(ctx.item.id)">&#128465; Delete</button>
        </template>
        <template v-else-if="ctx.type === 'request'">
          <button class="ctx-item" @click="renameReq(ctx.item)">&#9998; Rename</button>
          <button class="ctx-item" @click="duplicateReq(ctx.item.id)">&#9112; Duplicate</button>
          <div class="ctx-divider"></div>
          <button class="ctx-item ctx-danger" @click="deleteReq(ctx.item.id)">&#128465; Delete</button>
        </template>
      </div>
    </Teleport>

    <!-- Collection Runner modal -->
    <CollectionRunner
      v-if="runnerCollection"
      :collection-id="runnerCollection.id"
      :collection-name="runnerCollection.name"
      :requests="runnerCollection.requests"
      @close="runnerCollection = null"
    />

    <!-- Import Modal -->
    <Teleport to="body">
      <div v-if="showImportModal" class="import-overlay" @click.self="showImportModal = false">
        <div class="import-modal">
          <div class="import-modal-header">
            <h3 class="import-modal-title">Import Postman Collection</h3>
            <button class="import-close" @click="showImportModal = false">&times;</button>
          </div>

          <!-- Drop zone -->
          <div
            class="import-dropzone"
            :class="{ dragover: importDragOver, 'has-file': !!importFile }"
            @dragover="onImportDragOver"
            @dragleave="onImportDragLeave"
            @drop="onImportDrop"
            @click="$refs.importFileInput.click()"
          >
            <div v-if="!importFile" class="dropzone-placeholder">
              <div class="dropzone-icon">&#128194;</div>
              <div class="dropzone-text">Drag Postman JSON here<br>or click to browse</div>
            </div>
            <div v-else class="dropzone-file">
              <span class="dropzone-file-icon">&#128196;</span>
              <span class="dropzone-file-name">{{ importFile.name }}</span>
              <button class="dropzone-clear" @click.stop="importFile = null">&times;</button>
            </div>
            <input
              ref="importFileInput"
              type="file"
              accept=".json"
              style="display:none"
              @change="onImportFileSelect"
            />
          </div>

          <!-- Target selection -->
          <div class="import-target-section">
            <label class="import-section-label">Import into:</label>
            <div class="import-radio-group">
              <label class="import-radio">
                <input type="radio" v-model="importTarget" value="existing" />
                <span>Existing collection</span>
              </label>
              <label class="import-radio">
                <input type="radio" v-model="importTarget" value="new" />
                <span>New collection</span>
              </label>
            </div>

            <select
              v-if="importTarget === 'existing'"
              v-model="importTargetColId"
              class="import-select"
            >
              <option v-for="col in store.collections" :key="col.id" :value="col.id">
                {{ col.name }}
              </option>
              <option v-if="!store.collections.length" value="" disabled>No collections</option>
            </select>

            <input
              v-else
              v-model="importNewName"
              class="import-input"
              placeholder="New collection name..."
            />
          </div>

          <!-- Actions -->
          <div class="import-modal-actions">
            <button class="import-btn-cancel" @click="showImportModal = false">Cancel</button>
            <button
              class="import-btn-import"
              :disabled="!importFile || importLoading || (importTarget === 'existing' && !importTargetColId)"
              @click="doImport"
            >
              {{ importLoading ? 'Importing...' : 'Import' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { usePechkinStore } from '@/stores/pechkin'
import { pechkinApi } from '@/services/api'
import CollectionRunner from './CollectionRunner.vue'

const props = defineProps({ projectId: { type: String, required: true } })
const store = usePechkinStore()

const expanded = reactive({})
const expandedFolders = reactive({})
const runnerCollection = ref(null)
const ctx = reactive({ show: false, x: 0, y: 0, type: '', item: null })

// Import modal state
const showImportModal = ref(false)
const importTarget = ref('existing')
const importNewName = ref('')
const importTargetColId = ref(null)
const importFile = ref(null)
const importLoading = ref(false)
const importDragOver = ref(false)

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

function openRunner(col) {
  const reqs = collectAllRequests(col)
  runnerCollection.value = { id: col.id, name: col.name, requests: reqs }
}

function collectAllRequests(col) {
  const list = []
  function walkFolder(folder) {
    for (const req of (folder.requests || [])) {
      list.push({ id: req.id, name: req.name, method: req.method })
    }
    for (const child of (folder.children || folder.folders || [])) {
      walkFolder(child)
    }
  }
  for (const folder of (col.folders || [])) walkFolder(folder)
  for (const req of (col.requests || [])) list.push({ id: req.id, name: req.name, method: req.method })
  return list
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

async function exportCollection(id) {
  try {
    await store.exportCollection(id)
  } catch (err) {
    alert('Export failed: ' + err.message)
  }
}

async function renameCollection(col) {
  const name = prompt('New name:', col.name)
  if (!name || name === col.name) return
  await store.updateCollectionName(col.id, name)
}

async function renameFolder(folder) {
  const name = prompt('New folder name:', folder.name)
  if (!name || name === folder.name) return
  await pechkinApi.updateFolder(folder.id, { name })
  const pid = store.collections[0]?.project_id
  if (pid) await store.fetchCollections(pid)
}

async function renameReq(req) {
  const name = prompt('New request name:', req.name)
  if (!name || name === req.name) return
  await store.updateRequest(req.id, { name })
  const pid = store.collections[0]?.project_id
  if (pid) await store.fetchCollections(pid)
}

// Import modal functions
function triggerImport() {
  showImportModal.value = true
  importTarget.value = 'existing'
  importTargetColId.value = store.collections[0]?.id || null
  importNewName.value = ''
  importFile.value = null
}

function onImportDragOver(e) {
  e.preventDefault()
  importDragOver.value = true
}

function onImportDragLeave() {
  importDragOver.value = false
}

function onImportDrop(e) {
  e.preventDefault()
  importDragOver.value = false
  const f = e.dataTransfer?.files?.[0]
  if (f && f.name.endsWith('.json')) {
    importFile.value = f
    importNewName.value = f.name.replace('.postman_collection.json', '').replace('.json', '').replace(/_/g, ' ')
  }
}

function onImportFileSelect(e) {
  const f = e.target.files?.[0]
  if (f) {
    importFile.value = f
    importNewName.value = f.name.replace('.postman_collection.json', '').replace('.json', '').replace(/_/g, ' ')
  }
}

async function doImport() {
  if (!importFile.value) return
  importLoading.value = true
  try {
    let targetColId = importTargetColId.value

    if (importTarget.value === 'new') {
      let colName = importNewName.value.trim() || 'Imported Collection'
      try {
        const text = await importFile.value.text()
        const json = JSON.parse(text)
        if (json.info?.name) colName = json.info.name
      } catch { /* use filename */ }
      const newCol = await store.createCollection(props.projectId, colName)
      targetColId = newCol.id
      expanded[newCol.id] = true
    }

    const formData = new FormData()
    formData.append('file', importFile.value)
    const result = await store.importPostmanFile(targetColId, formData)

    const msg = `Imported: ${result.imported_requests} requests, ${result.imported_folders} folders`
    if (window.showToast) window.showToast(msg, 'success', 4000)
    else alert(msg)

    showImportModal.value = false
    importFile.value = null
  } catch (err) {
    const msg = 'Import error: ' + (err?.response?.data?.detail || err.message || 'Unknown error')
    if (window.showToast) window.showToast(msg, 'error', 5000)
    else alert(msg)
  } finally {
    importLoading.value = false
  }
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
/* Кнопки в header */
.tree-btn {
  width: 28px;
  height: 28px;
  border: 1px solid var(--border-color);
  border-radius: 5px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  font-size: 14px;
  flex-shrink: 0;
}
.tree-btn:hover { color: var(--accent); border-color: var(--accent); background: var(--accent-muted); }
.tree-btn-primary { background: var(--accent); color: white; border-color: var(--accent); }
.tree-btn-primary:hover { opacity: 0.85; color: white; }
.tree-btn-icon { font-size: 14px; line-height: 1; }

/* Кнопки в row */
.row-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.15s;
}
.collection-row:hover .row-actions,
.tree-row:hover .row-actions {
  opacity: 1;
}
.row-btn {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  background: none;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  transition: all 0.12s;
}
.row-btn:hover { background: var(--bg-tertiary); color: var(--accent); }

/* Убрать старые small кнопки */
.tree-add-btn.small { display: none; }
.tree-loading { padding: 20px; text-align: center; color: var(--text-secondary); font-size: 12px; }
.tree-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
  scrollbar-width: thin;
  scrollbar-color: var(--border-color) transparent;
}
.tree-row {
  display: flex; align-items: center; gap: 6px; padding: 5px 14px; cursor: pointer;
  font-size: 13px; color: var(--text-primary); transition: background 0.1s;
  min-height: 32px;
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
.ctx-divider {
  height: 1px;
  background: var(--border-color);
  margin: 4px 0;
}

/* Import Modal */
.import-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.import-modal {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 24px;
  width: 460px;
  max-width: 95vw;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.import-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.import-modal-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.import-close {
  background: none;
  border: none;
  font-size: 20px;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}
.import-close:hover { color: var(--text-primary); }

.import-dropzone {
  border: 2px dashed var(--border-color);
  border-radius: 8px;
  padding: 28px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  min-height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.import-dropzone:hover, .import-dropzone.dragover {
  border-color: var(--accent);
  background: var(--accent-muted);
}
.import-dropzone.has-file {
  border-color: var(--success);
  border-style: solid;
}

.dropzone-placeholder { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.dropzone-icon { font-size: 32px; }
.dropzone-text { font-size: 13px; color: var(--text-secondary); line-height: 1.5; }

.dropzone-file { display: flex; align-items: center; gap: 8px; }
.dropzone-file-icon { font-size: 20px; }
.dropzone-file-name { font-size: 13px; color: var(--text-primary); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dropzone-clear { background: none; border: none; color: var(--text-secondary); cursor: pointer; font-size: 18px; padding: 0 4px; }
.dropzone-clear:hover { color: var(--error); }

.import-target-section { display: flex; flex-direction: column; gap: 8px; }
.import-section-label { font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }

.import-radio-group { display: flex; gap: 16px; }
.import-radio { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--text-primary); cursor: pointer; }

.import-select, .import-input {
  padding: 8px 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  width: 100%;
  box-sizing: border-box;
}
.import-select:focus, .import-input:focus { border-color: var(--accent); }

.import-modal-actions { display: flex; justify-content: flex-end; gap: 8px; }

.import-btn-cancel {
  padding: 8px 16px;
  background: none;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
}
.import-btn-cancel:hover { color: var(--text-primary); }

.import-btn-import {
  padding: 8px 20px;
  background: var(--accent);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
}
.import-btn-import:hover:not(:disabled) { opacity: 0.85; }
.import-btn-import:disabled { opacity: 0.4; cursor: not-allowed; }
</style>
