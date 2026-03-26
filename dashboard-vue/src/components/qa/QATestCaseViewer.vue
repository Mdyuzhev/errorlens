<template>
  <div class="tcv-overlay">
    <!-- Topbar -->
    <div class="tcv-topbar">
      <div class="tcv-topbar-left">
        <button class="btn-back" @click="$emit('close')">&larr; Back</button>
        <span class="tcv-human-id">{{ testCase?.human_id || '' }}</span>
      </div>
      <div class="tcv-topbar-right">
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

          <!-- Links tab -->
          <div v-if="activeDetailTab === 'links'" class="tab-links">
            <LinkSearch
              title="Issues"
              empty-text="No linked issues"
              placeholder="Find issue by ID or title..."
              :items="issueItems"
              :search-fn="searchIssues"
              :exclude-ids="form.linked_issue_ids"
              @add="addIssue"
              @remove="removeIssue"
            />
            <LinkSearch
              title="Articles"
              empty-text="No linked articles"
              placeholder="Find article by title..."
              :items="articleItems"
              :search-fn="searchArticles"
              :exclude-ids="form.linked_article_ids"
              @add="addArticle"
              @remove="removeArticle"
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
import { tasksApi, articlesApi } from '@/services/api'
import StepsEditor from './StepsEditor.vue'
import LinkSearch from './LinkSearch.vue'

const props = defineProps({
  testCase: { type: Object, required: true }
})

const emit = defineEmits(['close', 'save'])

const detailTabs = [
  { key: 'details', label: 'Details' },
  { key: 'steps', label: 'Steps' },
  { key: 'links', label: 'Links' },
]

const activeDetailTab = ref('details')
const tagInput = ref('')

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
})

// Linked entities preview data
const linkedIssuesData = ref([])
const linkedArticlesData = ref([])

const issueItems = computed(() =>
  form.value.linked_issue_ids.map(id => {
    const d = linkedIssuesData.value.find(i => i.id === id)
    return { id, badge: d?.human_id || id.slice(0, 8), label: d?.title || 'Issue' }
  })
)

const articleItems = computed(() =>
  form.value.linked_article_ids.map(id => {
    const d = linkedArticlesData.value.find(a => a.id === id)
    return { id, label: d?.title || id.slice(0, 8) }
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
    }
  }
})

// Search functions for LinkSearch
async function searchIssues(q) {
  const res = await tasksApi.list({ q, limit: 10 })
  const items = Array.isArray(res.data) ? res.data : res.data.items || []
  return items.map(i => ({ id: i.id, badge: i.human_id, label: i.title, human_id: i.human_id, title: i.title }))
}

async function searchArticles(q) {
  const res = await articlesApi.list({ q, limit: 10 })
  const items = Array.isArray(res.data) ? res.data : res.data.items || []
  return items.map(a => ({ id: a.id, label: a.title, title: a.title }))
}

function addIssue(item) {
  if (!form.value.linked_issue_ids.includes(item.id)) {
    form.value.linked_issue_ids.push(item.id)
    linkedIssuesData.value.push({ id: item.id, human_id: item.human_id || item.badge, title: item.title || item.label })
  }
}

function removeIssue(id) {
  form.value.linked_issue_ids = form.value.linked_issue_ids.filter(i => i !== id)
  linkedIssuesData.value = linkedIssuesData.value.filter(i => i.id !== id)
}

function addArticle(item) {
  if (!form.value.linked_article_ids.includes(item.id)) {
    form.value.linked_article_ids.push(item.id)
    linkedArticlesData.value.push({ id: item.id, title: item.title || item.label })
  }
}

function removeArticle(id) {
  form.value.linked_article_ids = form.value.linked_article_ids.filter(a => a !== id)
  linkedArticlesData.value = linkedArticlesData.value.filter(a => a.id !== id)
}

function handleSave() {
  emit('save', { ...form.value })
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
</style>
