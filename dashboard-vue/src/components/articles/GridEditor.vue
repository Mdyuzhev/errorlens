<template>
  <div class="grid-editor">
    <!-- Collaboration presence indicators -->
    <div v-if="collabUsers.length > 1" class="collab-presence">
      <span
        v-for="user in collabUsers"
        :key="user.name"
        class="collab-avatar"
        :style="{ background: user.color }"
        :title="user.name"
      >{{ user.name?.[0]?.toUpperCase() || '?' }}</span>
    </div>
    <div class="grid-body">
      <div
        v-for="(row, rowIdx) in grid.rows"
        :key="row.id"
        class="grid-row-wrapper"
      >
        <div class="grid-row">
          <div
            v-for="col in row.columns"
            :key="col.id"
            class="grid-col"
            :data-span="col.span"
          >
            <div v-if="!readonly" class="col-toolbar">
              <button
                class="col-btn"
                title="Разделить"
                :disabled="!canSplit(row, col)"
                @click="splitColumn(row.id, col.id)"
              >÷</button>
              <button
                v-if="row.columns.length > 1"
                class="col-btn col-btn-danger"
                title="Удалить колонку"
                @click="deleteColumn(row, col)"
              >×</button>
            </div>
            <RichEditor
              :ref="el => setColRef(col.id, el)"
              :modelValue="col.content"
              @update:modelValue="updateColContent(row.id, col.id, $event)"
              placeholder="Начните писать..."
              :uploadEnabled="uploadEnabled"
              :editable="!readonly"
              :showToolbar="false"
              @focus="handleEditorFocus(col.id)"
            />
          </div>
        </div>

        <div v-if="!readonly" class="row-actions">
          <button
            v-if="row.columns.length < 3"
            class="row-btn"
            title="Добавить колонку"
            @click="addColumn(row)"
          >+</button>
          <button
            class="row-btn"
            title="Вверх"
            :disabled="rowIdx === 0"
            @click="moveRow(rowIdx, -1)"
          >↑</button>
          <button
            class="row-btn"
            title="Вниз"
            :disabled="rowIdx === grid.rows.length - 1"
            @click="moveRow(rowIdx, 1)"
          >↓</button>
          <button
            class="row-btn row-btn-danger"
            title="Удалить строку"
            @click="deleteRow(row, rowIdx)"
          >×</button>
        </div>
      </div>

      <button v-if="!readonly" class="add-row-btn" @click="addRow">+ Добавить строку</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount, onMounted, watch } from 'vue'
import RichEditor from '@/components/common/RichEditor.vue'

const props = defineProps({
  modelValue: { type: Object, required: true },
  uploadEnabled: { type: Boolean, default: false },
  readonly: { type: Boolean, default: false },
  articleSlug: { type: String, default: null }
})

const emit = defineEmits(['update:modelValue'])

const grid = computed(() => props.modelValue)
const activeEditor = ref(null)
const activeColId = ref(null)
const colRefs = {}

// Collaboration state
const collabUsers = ref([])
let ydoc = null
let wsProvider = null

const COLLAB_COLORS = [
  '#ef4444', '#f97316', '#eab308', '#22c55e',
  '#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899',
]

function randomUserColor() {
  return COLLAB_COLORS[Math.floor(Math.random() * COLLAB_COLORS.length)]
}

async function initCollaboration() {
  if (!props.articleSlug || props.readonly) return

  try {
    const { useAuthStore } = await import('@/stores/auth')
    const authStore = useAuthStore()
    if (!authStore.accessToken) return

    const Y = await import('yjs')
    const { WebsocketProvider } = await import('y-websocket')

    ydoc = new Y.Doc()
    const wsUrl = `${window.location.origin.replace('http', 'ws')}/collab/`
    wsProvider = new WebsocketProvider(wsUrl, `article:${props.articleSlug}`, ydoc, {
      params: { token: authStore.accessToken }
    })

    // Track presence
    wsProvider.awareness.on('change', () => {
      const users = []
      wsProvider.awareness.getStates().forEach((state) => {
        if (state.user) users.push(state.user)
      })
      collabUsers.value = users
    })

    // Set local user info
    wsProvider.awareness.setLocalStateField('user', {
      name: authStore.user?.username || 'Anonymous',
      color: randomUserColor(),
    })
  } catch (err) {
    console.warn('[Collab] Init failed:', err.message)
  }
}

function destroyCollaboration() {
  if (wsProvider) {
    wsProvider.destroy()
    wsProvider = null
  }
  if (ydoc) {
    ydoc.destroy()
    ydoc = null
  }
  collabUsers.value = []
}

onMounted(() => {
  initCollaboration()
})

function setColRef(colId, el) {
  if (el) {
    colRefs[colId] = el
  }
}

function handleEditorFocus(colId) {
  const colRef = colRefs[colId]
  if (colRef?.editor) {
    activeEditor.value = colRef.editor
    activeColId.value = colId
  }
}

function triggerImageUpload() {
  if (activeColId.value && colRefs[activeColId.value]) {
    const richEditor = colRefs[activeColId.value]
    // Access the hidden file input inside RichEditor
    if (richEditor.$el) {
      const input = richEditor.$el.querySelector('input[type="file"]')
      if (input) input.click()
    }
  }
}

defineExpose({ activeEditor, triggerImageUpload })

function uuid() {
  return crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2, 10)
}

function emitUpdate(newGrid) {
  emit('update:modelValue', { ...newGrid, rows: [...newGrid.rows] })
}

function makeEmptyContent() {
  return { type: 'doc', content: [{ type: 'paragraph' }] }
}

