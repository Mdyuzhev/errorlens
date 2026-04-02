<template>
  <div class="tcv-overlay">
    <!-- Topbar -->
    <div class="tcv-topbar">
      <div class="tcv-topbar-left">
        <button class="btn-back" @click="$emit('close')">&larr; Back</button>
        <span class="tcv-human-id">{{ testCase?.human_id || '' }}</span>
      </div>
      <div class="tcv-topbar-right">
        <button
          class="btn-imp"
          :class="{ 'btn-imp--loading': impLoading }"
          :disabled="impLoading"
          @click="handleImprove"
          title="Improve with AI (Ollama)"
        >
          <span v-if="impLoading" class="imp-spinner"></span>
          {{ impLoading ? 'Improving...' : 'IMP' }}
        </button>
        <span v-if="impError" class="imp-error">{{ impError }}</span>
        <button class="btn-delete" @click="$emit('delete', testCase.id)">Delete</button>
        <button class="btn-cancel" @click="$emit('close')">Cancel</button>
        <button class="btn-save" @click="handleSave">Save</button>
      </div>
    </div>

    <!-- Body -->
    <div class="tcv-body">
      <!-- Left: tabs content -->
      <div class="tcv-left">
        <nav class="tcv-tabs">
          <button
            v-for="t in detailTabs"
            :key="t.key"
            class="tcv-tab"
            :class="{ active: activeDetailTab === t.key }"
            @click="activeDetailTab = t.key"
          >
            {{ t.label }}
          </button>
        </nav>

        <div class="tcv-tab-content">
          <!-- Details tab -->
          <div v-if="activeDetailTab === 'details'" class="tab-details">
            <label class="field-label">Title</label>
            <input v-model="form.title" class="field-input" placeholder="Test case title" />

            <label class="field-label">Description</label>
            <textarea
              v-model="form.description"
              class="field-textarea"
              placeholder="Description..."
              rows="4"
            />

            <label class="field-label">Preconditions</label>
            <textarea
              v-model="form.preconditions"
              class="field-textarea"
              placeholder="Preconditions..."
              rows="3"
            />

            <label class="field-label">Postconditions</label>
            <textarea
              v-model="form.postconditions"
              class="field-textarea"
              placeholder="Postconditions..."
              rows="3"
            />
          </div>

          <!-- Steps tab -->
          <div v-if="activeDetailTab === 'steps'" class="tab-steps">
            <StepsEditor v-model="form.steps" />
          </div>

          <!-- Parameters tab -->
          <div v-if="activeDetailTab === 'parameters'" class="tab-parameters">
            <div class="param-toolbar">
              <p class="param-hint">
                Параметры позволяют запускать тест-кейс с разными наборами данных.
                Каждый набор значений создаёт отдельную строку результата в прогоне.
              </p>
              <button class="btn-add-param" @click="addParameter">+ Add Parameter</button>
            </div>

            <table v-if="form.parameters.length" class="param-table">
              <thead>
                <tr>
                  <th class="col-param-key">Parameter Name</th>
                  <th class="col-param-values">Values (comma-separated)</th>
                  <th class="col-param-del"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(param, idx) in form.parameters" :key="param._id" class="param-row">
                  <td>
                    <input
                      v-model="param.key"
                      class="param-input"
                      placeholder="e.g. browser"
                    />
                  </td>
                  <td>
                    <input
                      v-model="param.values"
                      class="param-input"
                      placeholder="e.g. Chrome, Firefox, Safari"
                    />
                  </td>
                  <td>
                    <button class="param-del" @click="removeParameter(idx)">&times;</button>
                  </td>
                </tr>
              </tbody>
            </table>

            <div v-else class="param-empty">
              No parameters defined. Click "+ Add Parameter" to add one.
            </div>

            <div v-if="form.parameters.length" class="param-preview">
              <p class="param-preview-title">Preview: {{ paramCombinations }} combinations</p>
            </div>
          </div>

          <!-- Links tab -->
          <div v-if="activeDetailTab === 'links'" class="tab-links">
            <LinkSearch
              title="Issues"
              empty-text="No linked issues"
              placeholder="Find issue by ID or title..."
              :entity-types="['task']"
              :project-id="projectId"
              :items="issueItems"
              :exclude-ids="form.linked_issue_ids"
              @add="addIssue"
              @remove="removeIssue"
              @click-item="navigateToEntity"
            />
            <LinkSearch
              title="Articles"
              empty-text="No linked articles"
              placeholder="Find article by title..."
              :entity-types="['article']"
              :project-id="projectId"
              :items="articleItems"
              :exclude-ids="form.linked_article_ids"
              @add="addArticle"
              @remove="removeArticle"
              @click-item="navigateToEntity"
            />
          </div>
        </div>
      </div>

      <!-- Right sidebar -->
      <aside class="tcv-sidebar">
        <div class="sidebar-field">
          <label class="sidebar-label">Status</label>
          <select v-model="form.status" class="sidebar-select">
            <option value="draft">Draft</option>
            <option value="ready">Ready</option>
            <option value="approved">Approved</option>
          </select>
        </div>

        <div class="sidebar-field">
          <label class="sidebar-label">Priority</label>
          <select v-model="form.priority" class="sidebar-select">
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>

        <div class="sidebar-field">
          <label class="sidebar-label">Automation</label>
          <select v-model="form.automation_status" class="sidebar-select">
            <option value="">None</option>
            <option value="manual">Manual</option>
            <option value="automated">Automated</option>
            <option value="needs_update">Needs Update</option>
          </select>
        </div>

        <div class="sidebar-field">
          <label class="sidebar-label">Tags</label>
          <div class="tags-wrap">
            <span v-for="(tag, i) in form.tags" :key="i" class="tag-chip">
              {{ tag }}
              <button class="tag-remove" @click="removeTag(i)">&times;</button>
            </span>
            <input
              v-model="tagInput"
              class="tag-input"
              placeholder="Add tag..."
              @keydown.enter.prevent="addTag"
              @keydown.backspace="onTagBackspace"
            />
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api, { entityLinksApi } from '@/services/api'
import StepsEditor from './StepsEditor.vue'
import LinkSearch from './LinkSearch.vue'

