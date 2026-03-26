<template>
  <div class="code-block-wrapper">
    <div class="code-block-header">
      <select
        v-if="!readonly"
        class="code-lang-select"
        :value="language"
        @change="$emit('update:language', $event.target.value)"
      >
        <option v-for="lang in LANGUAGES" :key="lang" :value="lang">{{ lang }}</option>
      </select>
      <span v-else class="code-lang-badge">{{ language }}</span>
      <button class="code-copy-btn" title="Копировать" @click="copyCode">
        {{ copied ? 'Скопировано!' : 'Копировать' }}
      </button>
    </div>

    <div v-if="readonly" class="code-block-body">
      <pre class="code-pre"><code ref="codeRef" :class="`language-${language}`">{{ code }}</code></pre>
    </div>
    <div v-else class="code-block-body">
      <textarea
        class="code-textarea"
        :value="code"
        @input="$emit('update:code', $event.target.value)"
        placeholder="// Вставьте код..."
        spellcheck="false"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'

const props = defineProps({
  language: { type: String, default: 'javascript' },
  code: { type: String, default: '' },
  readonly: { type: Boolean, default: false }
})

defineEmits(['update:language', 'update:code'])

const LANGUAGES = [
  'javascript', 'python', 'bash', 'sql', 'typescript',
  'json', 'yaml', 'go', 'rust'
]

const codeRef = ref(null)
const copied = ref(false)
let hljsLoaded = null

function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve()
      return
    }
    const script = document.createElement('script')
    script.src = src
    script.onload = resolve
    script.onerror = reject
    document.head.appendChild(script)
  })
}

function loadStylesheet(href) {
  if (document.querySelector(`link[href="${href}"]`)) return
  const link = document.createElement('link')
  link.rel = 'stylesheet'
  link.href = href
  document.head.appendChild(link)
}

async function loadHljs() {
  if (window.hljs) return window.hljs
  if (!hljsLoaded) {
    hljsLoaded = loadScript(
      'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js'
    )
    loadStylesheet(
      'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css'
    )
  }
  await hljsLoaded
  return window.hljs
}

async function highlight() {
  if (!props.readonly || !codeRef.value) return
  try {
    const hljs = await loadHljs()
    if (codeRef.value) {
      codeRef.value.removeAttribute('data-highlighted')
      hljs.highlightElement(codeRef.value)
    }
  } catch (err) {
    console.warn('[CodeBlock] highlight.js load failed:', err.message)
  }
}

onMounted(() => {
  if (props.readonly) highlight()
})

watch(() => [props.code, props.language, props.readonly], async () => {
  if (props.readonly) {
    await nextTick()
    highlight()
  }
})

async function copyCode() {
  try {
    await navigator.clipboard.writeText(props.code)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch (err) {
    console.warn('[CodeBlock] Copy failed:', err.message)
  }
}
</script>

<style scoped>
.code-block-wrapper {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.code-block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.code-lang-select {
  background: var(--bg-primary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  outline: none;
  cursor: pointer;
}

.code-lang-select:focus {
  border-color: var(--accent);
}

.code-lang-badge {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.code-copy-btn {
  background: var(--bg-tertiary, var(--bg-primary));
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.code-copy-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.code-block-body {
  background: var(--bg-primary);
}

.code-pre {
  margin: 0;
  padding: 16px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.5;
}

.code-pre code {
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  color: var(--text-primary);
}

.code-textarea {
  width: 100%;
  min-height: 120px;
  padding: 16px;
  border: none;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.5;
  resize: vertical;
  outline: none;
  tab-size: 2;
}

.code-textarea::placeholder {
  color: var(--placeholder-color, var(--text-secondary));
}
</style>
