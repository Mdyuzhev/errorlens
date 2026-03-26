<template>
  <div class="attachments-block">
    <h4>Attachments</h4>

    <!-- Drop zone -->
    <div
      class="drop-zone"
      :class="{ dragging }"
      @dragover.prevent="dragging = true"
      @dragleave="dragging = false"
      @drop.prevent="handleDrop"
    >
      <span class="drop-hint">Drop files here or</span>
      <button class="btn-link" @click="$refs.fileInput.click()">browse</button>
      <input ref="fileInput" type="file" multiple hidden @change="handleFiles" />
    </div>

    <!-- File list -->
    <div v-if="attachments?.length" class="file-list">
      <div v-for="att in attachments" :key="att.id" class="file-item">
        <span class="file-name" :title="att.filename">{{ att.filename }}</span>
        <span class="file-size">{{ formatSize(att.size) }}</span>
        <button class="btn-delete" @click="removeFile(att.id)" title="Delete">&times;</button>
      </div>
    </div>
    <div v-else class="empty-hint">No attachments</div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useIssuesStore } from '@/stores/issues'

const props = defineProps({
  issueId: { type: String, required: true },
  attachments: { type: Array, default: () => [] },
})

const store = useIssuesStore()
const dragging = ref(false)

function formatSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

async function uploadFiles(files) {
  for (const file of files) {
    await store.uploadAttachment(props.issueId, file)
  }
}

function handleDrop(e) {
  dragging.value = false
  const files = e.dataTransfer?.files
  if (files?.length) uploadFiles(files)
}

function handleFiles(e) {
  const files = e.target?.files
  if (files?.length) uploadFiles(files)
  e.target.value = ''
}

async function removeFile(attId) {
  await store.deleteAttachment(props.issueId, attId)
}
</script>

<style scoped>
.attachments-block h4 {
  margin: 0 0 12px 0;
  font-size: 13px;
  text-transform: uppercase;
  color: var(--text-secondary);
  letter-spacing: 0.5px;
}

.drop-zone {
  border: 2px dashed var(--border-color);
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  transition: border-color 0.2s, background 0.2s;
}

.drop-zone.dragging {
  border-color: var(--accent);
  background: rgba(59, 130, 246, 0.05);
}

.drop-hint {
  font-size: 13px;
  color: var(--text-secondary);
}

.btn-link {
  background: none;
  border: none;
  color: var(--accent);
  cursor: pointer;
  font-size: 13px;
  text-decoration: underline;
}

.file-list {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: var(--bg-secondary);
  border-radius: 6px;
  font-size: 13px;
}

.file-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-primary);
}

.file-size {
  color: var(--text-secondary);
  font-size: 11px;
  flex-shrink: 0;
}

.btn-delete {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 16px;
  padding: 0 4px;
  line-height: 1;
}

.btn-delete:hover { color: #ef4444; }

.empty-hint {
  font-size: 12px;
  color: var(--text-secondary);
  font-style: italic;
  margin-top: 8px;
}
</style>