const props = defineProps({
  testCase: { type: Object, required: true },
  projectId: { type: String, default: null },
})

const emit = defineEmits(['close', 'save', 'delete'])
const router = useRouter()

const detailTabs = [
  { key: 'details', label: 'Details' },
  { key: 'steps', label: 'Steps' },
  { key: 'parameters', label: 'Parameters' },
  { key: 'links', label: 'Links' },
]

const activeDetailTab = ref('details')
const tagInput = ref('')
const impLoading = ref(false)
const impError = ref('')

const form = ref({
  title: '',
  description: '',
  preconditions: '',
  postconditions: '',
  steps: [],
  status: 'draft',
  priority: 'medium',
  automation_status: '',
  tags: [],
  linked_issue_ids: [],
  linked_article_ids: [],
  parameters: [],
})

// Linked entities preview data
const linkedIssuesData = ref([])
const linkedArticlesData = ref([])

const issueItems = computed(() =>
  form.value.linked_issue_ids.map(id => {
    const d = linkedIssuesData.value.find(i => i.id === id)
    return {
      id,
      type: 'task',
      badge: d?.badge || null,
      label: d?.label || id.slice(0, 8),
      status: d?.status,
    }
  })
)

const articleItems = computed(() =>
  form.value.linked_article_ids.map(id => {
    const d = linkedArticlesData.value.find(a => a.id === id)
    return {
      id,
      type: 'article',
      badge: d?.badge || null,
      label: d?.label || id.slice(0, 8),
      status: d?.status,
    }
  })
)

onMounted(() => {
  if (props.testCase) {
    form.value = {
      title: props.testCase.title || '',
      description: props.testCase.description || '',
      preconditions: props.testCase.preconditions || '',
      postconditions: props.testCase.postconditions || '',
      steps: (props.testCase.steps || []).map(s => ({ ...s })),
      status: props.testCase.status || 'draft',
      priority: props.testCase.priority || 'medium',
      automation_status: props.testCase.automation_status || '',
      tags: [...(props.testCase.tags || [])],
      linked_issue_ids: [...(props.testCase.linked_issue_ids || [])],
      linked_article_ids: [...(props.testCase.linked_article_ids || [])],
      parameters: (props.testCase.parameters || []).map(p => ({
        key: p.key || '',
        values: Array.isArray(p.values) ? p.values.join(', ') : (p.values || ''),
        _id: Math.random()
      })),
    }
    hydrateLinkedEntities()
  }
})

function addIssue(item) {
  if (!form.value.linked_issue_ids.includes(item.id)) {
    form.value.linked_issue_ids.push(item.id)
    linkedIssuesData.value.push({ id: item.id, badge: item.badge, label: item.label, status: item.status })
  }
}

function removeIssue(id) {
  form.value.linked_issue_ids = form.value.linked_issue_ids.filter(i => i !== id)
  linkedIssuesData.value = linkedIssuesData.value.filter(i => i.id !== id)
}

