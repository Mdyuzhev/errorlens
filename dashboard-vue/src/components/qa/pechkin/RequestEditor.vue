<template>
  <div class="request-editor">
    <!-- URL bar -->
    <div class="url-bar">
      <select v-model="req.method" class="method-select" :class="methodClass">
        <option v-for="m in methods" :key="m" :value="m">{{ m }}</option>
      </select>
      <input v-model="req.url" class="url-input" placeholder="https://api.example.com/path" @keydown.enter="send" />
      <button class="send-btn" :disabled="store.executing" @click="send">
        {{ store.executing ? 'Sending...' : 'Send' }}
      </button>
    </div>

    <!-- Tabs -->
    <div class="editor-tabs">
      <button v-for="t in tabs" :key="t" class="editor-tab" :class="{ active: activeTab === t }" @click="activeTab = t">
        {{ t }}
      </button>
    </div>

    <!-- Params -->
    <div v-show="activeTab === 'Params'" class="tab-content">
      <KvTable v-model="params" label="Query Parameters" @update:model-value="syncParamsToUrl" />
    </div>

    <!-- Headers -->
    <div v-show="activeTab === 'Headers'" class="tab-content">
      <div class="quick-headers">
        <button v-for="h in quickHeaders" :key="h" class="quick-btn" @click="addHeader(h)">+ {{ h }}</button>
      </div>
      <KvTable v-model="headers" label="Headers" />
    </div>

    <!-- Body -->
    <div v-show="activeTab === 'Body'" class="tab-content">
      <div class="body-type-bar">
        <label v-for="bt in bodyTypes" :key="bt.value" class="body-radio">
          <input type="radio" v-model="req.body_type" :value="bt.value" />
          <span>{{ bt.label }}</span>
        </label>
      </div>
      <div v-if="req.body_type === 'raw'" class="body-raw">
        <div class="body-toolbar">
          <button class="rv-toggle" @click="prettyBody">Pretty</button>
        </div>
        <textarea v-model="req.body" class="body-textarea" placeholder='{"key": "value"}' />
      </div>
      <div v-else-if="req.body_type === 'form-data' || req.body_type === 'x-www-form-urlencoded'" class="body-form">
        <KvTable v-model="bodyKv" label="Form Fields" />
      </div>
      <div v-else class="body-none">
        <p class="body-none-text">This request does not have a body</p>
      </div>
    </div>

    <!-- Auth -->
    <div v-show="activeTab === 'Auth'" class="tab-content">
      <AuthEditor v-model="req.auth" />
    </div>

    <!-- Pre-request -->
    <div v-show="activeTab === 'Pre-request'" class="tab-content">
      <div class="script-toolbar">
        <span class="script-lang-label">Python</span>
        <div class="snippet-btns">
          <button class="snippet-btn" @click="insertSnippet('pre', 'setauth')">Set Bearer</button>
          <button class="snippet-btn" @click="insertSnippet('pre', 'log')">Log request</button>
          <button class="snippet-btn" @click="insertSnippet('pre', 'setheader')">Set header</button>
        </div>
      </div>
      <div class="script-editor-wrap" :data-line-count="preLineCount">
        <div class="line-numbers" aria-hidden="true">
          <span v-for="n in preLineCount" :key="n">{{ n }}</span>
        </div>
        <textarea
          ref="preScriptEl"
          v-model="req.pre_request_script"
          class="script-textarea with-lines"
          placeholder="# Pre-request script runs before sending
# Example: set_header('X-Custom', 'value')"
          spellcheck="false"
          @input="onPreScriptChange"
          @keydown.tab.prevent="insertTab($event)"
        />
      </div>
    </div>

    <!-- Tests -->
    <div v-show="activeTab === 'Tests'" class="tab-content">
      <div class="script-toolbar">
        <span class="script-lang-label">Python</span>
        <div class="snippet-btns">
          <button class="snippet-btn" @click="insertSnippet('tests', 'status200')">Status 200</button>
          <button class="snippet-btn" @click="insertSnippet('tests', 'hasbody')">Has body</button>
          <button class="snippet-btn" @click="insertSnippet('tests', 'jsonparse')">Parse JSON</button>
          <button class="snippet-btn" @click="insertSnippet('tests', 'hasfield')">Has field</button>
        </div>
      </div>
      <div class="script-editor-wrap" :data-line-count="testLineCount">
        <div class="line-numbers" aria-hidden="true">
          <span v-for="n in testLineCount" :key="n">{{ n }}</span>
        </div>
        <textarea
          ref="testScriptEl"
          v-model="req.test_script"
          class="script-textarea with-lines"
          placeholder="# Write test assertions here
