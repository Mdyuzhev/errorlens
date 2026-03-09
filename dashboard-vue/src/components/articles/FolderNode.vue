<template>
  <div>
    <div
      class="tree-item"
      :class="{ selected, 'drop-target': isDragOver }"
      :style="{ paddingLeft: (depth * 16 + 12) + 'px' }"
      :draggable="true"
      @click="$emit('select', folder.id)"
      @contextmenu.prevent="showContextMenu"
      @dragstart="onDragStart"
      @dragover.prevent="onDragOver"
      @dragleave="onDragLeave"
      @drop="onDrop"
      @dragend="onDragEnd"
    >
      <span
        v-if="hasChildren"
        class="tree-arrow"
        @click.stop="$emit('toggle', folder.id)"
      >
        <AppIcon :name="expanded ? 'chevron-down' : 'chevron-right'" :size="14" :glow="false" />
      </span>
      <span v-else class="tree-arrow-spacer"></span>
      <span class="tree-icon"><AppIcon name="folder" :size="14" /></span>
      <span class="folder-name">{{ folder.name }}</span>
      <span v-if="folder.articles_count" class="folder-count">{{ folder.articles_count }}</span>
    </div>

    <div v-if="expanded" class="folder-children">
      <!-- Nested articles -->
      <div
        v-for="article in folder.articles"
        :key="article.id"
        class="tree-item article-item"
        :style="{ paddingLeft: ((depth + 1) * 16 + 28) + 'px' }"
        :draggable="true"
        @dragstart="onArticleDragStart($event, article)"
        @click="$emit('select', folder.id)"
      >
        <span class="tree-icon"><AppIcon name="file" :size="14" /></span>
        <span class="article-name">{{ article.title }}</span>
      </div>

      <!-- Nested folders -->
      <FolderNode
        v-for="child in folder.children"
        :key="child.id"
        :folder="child"
        :depth="depth + 1"
        :expanded="expandedIds.has(child.id)"
        :selected="selectedFolderId === child.id"
        :expanded-ids="expandedIds"
        :selected-folder-id="selectedFolderId"
        @select="$emit('select', $event)"
        @toggle="$emit('toggle', $event)"
        @create="$emit('create', $event)"
        @rename="$emit('rename', $event)"
        @delete="$emit('delete', $event)"
        @drop="$emit('drop', $event)"
      />
    </div>

    <!-- Context Menu -->
    <div
      v-if="contextMenu"
      class="context-menu"
      :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }"
    >
      <div class="context-item" @click="handleRename">Rename</div>
      <div v-if="depth < 2" class="context-item" @click="handleNewSubfolder">New Subfolder</div>
      <div class="context-item danger" @click="handleDelete">Delete</div>
    </div>
    <div v-if="contextMenu" class="context-backdrop" @click="contextMenu = null"></div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'

const props = defineProps({
  folder: { type: Object, required: true },
  depth: { type: Number, default: 0 },
  expanded: { type: Boolean, default: false },
  selected: { type: Boolean, default: false },
  expandedIds: { type: Set, default: () => new Set() },
  selectedFolderId: { type: String, default: null },
})

const emit = defineEmits(['select', 'toggle', 'create', 'rename', 'delete', 'drop'])

const contextMenu = ref(null)
const isDragOver = ref(false)

const hasChildren = computed(() =>
  (props.folder.children?.length > 0) || (props.folder.articles?.length > 0)
)

function showContextMenu(e) {
  contextMenu.value = { x: e.clientX, y: e.clientY }
}

function handleRename() {
  contextMenu.value = null
  emit('rename', { id: props.folder.id, name: props.folder.name })
}

function handleNewSubfolder() {
  contextMenu.value = null
  emit('create', props.folder.id)
  // Auto-expand this folder
  if (!props.expanded) {
    emit('toggle', props.folder.id)
  }
}

function handleDelete() {
  contextMenu.value = null
  if (confirm(`Delete folder "${props.folder.name}" and all subfolders?`)) {
    emit('delete', props.folder.id)
  }
}

// Drag & Drop
function onDragStart(e) {
  e.dataTransfer.setData('application/json', JSON.stringify({
    itemId: props.folder.id,
    itemType: 'folder',
  }))
  e.dataTransfer.effectAllowed = 'move'
}

function onArticleDragStart(e, article) {
  e.stopPropagation()
  e.dataTransfer.setData('application/json', JSON.stringify({
    itemId: article.id,
    itemType: 'article',
  }))
  e.dataTransfer.effectAllowed = 'move'
}

function onDragOver(e) {
  try {
    e.dataTransfer.dropEffect = 'move'
    isDragOver.value = true
  } catch {
    // ignore
  }
}

function onDragLeave() {
  isDragOver.value = false
}

function onDrop(e) {
  e.stopPropagation()
  isDragOver.value = false
  try {
    const data = JSON.parse(e.dataTransfer.getData('application/json'))
    // Prevent dropping on self
    if (data.itemType === 'folder' && data.itemId === props.folder.id) return
    emit('drop', { ...data, targetFolderId: props.folder.id })
  } catch {
    // ignore
  }
}

function onDragEnd() {
  isDragOver.value = false
}

// Cleanup context menu on unmount
onUnmounted(() => {
  contextMenu.value = null
})
</script>

<style scoped>
.tree-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  cursor: pointer;
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  transition: all 0.15s;
  user-select: none;
}

.tree-item:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.tree-item.selected {
  background: rgba(124, 58, 237, 0.15);
  color: var(--accent);
  font-weight: 600;
}

.tree-item.drop-target {
  background: rgba(124, 58, 237, 0.25);
  outline: 2px dashed var(--accent);
}

.tree-arrow {
  font-size: 10px;
  width: 14px;
  text-align: center;
  flex-shrink: 0;
  cursor: pointer;
}

.tree-arrow-spacer {
  width: 14px;
  flex-shrink: 0;
}

.tree-icon {
  font-size: 14px;
  flex-shrink: 0;
}

.folder-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.folder-count {
  font-size: 11px;
  background: var(--bg-secondary);
  padding: 1px 6px;
  border-radius: 10px;
  color: var(--text-secondary);
}

.article-item {
  font-size: 12px;
  opacity: 0.8;
}

.article-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Context Menu */
.context-menu {
  position: fixed;
  background: var(--bg-card);
  border: 1px solid var(--bg-secondary);
  border-radius: 8px;
  padding: 4px;
  z-index: 1000;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  min-width: 140px;
}

.context-item {
  padding: 6px 12px;
  font-size: 13px;
  cursor: pointer;
  border-radius: 4px;
  color: var(--text-primary);
}

.context-item:hover {
  background: var(--bg-secondary);
}

.context-item.danger {
  color: #ef4444;
}

.context-item.danger:hover {
  background: rgba(239, 68, 68, 0.15);
}

.context-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 999;
}
</style>