function addArticle(item) {
  if (!form.value.linked_article_ids.includes(item.id)) {
    form.value.linked_article_ids.push(item.id)
    linkedArticlesData.value.push({ id: item.id, badge: item.badge, label: item.label, status: item.status })
  }
}

function removeArticle(id) {
  form.value.linked_article_ids = form.value.linked_article_ids.filter(a => a !== id)
  linkedArticlesData.value = linkedArticlesData.value.filter(a => a.id !== id)
}

// Hydrate linked entities via entityLinksApi.getPreview
async function hydrateLinkedEntities() {
  const issueIds = form.value.linked_issue_ids || []
  const articleIds = form.value.linked_article_ids || []

  if (issueIds.length) {
    const results = await Promise.all(
      issueIds.map(id =>
        entityLinksApi.getPreview('task', id)
          .then(r => ({
            id: r.data.id,
            type: 'task',
            badge: r.data.human_id,
            label: r.data.title,
            status: r.data.status,
          }))
          .catch(() => ({ id, type: 'task', badge: null, label: id.slice(0, 8), status: null }))
      )
    )
    linkedIssuesData.value = results
  }

  if (articleIds.length) {
    const results = await Promise.all(
      articleIds.map(id =>
        entityLinksApi.getPreview('article', id)
          .then(r => ({
            id: r.data.id,
            type: 'article',
            badge: r.data.human_id || null,
            label: r.data.title,
            status: r.data.status,
          }))
          .catch(() => ({ id, type: 'article', badge: null, label: id.slice(0, 8), status: null }))
      )
    )
    linkedArticlesData.value = results
  }
}

function navigateToEntity(item) {
  if (item.type === 'task') {
    const target = item.badge || item.id
    router.push(`/issues/${target}`)
    emit('close')
  } else if (item.type === 'article') {
    router.push('/articles')
    emit('close')
  }
}

function addParameter() {
  form.value.parameters.push({ key: '', values: '', _id: Math.random() })
}

function removeParameter(idx) {
  form.value.parameters.splice(idx, 1)
}

const paramCombinations = computed(() => {
  const params = form.value.parameters.filter(p => p.key && p.values)
  if (!params.length) return 0
  return params.reduce((acc, p) => {
    const vals = p.values.split(',').map(v => v.trim()).filter(Boolean)
    return acc * (vals.length || 1)
  }, 1)
})

async function handleImprove() {
  if (impLoading.value) return
  impLoading.value = true
  impError.value = ''

  const provider = localStorage.getItem('llm_default_provider') || 'ollama'
  const model = localStorage.getItem('llm_default_model') || 'qwen2.5-coder:7b'

  try {
    const resp = await api.post(`/testcases/${props.testCase.id}/improve`, {
      provider,
      model,
    })
    const improved = resp.data

    if (improved.title)        form.value.title        = improved.title
    if (improved.description !== undefined) form.value.description  = improved.description
    if (improved.preconditions !== undefined) form.value.preconditions = improved.preconditions
    if (improved.postconditions !== undefined) form.value.postconditions = improved.postconditions
    if (improved.steps?.length) {
      form.value.steps = improved.steps.map(s => ({
        action:   s.action   || '',
        expected: s.expected || '',
        data:     s.data     || '',
      }))
    }
  } catch (err) {
    impError.value = err.response?.data?.detail || 'Ollama unavailable'
    setTimeout(() => { impError.value = '' }, 5000)
  } finally {
    impLoading.value = false
  }
}

function handleSave() {
  const saveData = {
    ...form.value,
    parameters: form.value.parameters
      .filter(p => p.key.trim())
      .map(p => ({
        key: p.key.trim(),
        values: p.values.split(',').map(v => v.trim()).filter(Boolean)
      }))
  }
  emit('save', saveData)
}

function addTag() {
  const val = tagInput.value.trim()
  if (val && !form.value.tags.includes(val)) {
    form.value.tags.push(val)
  }
  tagInput.value = ''
}

function removeTag(idx) {
  form.value.tags.splice(idx, 1)
}

function onTagBackspace() {
  if (!tagInput.value && form.value.tags.length > 0) {
    form.value.tags.pop()
  }
}
</script>

<style scoped>
.tcv-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
  color: var(--text-primary);
}

.tcv-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  min-height: 48px;
  padding: 0 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.tcv-topbar-left,
.tcv-topbar-right { display: flex; align-items: center; gap: 12px; }

.btn-back {
  background: none; border: none; color: var(--text-secondary);
  font-size: 13px; cursor: pointer; padding: 4px 8px; border-radius: 4px;
}
.btn-back:hover { color: var(--text-primary); background: var(--bg-tertiary); }