function addRow() {
  const newRow = {
    id: uuid(),
    columns: [{ id: uuid(), span: 12, content: makeEmptyContent() }]
  }
  const updated = { ...grid.value, rows: [...grid.value.rows, newRow] }
  emitUpdate(updated)
}

function deleteRow(row, rowIdx) {
  const hasContent = row.columns.some(c => contentNotEmpty(c.content))
  if (hasContent && !confirm('Удалить строку с содержимым?')) return
  const rows = grid.value.rows.filter((_, i) => i !== rowIdx)
  emitUpdate({ ...grid.value, rows })
}

function moveRow(idx, dir) {
  const rows = [...grid.value.rows]
  const target = idx + dir
  if (target < 0 || target >= rows.length) return
  ;[rows[idx], rows[target]] = [rows[target], rows[idx]]
  emitUpdate({ ...grid.value, rows })
}

function canSplit(row, col) {
  return row.columns.length < 3 && col.span >= 4
}

function splitColumn(rowId, colId) {
  const rows = grid.value.rows.map(row => {
    if (row.id !== rowId) return row
    if (row.columns.length >= 3) return row

    const colIdx = row.columns.findIndex(c => c.id === colId)
    if (colIdx === -1) return row

    const col = row.columns[colIdx]
    if (col.span < 4) return row

    const leftSpan = Math.ceil(col.span / 2)
    const rightSpan = Math.floor(col.span / 2)

    const newColumns = [...row.columns]
    newColumns[colIdx] = { ...col, span: leftSpan }
    newColumns.splice(colIdx + 1, 0, {
      id: uuid(),
      span: rightSpan,
      content: makeEmptyContent()
    })
    return { ...row, columns: newColumns }
  })
  emitUpdate({ ...grid.value, rows })
}

function deleteColumn(row, col) {
  if (row.columns.length <= 1) return
  if (contentNotEmpty(col.content) && !confirm('Удалить колонку с содержимым?')) return

  const rows = grid.value.rows.map(r => {
    if (r.id !== row.id) return r
    const idx = r.columns.findIndex(c => c.id === col.id)
    if (idx === -1) return r

    const newColumns = r.columns.filter(c => c.id !== col.id)
    // Redistribute span to neighbor
    const neighborIdx = idx > 0 ? idx - 1 : 0
    newColumns[neighborIdx] = {
      ...newColumns[neighborIdx],
      span: newColumns[neighborIdx].span + col.span
    }
    return { ...r, columns: newColumns }
  })
  emitUpdate({ ...grid.value, rows })
}

function addColumn(row) {
  if (row.columns.length >= 3) return
  const rows = grid.value.rows.map(r => {
    if (r.id !== row.id) return r
    // Take space from the last column
    const cols = [...r.columns]
    const last = cols[cols.length - 1]
    if (last.span < 4) return r
    const newSpan = Math.floor(last.span / 2)
    cols[cols.length - 1] = { ...last, span: Math.ceil(last.span / 2) }
    cols.push({ id: uuid(), span: newSpan, content: makeEmptyContent() })
    return { ...r, columns: cols }
  })
  emitUpdate({ ...grid.value, rows })
}

function updateColContent(rowId, colId, newContent) {
  const rows = grid.value.rows.map(row => {
    if (row.id !== rowId) return row
    return {
      ...row,
      columns: row.columns.map(col =>
        col.id === colId ? { ...col, content: newContent } : col
      )
    }
  })
  emitUpdate({ ...grid.value, rows })
}

function contentNotEmpty(content) {
  if (!content) return false
  if (!content.content || content.content.length === 0) return false
  return content.content.some(node => {
    if (node.content && node.content.length > 0) return true
    if (node.type === 'image') return true
    return false
  })
}

onBeforeUnmount(() => {
  destroyCollaboration()
  Object.keys(colRefs).forEach(k => delete colRefs[k])
})
</script>

<style scoped>
.grid-editor {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.grid-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px 40px;
}

.grid-row-wrapper {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  align-items: flex-start;
}

.grid-row {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 16px;
  min-width: 0;
}

.grid-col[data-span="12"] { grid-column: span 12; }
.grid-col[data-span="8"]  { grid-column: span 8; }
.grid-col[data-span="6"]  { grid-column: span 6; }
.grid-col[data-span="4"]  { grid-column: span 4; }
.grid-col[data-span="3"]  { grid-column: span 3; }

.grid-col {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border-color, rgba(255,255,255,0.1));
  border-radius: 8px;
  padding: 12px;
  min-height: 120px;
}

.grid-col:hover .col-toolbar {
  opacity: 1;
}

.col-toolbar {
  position: absolute;
  top: 4px;
  right: 4px;
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.15s;
  z-index: 5;
}

.col-btn {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.col-btn:hover:not(:disabled) {
  background: var(--accent);
  color: white;
}

.col-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.col-btn-danger:hover:not(:disabled) {
  background: #ef4444;
}

.row-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.15s;
  padding-top: 4px;
}

.grid-row-wrapper:hover .row-actions {
  opacity: 1;
}

.row-btn {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.row-btn:hover:not(:disabled) {
  background: var(--accent);
  color: white;
}

.row-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.row-btn-danger:hover:not(:disabled) {
  background: #ef4444;
}

.add-row-btn {
  width: 100%;
  padding: 12px;
  border: 2px dashed var(--border-color, rgba(255,255,255,0.15));
  border-radius: 8px;
  background: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 14px;
  transition: all 0.15s;
}

.add-row-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.grid-col :deep(.ProseMirror) {
  min-height: 80px;
}

.collab-presence {
  display: flex;
  gap: 4px;
  padding: 8px 40px 0;
  justify-content: flex-end;
}

.collab-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 12px;
  font-weight: 600;
}
</style>