# Example: test(response['status_code'] == 200, 'Status OK')"
          spellcheck="false"
          @input="onTestScriptChange"
          @keydown.tab.prevent="insertTab($event)"
          @scroll="syncScroll($event, 'test')"
        />
      </div>
    </div>

    <!-- Code -->
    <div v-show="activeTab === 'Code'" class="tab-content">
      <div class="code-gen">
        <div class="code-lang-bar">
          <button v-for="l in codeLangs" :key="l" class="code-lang-btn" :class="{ active: codeLang === l }" @click="codeLang = l">
            {{ l }}
          </button>
        </div>
        <div class="code-output-wrap">
          <button class="copy-snippet-btn" @click="copySnippet">{{ snippetCopied ? 'Copied!' : 'Copy' }}</button>
          <pre class="code-output"><code>{{ generatedCode }}</code></pre>
        </div>
      </div>
    </div>

    <!-- Settings -->
    <div v-show="activeTab === 'Settings'" class="tab-content">
      <SettingsEditor
        v-model="req.settings"
        @update:model-value="onSettingsChange"
      />
    </div>

    <!-- Auto-save on blur -->
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { usePechkinStore } from '@/stores/pechkin'
import AuthEditor from './AuthEditor.vue'
import SettingsEditor from './SettingsEditor.vue'

const store = usePechkinStore()
const methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
const tabs = ['Params', 'Headers', 'Body', 'Auth', 'Pre-request', 'Tests', 'Code', 'Settings']
const activeTab = ref('Params')
const quickHeaders = ['Content-Type', 'Authorization', 'Accept', 'X-API-Key']
const bodyTypes = [
  { value: 'none', label: 'none' },
  { value: 'raw', label: 'raw' },
  { value: 'form-data', label: 'form-data' },
  { value: 'x-www-form-urlencoded', label: 'x-www-form-urlencoded' },
]
const codeLangs = ['cURL', 'Python', 'JavaScript']
const codeLang = ref('cURL')
const snippetCopied = ref(false)
const testScriptEl = ref(null)
const preScriptEl = ref(null)

const req = reactive({
  method: 'GET', url: '', headers: {}, body: '', body_type: 'none',
  auth: { type: 'none' }, pre_request_script: '', test_script: '', settings: {},
})
const params = ref([])
const headers = ref([])
const bodyKv = ref([])

const methodClass = computed(() => {
  const m = req.method?.toUpperCase()
  const map = { GET: 'sel-get', POST: 'sel-post', PUT: 'sel-put', PATCH: 'sel-patch', DELETE: 'sel-delete' }
  return map[m] || ''
})

// Sync active request to local state
watch(() => store.activeRequest, (r) => {
  if (!r) return
  req.method = r.method || 'GET'
  req.url = r.url || ''
  req.body = typeof r.body === 'string' ? r.body : (r.body ? JSON.stringify(r.body) : '')
  req.body_type = r.body_type || 'none'
  req.auth = r.auth || { type: 'none' }
  req.pre_request_script = r.pre_request_script || ''
  req.test_script = r.test_script || ''
  req.settings = r.settings || {}
  // Parse headers
  headers.value = Object.entries(r.headers || {}).map(([k, v]) => ({ key: k, value: v, enabled: true }))
  // Parse URL params
  parseUrlParams()
}, { immediate: true })

const testLineCount = computed(() => {
  const lines = (req.test_script || '').split('\n').length
  return Math.max(lines, 10)
})

const preLineCount = computed(() => {
  const lines = (req.pre_request_script || '').split('\n').length
  return Math.max(lines, 10)
})

