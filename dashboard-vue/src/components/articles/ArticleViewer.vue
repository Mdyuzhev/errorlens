<template>
  <div class="article-viewer">
    <div class="viewer-header">
      <button class="btn-back" @click="$emit('close')">← Назад</button>
      <span class="viewer-title">{{ article.title }}</span>
      <span class="viewer-status" :class="article.status">{{ article.status }}</span>
      <button class="btn btn-primary btn-sm" @click="$emit('edit')">Edit</button>
    </div>

    <div v-if="article.category || articleTags.length" class="viewer-subheader">
      <span v-if="article.category" class="viewer-category">{{ article.category }}</span>
      <span v-for="tag in articleTags" :key="tag" class="viewer-tag">{{ tag }}</span>
    </div>

    <div class="viewer-body">
      <div class="viewer-content">
        <GridEditor
          :modelValue="gridContent"
          :readonly="true"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import GridEditor from './GridEditor.vue'

const props = defineProps({
  article: { type: Object, required: true }
})

defineEmits(['close', 'edit'])

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
  } catch {
    return { version: 'grid-1', rows: [] }
  }
})

const articleTags = computed(() => {
  return props.article.tags || []
})
</script>

<style scoped>
.article-viewer {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

.viewer-header {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 48px;
  padding: 0 16px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--bg-secondary);
  flex-shrink: 0;
}

.btn-back {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 14px;
  padding: 4px 8px;
  border-radius: 6px;
  white-space: nowrap;
}

.btn-back:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.viewer-title {
  flex: 1;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.viewer-status {
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  flex-shrink: 0;
}

.viewer-status.published {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.viewer-status.draft {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.btn-sm {
  padding: 4px 12px !important;
  font-size: 13px !important;
}

.viewer-subheader {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--bg-secondary);
  flex-shrink: 0;
}

.viewer-category {
  font-size: 13px;
  color: var(--accent, #6366f1);
  font-weight: 500;
}

.viewer-tag {
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  padding: 2px 8px;
  border-radius: 10px;
}

.viewer-body {
  flex: 1;
  overflow-y: auto;
}

.viewer-content {
  max-width: 860px;
  margin: 0 auto;
  padding: 40px 20px 80px;
}

.viewer-content :deep(.grid-editor) {
  height: auto;
}

.viewer-content :deep(.grid-body) {
  padding: 0;
  overflow: visible;
}

.viewer-content :deep(.grid-col) {
  background: none;
  border: none;
  padding: 0;
  min-height: auto;
}

.viewer-content :deep(.ProseMirror) {
  min-height: auto !important;
  border: none !important;
  padding: 0 !important;
  background: none !important;
}
</style>
