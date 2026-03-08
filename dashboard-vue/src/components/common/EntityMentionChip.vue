<template>
  <NodeViewWrapper as="span" class="entity-mention-chip" :class="[chipClass]" @click="showPreview = !showPreview">
    <!-- Loading -->
    <span v-if="loading" class="chip-loading">
      <span class="chip-spinner"></span>
      {{ node.attrs.entityTitle || '...' }}
    </span>

    <!-- Error / deleted -->
    <span v-else-if="error" class="chip-deleted" :title="'Entity deleted or unavailable'">
      <s>{{ node.attrs.entityTitle || 'Unknown' }}</s>
    </span>

    <!-- Loaded -->
    <span v-else class="chip-content">
      <span class="chip-icon">{{ typeIcon }}</span>
      <span class="chip-title">{{ preview?.title || node.attrs.entityTitle }}</span>
      <span v-if="preview?.status" class="chip-status" :class="statusClass">
        {{ preview.status }}
      </span>
    </span>

    <!-- Preview popup -->
    <div v-if="showPreview && preview" class="chip-preview-popup" @click.stop>
      <div class="preview-header">
        <span class="chip-icon">{{ typeIcon }}</span>
        <strong>{{ preview.title }}</strong>
      </div>
      <div v-if="preview.status" class="preview-status">
        Status: <span :class="statusClass">{{ preview.status }}</span>
      </div>
      <div class="preview-type">Type: {{ typeLabel }}</div>
      <button class="btn-open" @click.stop="navigateToEntity">Open</button>
    </div>
  </NodeViewWrapper>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { NodeViewWrapper } from '@tiptap/vue-3'
import { useRouter } from 'vue-router'
import { entityLinksApi } from '@/services/api'

const router = useRouter()

const props = defineProps({
  node: { type: Object, required: true },
  updateAttributes: { type: Function, required: true },
})

const loading = ref(true)
const error = ref(false)
const preview = ref(null)
const showPreview = ref(false)

const typeIcons = { testcase: '\u{1F9EA}', task: '\u2705', article: '\u{1F4C4}' }
const typeLabels = { testcase: 'Test Case', task: 'Task', article: 'Article' }

const typeIcon = computed(() => typeIcons[props.node.attrs.entityType] || '\u{1F4C4}')
const typeLabel = computed(() => typeLabels[props.node.attrs.entityType] || 'Entity')

const chipClass = computed(() => `chip-type-${props.node.attrs.entityType || 'unknown'}`)

const statusClass = computed(() => {
  const s = (preview.value?.status || '').toLowerCase().replace(/\s+/g, '-')
  return `status-${s}`
})

async function fetchPreview() {
  const { entityType, entityId } = props.node.attrs
  if (!entityType || !entityId) {
    error.value = true
    loading.value = false
    return
  }

  try {
    const res = await entityLinksApi.getPreview(entityType, entityId)
    preview.value = res.data
    error.value = false
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

function navigateToEntity() {
  const { entityType, entityId } = props.node.attrs
  if (entityType === 'article') {
    const slug = preview.value?.slug || entityId
    router.push(`/articles/${slug}`)
  } else if (entityType === 'testcase') {
    router.push(`/testcases/${entityId}`)
  } else if (entityType === 'task') {
    router.push(`/tasks/${entityId}`)
  }
  showPreview.value = false
}

function handleClickOutside(e) {
  if (showPreview.value) showPreview.value = false
}

onMounted(() => {
  fetchPreview()
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.entity-mention-chip {
  display: inline-flex;
  align-items: center;
  position: relative;
  cursor: pointer;
  vertical-align: baseline;
}

.chip-content,
.chip-loading,
.chip-deleted {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.4;
  white-space: nowrap;
}

.chip-content {
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  border: 1px solid rgba(99, 102, 241, 0.3);
}

.chip-content:hover {
  background: rgba(99, 102, 241, 0.25);
}

.chip-loading {
  background: rgba(107, 114, 128, 0.15);
  color: #9ca3af;
}

.chip-deleted {
  background: rgba(239, 68, 68, 0.1);
  color: #f87171;
}

.chip-icon {
  font-size: 12px;
}

.chip-title {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chip-status {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
}

.chip-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-top-color: #9ca3af;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Status colors */
.status-draft { color: #f59e0b; }
.status-published { color: #10b981; }
.status-ready { color: #3b82f6; }
.status-approved { color: #10b981; }
.status-todo { color: #9ca3af; }
.status-in-progress, .status-in_progress { color: #3b82f6; }
.status-review { color: #f59e0b; }
.status-done { color: #10b981; }

/* Preview popup */
.chip-preview-popup {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 4px;
  background: var(--bg-card, #1e1e2e);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 12px;
  min-width: 220px;
  z-index: 1000;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}

.preview-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  font-size: 14px;
}

.preview-status,
.preview-type {
  font-size: 12px;
  color: var(--text-secondary, #9ca3af);
  margin-bottom: 4px;
}

.btn-open {
  margin-top: 8px;
  width: 100%;
  padding: 6px 12px;
  background: var(--accent, #6366f1);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

.btn-open:hover {
  opacity: 0.9;
}
</style>