// Snippets library
const SNIPPETS = {
  tests: {
    status200: `test(response['status_code'] == 200, "Status 200 OK")\n`,
    hasbody: `test(len(response['body']) > 0, "Response has body")\n`,
    jsonparse: `import json\ndata = json.loads(response['body'])\ntest(isinstance(data, (dict, list)), "Body is valid JSON")\n`,
    hasfield: `import json\ndata = json.loads(response['body'])\ntest('id' in data, "Response has 'id' field")\n`,
  },
  pre: {
    setauth: `set_header('Authorization', 'Bearer ' + env.get('token', ''))\n`,
    log: `log('Sending', request['method'], request['url'])\n`,
    setheader: `set_header('X-Custom-Header', 'value')\n`,
  }
}

function insertSnippet(type, key) {
  const code = SNIPPETS[type]?.[key]
  if (!code) return
  if (type === 'tests') {
    req.test_script = (req.test_script || '') + code
  } else {
    req.pre_request_script = (req.pre_request_script || '') + code
  }
}

function insertTab(e) {
  const ta = e.target
  const start = ta.selectionStart
  const end = ta.selectionEnd
  const value = ta.value
  ta.value = value.substring(0, start) + '    ' + value.substring(end)
  ta.selectionStart = ta.selectionEnd = start + 4
  ta.dispatchEvent(new Event('input'))
}

function syncScroll(e) {
  const wrap = e.target.closest('.script-editor-wrap')
  if (wrap) {
    const lineNums = wrap.querySelector('.line-numbers')
    if (lineNums) lineNums.scrollTop = e.target.scrollTop
  }
}

// Auto-save
let testSaveTimer = null
let preSaveTimer = null

function onTestScriptChange() {
  clearTimeout(testSaveTimer)
  testSaveTimer = setTimeout(() => {
    if (store.activeRequestId) {
      store.updateRequest(store.activeRequestId, { test_script: req.test_script })
    }
  }, 800)
}

function onPreScriptChange() {
  clearTimeout(preSaveTimer)
  preSaveTimer = setTimeout(() => {
    if (store.activeRequestId) {
      store.updateRequest(store.activeRequestId, { pre_request_script: req.pre_request_script })
    }
  }, 800)
}

let settingsSaveTimer = null
function onSettingsChange(newSettings) {
  req.settings = newSettings
  clearTimeout(settingsSaveTimer)
  settingsSaveTimer = setTimeout(() => {
    if (store.activeRequestId) {
      store.updateRequest(store.activeRequestId, { settings: req.settings })
    }
  }, 500)
}

function parseUrlParams() {
  try {
    const url = new URL(req.url)
    params.value = Array.from(url.searchParams.entries()).map(([k, v]) => ({ key: k, value: v, enabled: true }))
  } catch (e) {
    params.value = []
  }
}

function syncParamsToUrl() {
  try {
    const raw = req.url || 'https://example.com'
    const tplMatch = raw.match(/^(\{\{[^}]+\}\})(.*)$/)
    const prefix = tplMatch ? tplMatch[1] : ''
    const parseable = tplMatch ? 'https://placeholder.local' + tplMatch[2] : raw
    const url = new URL(parseable)
    url.search = ''
    params.value.filter(p => p.enabled && p.key).forEach(p => url.searchParams.append(p.key, p.value))
    if (tplMatch) {
      req.url = prefix + url.pathname + url.search
    } else {
      req.url = url.toString()
    }
  } catch (e) {
    // invalid URL, skip
  }
}

function addHeader(name) {
  headers.value.push({ key: name, value: '', enabled: true })
}

function prettyBody() {
  try {
    req.body = JSON.stringify(JSON.parse(req.body), null, 2)
  } catch (e) {
    // not JSON
  }
}

