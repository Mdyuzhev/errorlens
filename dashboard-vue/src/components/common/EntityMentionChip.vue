<template>
  <NodeViewWrapper as="span" class="entity-mention-chip" :class="[chipClass]" @click.stop="navigateToEntity">
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
      <span v-if="preview?.human_id" class="chip-human-id">{{ preview.human_id }}</span>
      <span class="chip-title">{{ preview?.title || node.attrs.entityTitle }}</span>
      <span v-if="preview?.status" class="chip-status" :class="statusClass">
        {{ preview.status }}
      </span>
    </span>
  </NodeViewWrapper>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { NodeViewWrapper } from '@tiptap/vue-3'
import { entityLinksApi } from '@/services/api'

const props = defineProps({
  node: { type: Object, required: true },
  updateAttributes: { type: Function, required: true },
})

const loading = ref(true)
const error = ref(false)
const preview = ref(null)

const typeIcons = { testcase: '\u{1F9EA}', task: '\u2705', article: '\u{1F4C4}' }
const typeIcon = computed(() => typeIcons[props.node.attrs.entityType] || '\u{1F4C4}')

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

function buildUrl(section, id) {
  return `${window.location.origin}${window.location.pathname}#/${section}/${id}`
}

function navigateToEntity() {
  if (loading.value || error.value) return
  const { entityType, entityId } = props.node.attrs
  if (entityType === 'article') {
    const slug = preview.value?.slug || entityId
    window.open(buildUrl('articles', slug), '_blank')
  } else if (entityType === 'testcase') {
    window.open(buildUrl('testcases', entityId), '_blank')
  } else if (entityType === 'task') {
    window.open(buildUrl('tasks', entityId), '_blank')
  }
}

onMounted(() => {
  fetchPreview()
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

.chip-human-id {
  font-size: 10px;
  font-family: monospace;
  opacity: 0.7;
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

</style>
