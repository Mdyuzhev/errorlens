<template>
  <div class="code-preview">
    <div class="preview-header">
      <span class="title">{{ title }}</span>
      <div class="header-actions">
        <button class="copy-btn" @click="copyToClipboard" :disabled="!code">
          {{ isCopied ? '✓ Скопировано' : '📋 Copy' }}
        </button>
      </div>
    </div>
    <div class="preview-body">
      <pre v-if="code" class="code-block"><code :class="`language-${language}`">{{ formattedCode }}</code></pre>
      <div v-else class="empty-preview">
        <div style="font-size:48px">📄</div>
        <p>Код появится после генерации</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: 'Generated Code'
  },
  code: {
    type: String,
    default: ''
  },
  language: {
    type: String,
    default: 'python',
    validator: (v) => ['python', 'java', 'javascript', 'json'].includes(v)
  }
})

const isCopied = ref(false)

const formattedCode = computed(() => {
  if (!props.code) return ''
  return props.code
    .split('\n')
    .map((line, i) => `${String(i + 1).padStart(4, ' ')} ${line}`)
    .join('\n')
})

async function copyToClipboard() {
  if (!props.code) return

  try {
    await navigator.clipboard.writeText(props.code)
    isCopied.value = true
    setTimeout(() => {
      isCopied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}
</script>

<style scoped>
.code-preview {
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  height: 100%;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.title {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.copy-btn {
  padding: 6px 12px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.copy-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(102, 126, 234, 0.05);
}

.copy-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.preview-body {
  flex: 1;
  overflow: auto;
  max-height: 600px;
}

.code-block {
  margin: 0;
  padding: 16px;
  background: var(--bg-card);
  overflow-x: auto;
}

.code-block code {
  display: block;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre;
}

.empty-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--text-secondary);
  text-align: center;
}

.empty-preview p {
  margin-top: 16px;
  font-size: 14px;
}

.preview-body::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.preview-body::-webkit-scrollbar-track {
  background: var(--bg-secondary);
}

.preview-body::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 4px;
}

.preview-body::-webkit-scrollbar-thumb:hover {
  background: var(--text-secondary);
}
</style>