async function send() {
  // Collect headers
  const h = {}
  headers.value.filter(x => x.enabled && x.key).forEach(x => { h[x.key] = x.value })
  req.headers = h

  // Collect body for form types
  if (req.body_type === 'x-www-form-urlencoded') {
    const sp = new URLSearchParams()
    bodyKv.value.filter(x => x.enabled && x.key).forEach(x => { sp.append(x.key, x.value) })
    req.body = sp.toString()
    h['Content-Type'] = 'application/x-www-form-urlencoded'
  } else if (req.body_type === 'form-data') {
    const obj = {}
    bodyKv.value.filter(x => x.enabled && x.key).forEach(x => { obj[x.key] = x.value })
    req.body = JSON.stringify(obj)
    h['Content-Type'] = 'multipart/form-data'
  }

  // Update store request
  if (store.activeRequestId) {
    await store.updateRequest(store.activeRequestId, {
      method: req.method, url: req.url, headers: h,
      body: req.body, body_type: req.body_type, auth: req.auth,
      pre_request_script: req.pre_request_script, test_script: req.test_script,
      settings: req.settings,
    })
  }
  store.$patch({
    activeRequest: { ...store.activeRequest, ...req }
  })
  await store.execute()
}

function jsonToPythonLiteral(str) {
  try {
    const obj = JSON.parse(str)
    return formatPyValue(obj)
  } catch (e) {
    return str
  }
}

function formatPyValue(val) {
  if (val === null) return 'None'
  if (val === true) return 'True'
  if (val === false) return 'False'
  if (typeof val === 'number') return String(val)
  if (typeof val === 'string') return "'" + val.replace(/\\/g, '\\\\').replace(/'/g, "\\'") + "'"
  if (Array.isArray(val)) return '[' + val.map(formatPyValue).join(', ') + ']'
  if (typeof val === 'object') {
    const entries = Object.entries(val).map(([k, v]) => formatPyValue(k) + ': ' + formatPyValue(v))
    return '{' + entries.join(', ') + '}'
  }
  return String(val)
}

const generatedCode = computed(() => {
  const m = req.method
  const u = req.url || 'https://example.com'
  const h = headers.value.filter(x => x.enabled && x.key)
  const hasBody = req.body_type !== 'none' && req.body

  if (codeLang.value === 'cURL') {
    let cmd = `curl -X ${m} '${u}'`
    h.forEach(x => { cmd += ` \\\n  -H '${x.key}: ${x.value}'` })
    if (hasBody) cmd += ` \\\n  -d '${req.body}'`
    return cmd
  }
  if (codeLang.value === 'Python') {
    let s = 'import requests\n\n'
    s += `resp = requests.${m.toLowerCase()}(\n    '${u}'`
    if (h.length) {
      s += ',\n    headers={'
      s += h.map(x => `\n        '${x.key}': '${x.value}'`).join(',')
      s += '\n    }'
    }
    if (hasBody) s += `,\n    json=${jsonToPythonLiteral(req.body)}`
    s += '\n)\nprint(resp.status_code, resp.json())'
    return s
  }
  if (codeLang.value === 'JavaScript') {
    let s = `const resp = await fetch('${u}', {\n  method: '${m}'`
    if (h.length) {
      s += ',\n  headers: {'
      s += h.map(x => `\n    '${x.key}': '${x.value}'`).join(',')
      s += '\n  }'
    }
    if (hasBody) s += `,\n  body: '${req.body}'`
    s += '\n})\nconst data = await resp.json()\nconsole.log(data)'
    return s
  }
  return ''
})

function copySnippet() {
  navigator.clipboard.writeText(generatedCode.value)
  snippetCopied.value = true
  setTimeout(() => { snippetCopied.value = false }, 2000)
}

// KvTable sub-component (inline)
</script>

<!-- KvTable as a child component defined inline via functional approach -->
<script>
import { h, defineComponent } from 'vue'

const KvTable = defineComponent({
  name: 'KvTable',
  props: {
    modelValue: { type: Array, default: () => [] },
    label: { type: String, default: '' },
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    function update(idx, field, val) {
      const copy = props.modelValue.map(x => ({ ...x }))
      copy[idx][field] = val
      emit('update:modelValue', copy)
    }
    function toggleEnabled(idx) {
      const copy = props.modelValue.map(x => ({ ...x }))
      copy[idx].enabled = !copy[idx].enabled
      emit('update:modelValue', copy)
    }
    function addRow() {
      emit('update:modelValue', [...props.modelValue, { key: '', value: '', enabled: true }])
    }
    function removeRow(idx) {
      emit('update:modelValue', props.modelValue.filter((_, i) => i !== idx))
    }
    return () => h('div', { class: 'kv-table' }, [
      h('table', { class: 'kv-inner' }, [
        h('thead', [h('tr', [
          h('th', { style: 'width:28px' }, ''),
          h('th', 'Key'),
          h('th', 'Value'),
          h('th', { style: 'width:28px' }, ''),
        ])]),
        h('tbody', props.modelValue.map((row, i) =>
          h('tr', { key: i, class: row.enabled ? '' : 'kv-disabled' }, [
            h('td', [h('input', {
              type: 'checkbox', checked: row.enabled,
              onChange: () => toggleEnabled(i),
            })]),
            h('td', [h('input', {
              class: 'kv-input', value: row.key, placeholder: 'key',
              onInput: (e) => update(i, 'key', e.target.value),
            })]),
            h('td', [h('input', {
              class: 'kv-input', value: row.value, placeholder: 'value',
              onInput: (e) => update(i, 'value', e.target.value),
            })]),
            h('td', [h('button', {
              class: 'kv-remove', onClick: () => removeRow(i),
            }, '\u00D7')]),
          ])
        )),
      ]),
      h('button', { class: 'kv-add', onClick: addRow }, '+ Add'),
    ])
  }
})

export default { components: { KvTable } }
</script>

<style scoped>
.request-editor {
  background: var(--bg-card);
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

/* URL bar */
.url-bar { display: flex; gap: 0; padding: 12px 14px; border-bottom: 1px solid var(--border-color); }
.method-select {
  padding: 8px 10px; background: var(--bg-secondary); border: 1px solid var(--border-color);
  border-radius: 6px 0 0 6px; color: var(--text-primary); font-size: 13px; font-weight: 700;
  outline: none; min-width: 90px;
}
.sel-get { color: var(--success); }
.sel-post { color: var(--accent); }
.sel-put, .sel-patch { color: var(--warning); }
.sel-delete { color: var(--error); }
.url-input {
  flex: 1; padding: 8px 12px; background: var(--bg-secondary); border: 1px solid var(--border-color);
  border-left: none; color: var(--text-primary); font-size: 13px; outline: none; font-family: monospace;
}
.url-input:focus { border-color: var(--accent); }
.send-btn {
  padding: 8px 20px; background: var(--accent); border: none; border-radius: 0 6px 6px 0;
  color: white; font-size: 13px; font-weight: 600; cursor: pointer; white-space: nowrap;
}
.send-btn:hover { background: var(--accent-hover); }
.send-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Tabs */
.editor-tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border-color); overflow-x: auto; }
.editor-tab {
  padding: 8px 14px; background: none; border: none; border-bottom: 2px solid transparent;
  color: var(--text-secondary); font-size: 12px; cursor: pointer; font-weight: 500; white-space: nowrap;
}
.editor-tab:hover { color: var(--text-primary); }
.editor-tab.active { color: var(--accent); border-bottom-color: var(--accent); }

