<template>
  <div class="code-preview">
    <div class="code-preview-header">
      <h3>{{ title }}</h3>
      <button
        v-if="code"
        @click="copyToClipboard"
        class="copy-btn"
        :class="{ copied: isCopied }"
      >
        {{ isCopied ? '✓' : '📋' }}
      </button>
    </div>
    <pre v-if="code" class="code-content"><code>{{ code }}</code></pre>
    <div v-else class="code-empty">Код не сгенерирован</div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  code: {
    type: String,
    default: ''
  }
})

const isCopied = ref(false)

const copyToClipboard = async () => {
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
  background: var(--bg-secondary);
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border-color);
}

.code-preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-color);
}

.code-preview-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.copy-btn {
  padding: 6px 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.copy-btn:hover {
  background: var(--bg-secondary);
  border-color: var(--primary-color);
}

.copy-btn.copied {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border-color: transparent;
}

.code-content {
  margin: 0;
  padding: 16px;
  overflow-x: auto;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
  background: var(--bg-secondary);
}

.code-content code {
  display: block;
  white-space: pre;
}

.code-empty {
  padding: 32px;
  text-align: center;
  color: var(--text-secondary);
  font-style: italic;
}

@media (max-width: 768px) {
  .code-content {
    font-size: 12px;
    padding: 12px;
  }
}
</style>
