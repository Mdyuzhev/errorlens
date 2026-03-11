<template>
  <div class="automations-tab">
    <div class="section-header">
      <h2>Automations</h2>
      <div class="header-actions">
        <select v-model="selectedProjectId" class="project-select" @change="loadRules">
          <option value="">Select project...</option>
          <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
        <button v-if="selectedProjectId" class="btn btn-sm btn-accent" @click="openEditor(null)">+ New Rule</button>
      </div>
    </div>

    <div v-if="!selectedProjectId" class="empty-state">
      Select a project to manage automation rules
    </div>

    <div v-if="loading" class="loading-state">Loading...</div>

    <div v-if="selectedProjectId && !loading && rules.length === 0" class="empty-state">
      No automation rules yet. Create one to automate task workflows.
    </div>

    <div v-if="rules.length > 0" class="rules-list">
      <div v-for="rule in rules" :key="rule.id" class="rule-card">
        <div class="rule-header">
          <div class="rule-title">
            <span class="rule-name">{{ rule.name }}</span>
            <span class="rule-badge" :class="rule.is_active ? 'active' : 'inactive'">
              {{ rule.is_active ? 'Active' : 'Inactive' }}
            </span>
          </div>
          <div class="rule-actions">
            <button class="btn-icon" title="Edit" @click="openEditor(rule)">
              <AppIcon name="edit" :size="14" />
            </button>
            <button class="btn-icon btn-danger" title="Delete" @click="deleteRule(rule)">
              <AppIcon name="trash" :size="14" />
            </button>
          </div>
        </div>
        <div class="rule-meta">
          <span class="meta-item">
            Trigger: {{ formatTrigger(rule) }}
          </span>
          <span v-if="rule.task_type_name" class="meta-item">
            Type: {{ rule.task_type_name }}
          </span>
          <span class="meta-item">
            Actions: {{ rule.actions?.length || 0 }}
          </span>
          <span class="meta-item clickable" @click="openRuns(rule)">
            Runs (7d): {{ rule.runs_count || 0 }}
          </span>
        </div>
      </div>
    </div>

    <!-- Rule Editor Modal -->
    <AutomationRuleEditor
      v-if="showEditor"
      :rule="editingRule"
      :project-id="selectedProjectId"
      @close="showEditor = false"
      @saved="onRuleSaved"
    />

    <!-- Runs Drawer -->
    <div v-if="showRuns" class="runs-drawer-overlay" @click.self="showRuns = false">
      <div class="runs-drawer">
        <div class="drawer-header">
          <h3>Runs: {{ runsForRule?.name }}</h3>
          <button class="btn-icon" @click="showRuns = false">&times;</button>
        </div>
        <div v-if="runs.length === 0" class="empty-state">No runs yet</div>
        <div v-for="run in runs" :key="run.id" class="run-item">
          <div class="run-header">
            <span class="run-status" :class="run.status">{{ run.status }}</span>
            <span class="run-time">{{ formatTime(run.started_at) }}</span>
          </div>
          <div v-if="run.error" class="run-error">{{ run.error }}</div>
          <div v-if="run.gitlab_pipeline_id" class="run-pipeline">
            Pipeline #{{ run.gitlab_pipeline_id }}
          </div>
          <div v-if="run.actions_log?.length" class="run-actions-log">
            <div v-for="(log, i) in run.actions_log" :key="i" class="log-entry">
              <span class="log-type">{{ log.type }}</span>
              <span class="log-status" :class="log.status">{{ log.status }}</span>
              <span v-if="log.error" class="log-error">{{ log.error }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { automationsApi } from '@/services/api'
import { projectsApi } from '@/services/api'
import AppIcon from '@/components/common/AppIcon.vue'
import AutomationRuleEditor from './AutomationRuleEditor.vue'

const projects = ref([])
const selectedProjectId = ref('')
const rules = ref([])
const loading = ref(false)
const showEditor = ref(false)
const editingRule = ref(null)
const showRuns = ref(false)
const runsForRule = ref(null)
const runs = ref([])

onMounted(async () => {
  const { data } = await projectsApi.list()
  projects.value = data
  if (data.length === 1) {
    selectedProjectId.value = data[0].id
    await loadRules()
  }
})

async function loadRules() {
  if (!selectedProjectId.value) { rules.value = []; return }
  loading.value = true
  try {
    const { data } = await automationsApi.getRules(selectedProjectId.value)
    rules.value = data
  } finally {
    loading.value = false
  }
}

function openEditor(rule) {
  editingRule.value = rule
  showEditor.value = true
}

async function deleteRule(rule) {
  if (!confirm(`Delete rule "${rule.name}"?`)) return
  await automationsApi.deleteRule(rule.id)
  await loadRules()
}

async function openRuns(rule) {
  runsForRule.value = rule
  showRuns.value = true
  const { data } = await automationsApi.getRuleRuns(rule.id)
  runs.value = data
}

function onRuleSaved() {
  showEditor.value = false
  loadRules()
}

function formatTrigger(rule) {
  const cond = rule.trigger_conditions || {}
  let parts = ['Status changed']
  if (cond.to_status_name) parts.push(`→ ${cond.to_status_name}`)
  if (cond.from_status_name) parts.push(`from ${cond.from_status_name}`)
  return parts.join(' ')
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = Math.floor((now - d) / 1000)
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}
</script>

<style scoped>
.automations-tab {
  max-width: 900px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.section-header h2 {
  margin: 0;
  font-size: 20px;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.project-select {
  padding: 8px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
}

.btn-accent {
  background: var(--accent);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-accent:hover {
  opacity: 0.9;
}

.empty-state, .loading-state {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary);
}

.rules-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rule-card {
  background: var(--bg-card);
  border-radius: 10px;
  padding: 16px 20px;
  border: 1px solid var(--border-color);
}

.rule-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.rule-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.rule-name {
  font-weight: 600;
  font-size: 15px;
}

.rule-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.rule-badge.active {
  background: rgba(76, 175, 80, 0.15);
  color: #4caf50;
}

.rule-badge.inactive {
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.rule-actions {
  display: flex;
  gap: 6px;
}

.btn-icon {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  transition: all 0.2s;
}

.btn-icon:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.btn-icon.btn-danger:hover {
  color: #e53935;
  background: rgba(229, 57, 53, 0.1);
}

.rule-meta {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.meta-item {
  font-size: 13px;
  color: var(--text-secondary);
}

.meta-item.clickable {
  cursor: pointer;
  color: var(--accent);
}

.meta-item.clickable:hover {
  text-decoration: underline;
}

/* Runs drawer */
.runs-drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}

.runs-drawer {
  width: 420px;
  max-width: 90vw;
  background: var(--bg-primary);
  height: 100%;
  overflow-y: auto;
  padding: 24px;
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.2);
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.drawer-header h3 {
  margin: 0;
  font-size: 16px;
}

.run-item {
  padding: 12px;
  background: var(--bg-card);
  border-radius: 8px;
  margin-bottom: 10px;
  border: 1px solid var(--border-color);
}

.run-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.run-status {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 8px;
}

.run-status.completed { background: rgba(76, 175, 80, 0.15); color: #4caf50; }
.run-status.failed { background: rgba(229, 57, 53, 0.15); color: #e53935; }
.run-status.running { background: rgba(33, 150, 243, 0.15); color: #2196f3; }
.run-status.pending { background: var(--bg-secondary); color: var(--text-secondary); }

.run-time {
  font-size: 12px;
  color: var(--text-secondary);
}

.run-error {
  font-size: 12px;
  color: #e53935;
  margin-top: 4px;
}

.run-pipeline {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.run-actions-log {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
}

.log-entry {
  display: flex;
  gap: 8px;
  font-size: 12px;
  padding: 2px 0;
}

.log-type {
  color: var(--text-secondary);
}

.log-status.ok { color: #4caf50; }
.log-status.error { color: #e53935; }
.log-status.running { color: #2196f3; }

.log-error {
  color: #e53935;
  font-style: italic;
}
</style>