.tab-content { flex: 1; overflow: auto; padding: 12px 14px; }

/* Quick headers */
.quick-headers { display: flex; gap: 6px; margin-bottom: 10px; flex-wrap: wrap; }
.quick-btn {
  padding: 3px 10px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
}
.quick-btn:hover { color: var(--accent); border-color: var(--accent); }

/* Body */
.body-type-bar { display: flex; gap: 14px; margin-bottom: 12px; }
.body-radio {
  display: flex; align-items: center; gap: 4px;
  font-size: 12px; color: var(--text-secondary); cursor: pointer;
}
.body-radio input { accent-color: var(--accent); }
.body-raw { display: flex; flex-direction: column; gap: 8px; flex: 1; }
.body-toolbar { display: flex; gap: 6px; }
.body-textarea, .script-textarea {
  flex: 1; min-height: 200px; padding: 12px;
  background: var(--bg-primary); border: 1px solid var(--border-color);
  border-radius: 6px; color: var(--text-primary);
  font-family: monospace; font-size: 12px; line-height: 1.5;
  resize: vertical; outline: none;
}
.body-textarea:focus, .script-textarea:focus { border-color: var(--accent); }
.body-none { padding: 40px; text-align: center; }
.body-none-text { color: var(--text-secondary); font-size: 13px; }

