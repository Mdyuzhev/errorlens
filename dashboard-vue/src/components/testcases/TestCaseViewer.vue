<template>
  <div class="tc-viewer">
    <div class="viewer-header">
      <button class="btn-back" @click="$emit('close')">← Назад</button>
      <span class="viewer-title">{{ testCase.title }}</span>
      <span v-if="testCase.human_id" class="human-id-badge">{{ testCase.human_id }}</span>
      <span class="viewer-badge priority" :class="testCase.priority?.toLowerCase()">{{ testCase.priority }}</span>
      <span class="viewer-badge status" :class="testCase.status?.toLowerCase()">{{ testCase.status }}</span>
      <button class="btn btn-primary btn-sm" @click="$emit('edit')">Edit</button>
    </div>

    <div class="viewer-body">
      <div class="viewer-document">
        <!-- Description -->
        <section v-if="descriptionJson" class="doc-section">
          <h2 class="doc-section-title">Description</h2>
          <RichEditor :modelValue="descriptionJson" :readonly="true" />
        </section>

        <!-- Steps -->
        <section v-if="testCase.steps?.length" class="doc-section">
          <h2 class="doc-section-title">Steps</h2>
          <table class="steps-table">
            <thead>
              <tr>
                <th class="step-num">#</th>
                <th>Action</th>
                <th>Expected Result</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(step, idx) in testCase.steps" :key="idx">
                <td class="step-num">{{ idx + 1 }}</td>
                <td>{{ stepText(step.action) }}</td>
                <td>{{ stepText(step.expected) }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <!-- Preconditions -->
        <section v-if="preconditionsJson" class="doc-section">
          <h2 class="doc-section-title">Preconditions</h2>
          <RichEditor :modelValue="preconditionsJson" :readonly="true" />
        </section>

        <!-- Postconditions -->
        <section v-if="postconditionsJson" class="doc-section">
          <h2 class="doc-section-title">Postconditions</h2>
          <RichEditor :modelValue="postconditionsJson" :readonly="true" />
        </section>

        <!-- Tags -->
        <section v-if="testCase.tags?.length" class="doc-section">
          <h2 class="doc-section-title">Tags</h2>
          <div class="tags-list">
            <span v-for="tag in testCase.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>
        </section>

        <!-- Backlinks -->
        <section v-if="backlinks.length" class="doc-section">
          <h2 class="doc-section-title">Mentioned in articles ({{ backlinks.length }})</h2>
          <div v-for="bl in backlinks" :key="bl.article_id" class="backlink-item" @click="goToArticle(bl)">
            <span class="backlink-icon">📄</span>
            {{ bl.article_title }}
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import RichEditor from '@/components/common/RichEditor.vue'

const props = defineProps({
  testCase: { type: Object, required: true },
  backlinks: { type: Array, default: () => [] }
})

defineEmits(['close', 'edit'])

function parseContent(raw) {
  if (!raw) return null
  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw
    if (parsed && parsed.type === 'doc') return parsed
  } catch {}
  return null
}

function stepText(val) {
  if (!val) return ''
  if (typeof val === 'string') {
    try {
      const parsed = JSON.parse(val)
      if (parsed?.type === 'doc') {
        return extractText(parsed)
      }
    } catch {}
    return val
  }
  return String(val)
}

function extractText(doc) {
  if (!doc?.content) return ''
  return doc.content.map(node => {
    if (node.type === 'text') return node.text || ''
    if (node.content) return extractText(node)
    return ''
  }).join(' ').trim()
}

function goToArticle(bl) {
  const slug = bl.article_slug || bl.article_id
  window.open(`${window.location.origin}${window.location.pathname}#/articles/${slug}`, '_blank')
}

const descriptionJson = computed(() => parseContent(props.testCase.description))
const preconditionsJson = computed(() => parseContent(props.testCase.preconditions))
const postconditionsJson = computed(() => parseContent(props.testCase.postconditions))
</script>

<style scoped>
.tc-viewer {
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

.human-id-badge {
  font-size: 11px;
  font-family: monospace;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  padding: 1px 6px;
  border-radius: 4px;
  flex-shrink: 0;
}

.viewer-badge {
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  flex-shrink: 0;
}

.viewer-badge.priority.critical { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
.viewer-badge.priority.high { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
.viewer-badge.priority.medium { background: rgba(59, 130, 246, 0.2); color: #3b82f6; }
.viewer-badge.priority.low { background: rgba(107, 114, 128, 0.2); color: #9ca3af; }

.viewer-badge.status.draft { background: rgba(107, 114, 128, 0.2); color: #9ca3af; }
.viewer-badge.status.ready { background: rgba(16, 185, 129, 0.2); color: #10b981; }
.viewer-badge.status.approved { background: rgba(124, 58, 237, 0.2); color: #a78bfa; }

.btn-sm {
  padding: 4px 12px !important;
  font-size: 13px !important;
}

.viewer-body {
  flex: 1;
  overflow-y: auto;
  background: var(--bg-secondary);
  padding: 40px 20px;
}

.viewer-document {
  background: var(--bg-card);
  max-width: 860px;
  margin: 0 auto;
  padding: 60px 80px;
  border-radius: 8px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
  min-height: calc(100vh - 180px);
}

.doc-section {
  margin-bottom: 32px;
}

.doc-section-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--bg-secondary);
  color: var(--text-primary);
}

.steps-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.steps-table th,
.steps-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--bg-secondary);
}

.steps-table th {
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  color: var(--text-secondary);
}

.step-num {
  width: 40px;
  text-align: center;
  color: var(--text-secondary);
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  background: var(--accent, #6366f1);
  color: white;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
}

.backlink-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.15s;
}

.backlink-item:hover {
  background: rgba(99, 102, 241, 0.1);
}

.backlink-icon {
  font-size: 16px;
}
</style>