.tcv-human-id {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 14px; color: var(--accent); font-weight: 600;
}
.btn-delete {
  padding: 6px 14px; background: rgba(239, 68, 68, 0.15); border: none;
  border-radius: 6px; color: #ef4444; font-size: 13px; cursor: pointer;
}
.btn-delete:hover { background: rgba(239, 68, 68, 0.25); }
.btn-cancel {
  padding: 6px 14px; background: none; border: 1px solid var(--border-color);
  border-radius: 6px; color: var(--text-secondary); font-size: 13px; cursor: pointer;
}
.btn-cancel:hover { color: var(--text-primary); }
.btn-save {
  padding: 6px 18px; background: var(--accent); border: none; border-radius: 6px;
  color: #fff; font-size: 13px; font-weight: 500; cursor: pointer;
}
.btn-save:hover { opacity: 0.85; }

.tcv-body { flex: 1; display: grid; grid-template-columns: 1fr 280px; overflow: hidden; }
.tcv-left { display: flex; flex-direction: column; overflow-y: auto; }

.tcv-tabs {
  display: flex; gap: 0; padding: 0 20px;
  border-bottom: 1px solid var(--border-color); background: var(--bg-secondary);
}
.tcv-tab {
  padding: 10px 16px; background: none; border: none;
  border-bottom: 2px solid transparent; color: var(--text-secondary);
  font-size: 13px; cursor: pointer; transition: all 0.15s;
}
.tcv-tab:hover { color: var(--text-primary); }
.tcv-tab.active { color: var(--text-primary); border-bottom-color: var(--accent); }
.tcv-tab-content { flex: 1; padding: 20px; overflow-y: auto; }

.field-label {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 6px;
  margin-top: 16px;
}
.field-label:first-child { margin-top: 0; }

.field-input {
  width: 100%;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
}
.field-input:focus { border-color: var(--accent); }

.field-textarea {
  width: 100%;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  font-family: inherit;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
}
.field-textarea:focus { border-color: var(--accent); }

.tab-steps { padding: 0; }

.tcv-sidebar {
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-color);
  padding: 20px 16px;
  overflow-y: auto;
}

.sidebar-field { margin-bottom: 20px; }

.sidebar-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.sidebar-select {
  width: 100%;
  padding: 7px 10px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  cursor: pointer;
}
.sidebar-select:focus { border-color: var(--accent); }

.tags-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  min-height: 36px;
  align-items: center;
}

.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  color: var(--accent);
  font-size: 12px;
}

.tag-remove {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}
.tag-remove:hover { color: #ef4444; }

.tag-input {
  flex: 1;
  min-width: 60px;
  background: none;
  border: none;
  color: var(--text-primary);
  font-size: 12px;
  outline: none;
}
.tag-input::placeholder { color: var(--placeholder-color); }

.tab-parameters { padding: 0; }

.param-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
}

.param-hint {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0;
  flex: 1;
  line-height: 1.5;
}

.btn-add-param {
  padding: 6px 14px;
  background: var(--accent);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
}
.btn-add-param:hover { opacity: 0.85; }

.param-table {
  width: 100%;
  border-collapse: collapse;
}

.param-table th {
  padding: 8px 10px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-color);
  text-align: left;
}

.col-param-key { width: 35%; }
.col-param-values { width: auto; }
.col-param-del { width: 32px; }

.param-row td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--border-color);
  vertical-align: middle;
}

.param-input {
  width: 100%;
  padding: 6px 8px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
}
.param-input:focus { border-color: var(--accent); }

.param-del {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 18px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
}
.param-del:hover { color: #ef4444; background: rgba(239,68,68,0.1); }

.param-empty {
  padding: 24px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
  border: 1px dashed var(--border-color);
  border-radius: 6px;
}

.param-preview {
  margin-top: 12px;
  padding: 8px 12px;
  background: var(--accent-muted);
  border-radius: 6px;
}

.param-preview-title {
  margin: 0;
  font-size: 12px;
  color: var(--accent);
  font-weight: 500;
}

/* IMP button */
.btn-imp {
  padding: 6px 14px;
  background: transparent;
  border: 1px solid var(--accent);
  border-radius: 6px;
  color: var(--accent);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}
.btn-imp:hover:not(:disabled) {
  background: var(--accent-muted);
}
.btn-imp:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
.btn-imp--loading {
  opacity: 0.75;
}

.imp-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid var(--accent-subtle);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: imp-spin 0.7s linear infinite;
  flex-shrink: 0;
}
@keyframes imp-spin {
  to { transform: rotate(360deg); }
}

.imp-error {
  font-size: 12px;
  color: var(--error);
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
