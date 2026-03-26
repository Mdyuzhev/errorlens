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
            <div v-if="!form.linked_issue_ids || form.linked_issue_ids.length === 0" class="empty-links">
              No linked issues
            </div>
            <div v-else class="links-list">
              <a
                v-for="lid in form.linked_issue_ids"
                :key="lid"
                class="link-item"
                :href="'#/issues/' + lid"
              >
                {{ lid }}
              </a>
            </div>
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
import { ref, onMounted } from 'vue'
import StepsEditor from './StepsEditor.vue'

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
})

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
    }
  }
})

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
  background: #0f0e17;
  display: flex;
  flex-direction: column;
  color: #e8e6f0;
}

.tcv-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  min-height: 48px;
  padding: 0 20px;
  background: #16152a;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
}

.tcv-topbar-left,
.tcv-topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-back {
  background: none;
  border: none;
  color: #7a788a;
  font-size: 13px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}
.btn-back:hover {
  color: #e8e6f0;
  background: #22203a;
}

.tcv-human-id {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 14px;
  color: #9b7de0;
  font-weight: 600;
}

.btn-cancel {
  padding: 6px 14px;
  background: none;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 6px;
  color: #7a788a;
  font-size: 13px;
  cursor: pointer;
}
.btn-cancel:hover {
  color: #e8e6f0;
}

.btn-save {
  padding: 6px 18px;
  background: #7c5cbf;
  border: none;
  border-radius: 6px;
  color: #e8e6f0;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
.btn-save:hover {
  opacity: 0.85;
}

/* Body */
.tcv-body {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 280px;
  overflow: hidden;
}

.tcv-left {
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: 0;
}

/* Detail tabs */
.tcv-tabs {
  display: flex;
  gap: 0;
  padding: 0 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  background: #16152a;
}

.tcv-tab {
  padding: 10px 16px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: #7a788a;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}
.tcv-tab:hover {
  color: #e8e6f0;
}
.tcv-tab.active {
  color: #e8e6f0;
  border-bottom-color: #7c5cbf;
}

.tcv-tab-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

/* Details tab */
.field-label {
  display: block;
  font-size: 12px;
  color: #7a788a;
  margin-bottom: 6px;
  margin-top: 16px;
}
.field-label:first-child {
  margin-top: 0;
}

.field-input {
  width: 100%;
  padding: 8px 12px;
  background: #22203a;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 6px;
  color: #e8e6f0;
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
}
.field-input:focus {
  border-color: #7c5cbf;
}

.field-textarea {
  width: 100%;
  padding: 8px 12px;
  background: #22203a;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 6px;
  color: #e8e6f0;
  font-size: 13px;
  font-family: inherit;
  resize: vertical;
  outline: none;
  box-sizing: border-box;
}
.field-textarea:focus {
  border-color: #7c5cbf;
}

/* Steps tab */
.tab-steps {
  padding: 0;
}

/* Links tab */
.empty-links {
  color: #4a4858;
  font-size: 13px;
  padding: 20px 0;
}

.links-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.link-item {
  display: inline-flex;
  padding: 6px 12px;
  background: #22203a;
  border-radius: 6px;
  color: #9b7de0;
  font-size: 13px;
  text-decoration: none;
  transition: background 0.15s;
}
.link-item:hover {
  background: #2d2b47;
}

/* Sidebar */
.tcv-sidebar {
  background: #16152a;
  border-left: 1px solid rgba(255, 255, 255, 0.07);
  padding: 20px 16px;
  overflow-y: auto;
}

.sidebar-field {
  margin-bottom: 20px;
}

.sidebar-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #7a788a;
  margin-bottom: 6px;
}

.sidebar-select {
  width: 100%;
  padding: 7px 10px;
  background: #22203a;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 6px;
  color: #e8e6f0;
  font-size: 13px;
  outline: none;
  cursor: pointer;
}
.sidebar-select:focus {
  border-color: #7c5cbf;
}

/* Tags */
.tags-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px;
  background: #22203a;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 6px;
  min-height: 36px;
  align-items: center;
}

.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: rgba(124, 92, 191, 0.2);
  border-radius: 4px;
  color: #9b7de0;
  font-size: 12px;
}

.tag-remove {
  background: none;
  border: none;
  color: #7a788a;
  font-size: 14px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}
.tag-remove:hover {
  color: #ef4444;
}

.tag-input {
  flex: 1;
  min-width: 60px;
  background: none;
  border: none;
  color: #e8e6f0;
  font-size: 12px;
  outline: none;
}
.tag-input::placeholder {
  color: #4a4858;
}
</style>