/* Code gen */
.code-gen { display: flex; flex-direction: column; gap: 10px; }
.code-lang-bar { display: flex; gap: 6px; }
.code-lang-btn {
  padding: 5px 14px; background: var(--bg-tertiary); border: 1px solid var(--border-color);
  border-radius: 6px; color: var(--text-secondary); font-size: 12px; cursor: pointer;
}
.code-lang-btn:hover { color: var(--text-primary); }
.code-lang-btn.active { background: var(--accent-subtle); color: var(--accent); border-color: var(--accent); }
.code-output-wrap { position: relative; }
.copy-snippet-btn {
  position: absolute; top: 8px; right: 8px; z-index: 2; padding: 3px 10px;
  background: var(--bg-tertiary); border: 1px solid var(--border-color);
  border-radius: 4px; color: var(--text-secondary); font-size: 11px; cursor: pointer;
}
.copy-snippet-btn:hover { color: var(--text-primary); }
.code-output {
  margin: 0; padding: 14px; background: var(--bg-primary); border: 1px solid var(--border-color);
  border-radius: 6px; color: var(--text-primary); font-family: monospace; font-size: 12px;
  line-height: 1.5; overflow-x: auto; white-space: pre; max-height: 400px; overflow-y: auto;
}

/* KV Table */
:deep(.kv-table) { width: 100%; }
:deep(.kv-inner) { width: 100%; border-collapse: collapse; font-size: 12px; }
:deep(.kv-inner th) {
  text-align: left; padding: 5px 6px; color: var(--text-secondary);
  border-bottom: 1px solid var(--border-color); font-weight: 500; font-size: 11px;
}
:deep(.kv-inner td) { padding: 3px 6px; border-bottom: 1px solid var(--border-color); }
:deep(.kv-input) {
  width: 100%; padding: 4px 8px; background: var(--bg-secondary);
  border: 1px solid var(--border-color); border-radius: 4px;
  color: var(--text-primary); font-size: 12px; outline: none; font-family: monospace;
}
:deep(.kv-input:focus) { border-color: var(--accent); }
:deep(.kv-disabled) { opacity: 0.4; }
:deep(.kv-remove) {
  background: none; border: none; color: var(--text-secondary);
  cursor: pointer; font-size: 16px; padding: 0 4px;
}
:deep(.kv-remove:hover) { color: var(--error); }
:deep(.kv-add) {
  margin-top: 6px; padding: 4px 12px; background: var(--bg-tertiary);
  border: 1px solid var(--border-color); border-radius: 4px;
  color: var(--text-secondary); font-size: 11px; cursor: pointer;
}
:deep(.kv-add:hover) { color: var(--accent); border-color: var(--accent); }

.rv-toggle {
  padding: 3px 10px; background: var(--bg-tertiary); border: 1px solid var(--border-color);
  border-radius: 4px; color: var(--text-secondary); font-size: 11px; cursor: pointer;
}
.rv-toggle:hover { color: var(--text-primary); }

/* Script editor */
.script-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 0 8px;
  flex-wrap: wrap;
}

.script-lang-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: var(--bg-tertiary);
  padding: 2px 8px;
  border-radius: 4px;
}

.snippet-btns {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.snippet-btn {
  padding: 3px 8px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--accent);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.12s;
  white-space: nowrap;
}
.snippet-btn:hover {
  background: var(--accent-muted);
  border-color: var(--accent);
}

.script-editor-wrap {
  display: flex;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  overflow: hidden;
  min-height: 200px;
  max-height: 400px;
  background: var(--bg-primary);
}

.line-numbers {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  padding: 12px 8px 12px 4px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  user-select: none;
  overflow: hidden;
  min-width: 32px;
}

.line-numbers span {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary);
  opacity: 0.5;
}

.script-textarea.with-lines {
  flex: 1;
  border: none;
  border-radius: 0;
  min-height: 200px;
  max-height: 400px;
  padding: 12px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: none;
  outline: none;
  overflow-y: auto;
  white-space: pre;
  tab-size: 4;
}
.script-textarea.with-lines:focus {
  box-shadow: none;
}
.script-editor-wrap:focus-within {
  border-color: var(--accent);
}
</style>
