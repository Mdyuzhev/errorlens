<template>
  <div class="editor-overlay" @click.self="$emit('close')">
    <div class="editor-panel">
      <div class="editor-header">
        <h3>{{ rule ? 'Edit Rule' : 'New Automation Rule' }}</h3>
        <button class="btn-icon" @click="$emit('close')">&times;</button>
      </div>

      <div class="editor-body">
        <!-- Name -->
        <div class="field">
          <label>Rule Name</label>
          <input v-model="form.name" placeholder="e.g. Run tests on Review" class="input" />
        </div>

        <div class="field">
          <label class="toggle-row">
            <input type="checkbox" v-model="form.is_active" />
            <span>Active</span>
          </label>
        </div>

        <!-- Trigger -->
        <div class="section-title">Trigger</div>

        <div class="field-row">
          <div class="field">
            <label>Event</label>
            <select v-model="form.trigger_event" class="input">
              <option value="task.status_changed">Task status changed</option>
            </select>
          </div>
          <div class="field">
            <label>Task Type</label>
            <select v-model="form.task_type_id" class="input" @change="onTypeChange">
              <option :value="null">Any</option>
              <option v-for="t in types" :key="t.id" :value="t.id">{{ t.name }}</option>
            </select>
          </div>
        </div>

        <div class="field-row">
          <div class="field">
            <label>From Status</label>
            <select v-model="form.trigger_conditions.from_status_id" class="input">
              <option :value="undefined">Any</option>
              <option v-for="s in statuses" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
          </div>
          <div class="field">
            <label>To Status</label>
            <select v-model="form.trigger_conditions.to_status_id" class="input">
              <option :value="undefined">Any</option>
              <option v-for="s in statuses" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
          </div>
        </div>

        <!-- Actions -->
        <div class="section-title">
          Actions
          <button class="btn btn-sm" @click="addAction">+ Add Action</button>
        </div>

        <div v-for="(action, i) in form.actions" :key="i" class="action-card">
          <div class="action-header">
            <span class="action-num">Action {{ i + 1 }}</span>
            <div class="action-controls">
              <button v-if="i > 0" class="btn-icon-sm" @click="moveAction(i, -1)" title="Move up">↑</button>
              <button v-if="i < form.actions.length - 1" class="btn-icon-sm" @click="moveAction(i, 1)" title="Move down">↓</button>
              <button class="btn-icon-sm btn-danger" @click="removeAction(i)" title="Remove">&times;</button>
            </div>
          </div>

          <div class="field">
            <label>Type</label>
            <select v-model="action.type" class="input" @change="onActionTypeChange(action)">
              <option value="run_gitlab_pipeline">Run GitLab Pipeline</option>
              <option value="change_task_status">Change Task Status</option>
              <option value="add_comment">Add Comment</option>
            </select>
          </div>

          <!-- Change Task Status -->
          <template v-if="action.type === 'change_task_status'">
            <div class="field">
              <label>Target Status</label>
              <select v-model="action.params.status_id" class="input">
                <option v-for="s in statuses" :key="s.id" :value="s.id">{{ s.name }}</option>
              </select>
            </div>
          </template>

          <!-- Add Comment -->
          <template v-if="action.type === 'add_comment'">
            <div class="field">
              <label>Comment Text</label>
              <textarea v-model="action.params.text" class="input textarea" rows="2"
                placeholder="Tests passed for {{task.human_id}}" />
              <span class="hint">Available: {{ '{{task.human_id}}, {{task.title}}, {{pipeline.url}}, {{pipeline.status}}' }}</span>
            </div>
          </template>

          <!-- Run GitLab Pipeline -->
          <template v-if="action.type === 'run_gitlab_pipeline'">
            <div class="field-row">
              <div class="field">
                <label>Connection</label>
                <select v-model="action.params.connection_id" class="input" @change="loadGitlabProjects(action)">
                  <option v-for="c in gitlabConnections" :key="c.id" :value="c.id">{{ c.name }}</option>
                </select>
              </div>
              <div class="field">
                <label>Project</label>
                <select v-model="action.params.gitlab_project_id" class="input">
                  <option v-for="p in action._projects || []" :key="p.id" :value="p.id">
                    {{ p.path_with_namespace }}
                  </option>
                </select>
              </div>
            </div>
            <div class="field">
              <label>Branch / Ref</label>
              <input v-model="action.params.ref" class="input" placeholder="main" />
            </div>

            <!-- Pipeline variables -->
            <div class="field">
              <label>Variables</label>
              <div v-for="(v, vi) in action.params.variables || []" :key="vi" class="var-row">
                <input v-model="v.key" class="input input-sm" placeholder="KEY" />
                <span class="var-eq">=</span>
                <input v-model="v.value" class="input input-sm" placeholder="value or {{task.human_id}}" />
                <button class="btn-icon-sm btn-danger" @click="action.params.variables.splice(vi, 1)">&times;</button>
              </div>
              <button class="btn btn-xs" @click="addVariable(action)">+ Variable</button>
            </div>

            <!-- Sub-actions -->
            <div class="sub-actions">
              <div class="sub-section">
                <label>On Success</label>
                <div v-for="(sa, si) in action.params.on_success || []" :key="si" class="sub-action-row">
                  <select v-model="sa.type" class="input input-sm">
                    <option value="change_task_status">Change Status</option>
                    <option value="add_comment">Add Comment</option>
                  </select>
                  <select v-if="sa.type === 'change_task_status'" v-model="sa.params.status_id" class="input input-sm">
                    <option v-for="s in statuses" :key="s.id" :value="s.id">{{ s.name }}</option>
                  </select>
                  <input v-if="sa.type === 'add_comment'" v-model="sa.params.text" class="input input-sm"
                    placeholder="Comment text..." />
                  <button class="btn-icon-sm btn-danger" @click="action.params.on_success.splice(si, 1)">&times;</button>
                </div>
                <button class="btn btn-xs" @click="addSubAction(action, 'on_success')">+ On Success</button>
              </div>

              <div class="sub-section">
                <label>On Failure</label>
                <div v-for="(sa, si) in action.params.on_failure || []" :key="si" class="sub-action-row">
                  <select v-model="sa.type" class="input input-sm">
                    <option value="change_task_status">Change Status</option>
                    <option value="add_comment">Add Comment</option>
                  </select>
                  <select v-if="sa.type === 'change_task_status'" v-model="sa.params.status_id" class="input input-sm">
                    <option v-for="s in statuses" :key="s.id" :value="s.id">{{ s.name }}</option>
                  </select>
                  <input v-if="sa.type === 'add_comment'" v-model="sa.params.text" class="input input-sm"
                    placeholder="Comment text..." />
                  <button class="btn-icon-sm btn-danger" @click="action.params.on_failure.splice(si, 1)">&times;</button>
                </div>
                <button class="btn btn-xs" @click="addSubAction(action, 'on_failure')">+ On Failure</button>
              </div>
            </div>
          </template>
        </div>

        <div v-if="form.actions.length === 0" class="empty-actions">
          No actions configured. Add at least one action.
        </div>
      </div>

      <div class="editor-footer">
        <button class="btn btn-ghost" @click="$emit('close')">Cancel</button>
        <button class="btn btn-accent" @click="save" :disabled="saving">
          {{ saving ? 'Saving...' : (rule ? 'Update' : 'Create') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { automationsApi, taskSettingsApi, gitlabApi } from '@/services/api'

const props = defineProps({
  rule: { type: Object, default: null },
  projectId: { type: String, required: true },
})
const emit = defineEmits(['close', 'saved'])

const types = ref([])
const statuses = ref([])
const gitlabConnections = ref([])
const saving = ref(false)

const form = reactive({
  name: props.rule?.name || '',
  is_active: props.rule?.is_active ?? true,
  trigger_event: props.rule?.trigger_event || 'task.status_changed',
  task_type_id: props.rule?.task_type_id || null,
  trigger_conditions: { ...(props.rule?.trigger_conditions || {}) },
  actions: (props.rule?.actions || []).map(a => ({
    type: a.type,
    params: { ...a.params, variables: [...(a.params?.variables || [])],
      on_success: (a.params?.on_success || []).map(s => ({ type: s.type, params: { ...s.params } })),
      on_failure: (a.params?.on_failure || []).map(s => ({ type: s.type, params: { ...s.params } })),
    },
    _projects: [],
  })),
})

onMounted(async () => {
  const [typesRes, connectionsRes] = await Promise.all([
    taskSettingsApi.getTypes(props.projectId),
    gitlabApi.listConnections(props.projectId).catch(() => ({ data: [] })),
  ])
  types.value = typesRes.data
  gitlabConnections.value = connectionsRes.data

  if (form.task_type_id) {
    await loadStatuses(form.task_type_id)
  } else if (types.value.length > 0) {
    await loadAllStatuses()
  }

  // Load gitlab projects for existing pipeline actions
  for (const action of form.actions) {
    if (action.type === 'run_gitlab_pipeline' && action.params.connection_id) {
      await loadGitlabProjects(action)
    }
  }
})

async function loadStatuses(typeId) {
  const { data } = await taskSettingsApi.getStatuses(typeId, props.projectId)
  statuses.value = data
}

async function loadAllStatuses() {
  const all = []
  const seen = new Set()
  for (const t of types.value) {
    try {
      const { data } = await taskSettingsApi.getStatuses(t.id, props.projectId)
      for (const s of data) {
        if (!seen.has(s.id)) { seen.add(s.id); all.push(s) }
      }
    } catch { /* skip */ }
  }
  statuses.value = all
}

async function onTypeChange() {
  if (form.task_type_id) {
    await loadStatuses(form.task_type_id)
  } else {
    await loadAllStatuses()
  }
}

async function loadGitlabProjects(action) {
  if (!action.params.connection_id) return
  try {
    const { data } = await gitlabApi.listProjects(action.params.connection_id)
    action._projects = data
  } catch {
    action._projects = []
  }
}

function addAction() {
  form.actions.push({
    type: 'add_comment',
    params: { text: '' },
    _projects: [],
  })
}

function removeAction(i) {
  form.actions.splice(i, 1)
}

function moveAction(i, dir) {
  const j = i + dir
  const tmp = form.actions[i]
  form.actions[i] = form.actions[j]
  form.actions[j] = tmp
}

function onActionTypeChange(action) {
  if (action.type === 'change_task_status') {
    action.params = { status_id: '' }
  } else if (action.type === 'add_comment') {
    action.params = { text: '' }
  } else if (action.type === 'run_gitlab_pipeline') {
    action.params = { connection_id: '', gitlab_project_id: '', ref: 'main', variables: [], on_success: [], on_failure: [] }
  }
}

function addVariable(action) {
  if (!action.params.variables) action.params.variables = []
  action.params.variables.push({ key: '', value: '' })
}

function addSubAction(action, key) {
  if (!action.params[key]) action.params[key] = []
  action.params[key].push({ type: 'add_comment', params: { text: '' } })
}

async function save() {
  saving.value = true
  try {
    // Clean actions: remove _projects
    const cleanActions = form.actions.map(({ _projects, ...rest }) => rest)

    // Clean trigger_conditions: remove undefined values
    const conditions = {}
    if (form.trigger_conditions.to_status_id) conditions.to_status_id = form.trigger_conditions.to_status_id
    if (form.trigger_conditions.from_status_id) conditions.from_status_id = form.trigger_conditions.from_status_id

    // Add status names for display
    const toStatus = statuses.value.find(s => s.id === conditions.to_status_id)
    const fromStatus = statuses.value.find(s => s.id === conditions.from_status_id)
    if (toStatus) conditions.to_status_name = toStatus.name
    if (fromStatus) conditions.from_status_name = fromStatus.name

    const payload = {
      project_id: props.projectId,
      name: form.name,
      is_active: form.is_active,
      trigger_event: form.trigger_event,
      task_type_id: form.task_type_id,
      trigger_conditions: conditions,
      actions: cleanActions,
    }

    if (props.rule) {
      await automationsApi.updateRule(props.rule.id, payload)
    } else {
      await automationsApi.createRule(payload)
    }
    emit('saved')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.editor-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding-top: 40px;
  overflow-y: auto;
}

.editor-panel {
  background: var(--bg-primary);
  border-radius: 14px;
  width: 640px;
  max-width: 95vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.editor-header h3 {
  margin: 0;
  font-size: 18px;
}

.editor-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.editor-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.field {
  margin-bottom: 14px;
}

.field label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.input {
  width: 100%;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
  box-sizing: border-box;
}

.textarea {
  resize: vertical;
  font-family: inherit;
}

.input-sm {
  padding: 6px 8px;
  font-size: 13px;
}

.field-row {
  display: flex;
  gap: 12px;
}

.field-row .field {
  flex: 1;
}

.section-title {
  font-weight: 600;
  font-size: 15px;
  margin: 20px 0 12px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.action-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 12px;
}

.action-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.action-num {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-secondary);
}

.action-controls {
  display: flex;
  gap: 4px;
}

.btn-icon-sm {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 4px;
  font-size: 14px;
  line-height: 1;
}

.btn-icon-sm:hover {
  background: var(--bg-secondary);
}

.btn-icon-sm.btn-danger:hover {
  color: #e53935;
}

.hint {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.var-row {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 6px;
}

.var-eq {
  color: var(--text-secondary);
  font-weight: bold;
}

.sub-actions {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--border-color);
}

.sub-section {
  margin-bottom: 12px;
}

.sub-section > label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  display: block;
  margin-bottom: 6px;
}

.sub-action-row {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 6px;
}

.empty-actions {
  text-align: center;
  padding: 20px;
  color: var(--text-secondary);
  font-size: 13px;
}

.toggle-row {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.btn {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

.btn-sm {
  padding: 4px 10px;
  font-size: 12px;
}

.btn-xs {
  padding: 3px 8px;
  font-size: 11px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
}

.btn-xs:hover {
  color: var(--text-primary);
}

.btn-ghost {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.btn-accent {
  background: var(--accent);
  color: white;
}

.btn-accent:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-icon {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 22px;
  padding: 4px;
}
</style>
