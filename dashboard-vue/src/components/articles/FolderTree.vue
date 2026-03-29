<template>
  <div class="folder-tree">
    <div
      class="tree-item root-item"
      :class="{ selected: !selectedFolderId }"
      @click="$emit('select', null)"
      @dragover.prevent="onDragOver($event, null)"
      @dragleave="onDragLeave"
      @drop="onDrop($event, null)"
    >
      <span class="tree-icon"><AppIcon name="file" :size="14" /></span>
      <span>All Articles</span>
    </div>

    <button class="btn-new-folder" @click="promptNewFolder(null)">
      + New Folder
    </button>

    <FolderNode
      v-for="folder in folders"
      :key="folder.id"
      :folder="folder"
      :depth="0"
      :expanded="expandedIds.has(folder.id)"
      :selected="selectedFolderId === folder.id"
      :expanded-ids="expandedIds"
      :selected-folder-id="selectedFolderId"
      @select="$emit('select', $event)"
      @toggle="$emit('toggle', $event)"
      @create="promptNewFolder"
      @rename="promptRename"
      @delete="$emit('delete', $event)"
      @drop="handleDrop"
    />

    <!-- Inline input for new folder -->
    <div v-if="showInput" class="folder-input-wrap" :style="{ paddingLeft: (inputDepth * 16 + 12) + 'px' }">
      <input
        ref="folderInput"
        v-model="inputName"
        class="folder-input"
        :placeholder="renaming ? 'Rename folder' : 'Folder name'"
        @keydown.enter="submitInput"
        @keydown.escape="cancelInput"
        @blur="submitInput"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import FolderNode from './FolderNode.vue'
import AppIcon from '@/components/common/AppIcon.vue'

const props = defineProps({
  folders: { type: Array, default: () => [] },
  selectedFolderId: { type: String, default: null },
  expandedIds: { type: Set, default: () => new Set() },
})

const emit = defineEmits(['select', 'toggle', 'create', 'rename', 'delete', 'drop'])

const showInput = ref(false)
const inputName = ref('')
const inputParentId = ref(null)
const inputDepth = ref(0)
const renaming = ref(false)
const renamingId = ref(null)
const folderInput = ref(null)

function promptNewFolder(parentId) {
  renaming.value = false
  renamingId.value = null
  inputParentId.value = parentId
  inputDepth.value = parentId ? getDepth(parentId) : 0
  inputName.value = ''
  showInput.value = true
  nextTick(() => folderInput.value?.focus())
}

function promptRename({ id, name }) {
  renaming.value = true
  renamingId.value = id
  inputName.value = name
  inputDepth.value = 0
  showInput.value = true
  nextTick(() => {
    folderInput.value?.focus()
    folderInput.value?.select()
  })
}

function submitInput() {
  const name = inputName.value.trim()
  if (!name) {
    cancelInput()
    return
  }
  if (renaming.value && renamingId.value) {
    emit('rename', { id: renamingId.value, name })
  } else {
    emit('create', { parentId: inputParentId.value, name })
  }
  cancelInput()
}

function cancelInput() {
  showInput.value = false
  inputName.value = ''
  renaming.value = false
  renamingId.value = null
}

function getDepth(folderId) {
  // Simple depth calc from tree
  function find(folders, depth) {
    for (const f of folders) {
      if (f.id === folderId) return depth + 1
      const d = find(f.children || [], depth + 1)
      if (d > 0) return d
    }
    return 0
  }
  return find(props.folders, 0)
}

function handleDrop(payload) {
  emit('drop', payload)
}

let dragOverTarget = null

function onDragOver(e, targetId) {
  e.dataTransfer.dropEffect = 'move'
  dragOverTarget = e.currentTarget
  e.currentTarget.classList.add('drop-target')
}

function onDragLeave(e) {
  e.currentTarget.classList.remove('drop-target')
}

function onDrop(e, targetFolderId) {
  e.currentTarget.classList.remove('drop-target')
  try {
    const data = JSON.parse(e.dataTransfer.getData('application/json'))
    emit('drop', { ...data, targetFolderId })
  } catch {
    // ignore
  }
}
</script>

<style scoped>
.folder-tree {
  padding: 8px 0;
}

.tree-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
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
  background: var(--accent-subtle);
  color: var(--accent);
  font-weight: 600;
}

.tree-item.drop-target {
  background: var(--accent-muted);
  outline: 2px dashed var(--accent);
}

.tree-icon {
  font-size: 14px;
  flex-shrink: 0;
}

.btn-new-folder {
  width: 100%;
  padding: 6px 12px;
  margin: 4px 0 8px;
  background: none;
  border: 1px dashed var(--text-secondary);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-new-folder:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-muted);
}

.folder-input-wrap {
  padding: 2px 12px;
}

.folder-input {
  width: 100%;
  padding: 4px 8px;
  background: var(--bg-secondary);
  border: 1px solid var(--accent);
  border-radius: 4px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
}
</style>
