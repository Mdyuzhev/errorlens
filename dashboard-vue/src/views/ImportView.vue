<template>
  <div class="import-view">
    <div class="import-header">
      <h1 class="import-title">Import from TestIT</h1>
      <div class="import-steps-bar">
        <div
          v-for="(s, i) in stepLabels"
          :key="i"
          class="step-item"
          :class="{ active: store.step === i+1, done: store.step > i+1 }"
        >
          <div class="step-dot">{{ store.step > i+1 ? '✓' : i+1 }}</div>
          <span class="step-label">{{ s }}</span>
        </div>
      </div>
    </div>

    <!-- Step 1: Upload -->
    <div v-if="store.step === 1" class="import-body">
      <div
        class="dropzone"
        :class="{ dragover: isDragging, loading: store.previewLoading }"
        @dragover.prevent="isDragging = true"
        @dragleave="isDragging = false"
        @drop.prevent="onDrop"
        @click="$refs.fileInput.click()"
      >
        <div v-if="store.previewLoading" class="dropzone-loading">
          <div class="spinner"></div>
          <p>Analysing file...</p>
        </div>
        <div v-else class="dropzone-content">
          <div class="dropzone-icon">📊</div>
          <p class="dropzone-main">Drag & drop TestIT Excel file</p>
          <p class="dropzone-sub">or <u>click to browse</u></p>
          <p class="dropzone-hint">.xlsx, .xls — up to 50 MB</p>
        </div>
        <input ref="fileInput" type="file" accept=".xlsx,.xls" style="display:none" @change="onFileSelect" />
      </div>
      <div v-if="uploadError" class="error-banner">{{ uploadError }}</div>
    </div>

    <!-- Step 2: Project + Preview -->
    <div v-if="store.step === 2" class="import-body">
      <div class="preview-section">
        <div class="preview-meta">
          <span class="preview-badge">{{ store.preview?.sheet_name }}</span>
          <span class="preview-count">{{ store.preview?.total_rows?.toLocaleString() }} test cases</span>
        </div>
        <table class="preview-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Folder</th>
              <th>Title</th>
              <th>Priority</th>
              <th>Status</th>
              <th>Steps</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in (store.preview?.preview || [])" :key="i">
              <td class="tc-id">{{ row.external_id }}</td>
              <td class="tc-folder" :title="row.folder">{{ truncate(row.folder, 30) }}</td>
              <td class="tc-title">{{ truncate(row.title, 50) }}</td>
              <td><span class="priority-badge" :class="row.priority">{{ row.priority }}</span></td>
              <td><span class="status-badge-sm" :class="row.status">{{ row.status }}</span></td>
              <td>{{ row.has_steps ? '✓' : '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="project-section">
        <h3 class="section-title">Target Project</h3>
        <div class="radio-group">
          <label class="radio-label">
            <input type="radio" :value="true" v-model="store.useNewProject" />
            Create new project
          </label>
          <label class="radio-label">
            <input type="radio" :value="false" v-model="store.useNewProject" />
            Use existing
          </label>
        </div>

        <div v-if="store.useNewProject" class="new-project-form">
          <div class="form-row">
            <label>Name</label>
            <input v-model="store.newProjectName" class="form-input" placeholder="Project name" />
          </div>
          <div class="form-row">
            <label>Prefix (2-4 letters)</label>
            <input v-model="store.newProjectPrefix" class="form-input prefix-input" placeholder="VN" maxlength="4" style="text-transform:uppercase" />
          </div>
        </div>

        <div v-else class="existing-project-form">
          <label>Project</label>
          <select v-model="store.targetProjectId" class="form-input">
            <option v-for="p in projects" :key="p.id" :value="p.id">
              {{ p.key ? `[${p.key}]` : '' }} {{ p.name }}
            </option>
          </select>
        </div>
      </div>

      <div class="import-actions">
        <button class="btn-secondary" @click="store.step = 1">Back</button>
        <button
          class="btn-primary"
          :disabled="importButtonDisabled || importing"
          @click="handleStartImport"
        >
          {{ importing ? 'Creating project...' : `Import ${store.preview?.total_rows?.toLocaleString()} cases` }}
        </button>
      </div>
    </div>

    <!-- Step 3: Progress -->
    <div v-if="store.step === 3" class="import-body import-progress">
      <h2 class="progress-title">Importing test cases...</h2>
      <div class="progress-bar-wrap">
        <div class="progress-bar" :style="{ width: (store.job?.progress_pct || 0) + '%' }"></div>
      </div>
      <div class="progress-pct">{{ store.job?.progress_pct || 0 }}%</div>
      <div class="progress-counters">
        <div class="counter-item">
          <div class="counter-value">{{ (store.job?.imported || 0).toLocaleString() }}</div>
          <div class="counter-label">Cases</div>
        </div>
        <div class="counter-item">
          <div class="counter-value">{{ store.job?.folders_created || 0 }}</div>
          <div class="counter-label">Folders</div>
        </div>
        <div class="counter-item">
          <div class="counter-value">{{ store.job?.skipped || 0 }}</div>
          <div class="counter-label">Skipped</div>
        </div>
      </div>
      <p class="progress-hint">Import runs in background. You can close this page.</p>
    </div>

    <!-- Step 4: Result -->
    <div v-if="store.step === 4" class="import-body import-result">
      <div v-if="store.job?.status === 'done'">
        <h2 class="result-title">Import complete!</h2>
        <div class="result-stats">
          <div class="stat-item success">
            <div class="stat-value">{{ store.job.imported?.toLocaleString() }}</div>
            <div class="stat-label">Cases imported</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ store.job.folders_created }}</div>
            <div class="stat-label">Folders created</div>
          </div>
          <div class="stat-item" v-if="store.job.skipped > 0">
            <div class="stat-value">{{ store.job.skipped }}</div>
            <div class="stat-label">Skipped (duplicates)</div>
          </div>
        </div>
        <div v-if="store.job.errors?.length" class="error-list">
          <h4>Errors ({{ store.job.errors.length }})</h4>
          <div v-for="(e, i) in store.job.errors.slice(0,10)" :key="i" class="error-item">{{ e }}</div>
          <div v-if="store.job.errors.length > 10" class="error-more">...and {{ store.job.errors.length - 10 }} more</div>
        </div>
        <div class="result-actions">
          <button class="btn-primary" @click="goToQA">Open QA section</button>
          <button class="btn-secondary" @click="store.reset()">New import</button>
        </div>
      </div>
      <div v-else>
        <h2 class="result-title error-text">Import failed</h2>
        <p class="error-text">{{ store.job?.errors?.[0] || 'Unknown error' }}</p>
        <button class="btn-secondary" @click="store.reset()">Try again</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImportStore } from '@/stores/import'
import { useCurrentProjectStore } from '@/stores/currentProject'
import { projectsApi } from '@/services/api'

const router = useRouter()
const store = useImportStore()
const currentProjectStore = useCurrentProjectStore()
const isDragging = ref(false)
const uploadError = ref(null)
const importing = ref(false)
const projects = ref([])

const stepLabels = ['File', 'Project', 'Import', 'Done']

const importButtonDisabled = computed(() => {
  if (store.useNewProject) return !store.newProjectName.trim() || !store.newProjectPrefix.trim()
  return !store.targetProjectId
})

function truncate(str, max) {
  if (!str) return ''
  return str.length > max ? str.slice(0, max) + '...' : str
}

async function onFileSelect(e) {
  const file = e.target.files?.[0]
  if (file) await processFile(file)
}

async function onDrop(e) {
  isDragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) await processFile(file)
}

async function processFile(file) {
  uploadError.value = null
  if (!file.name.match(/\.(xlsx|xls)$/i)) {
    uploadError.value = 'Only .xlsx and .xls files are supported'
    return
  }
  try {
    await store.loadPreview(file)
  } catch (e) {
    uploadError.value = 'Failed to read file: ' + (e?.response?.data?.detail || e.message)
  }
}

async function handleStartImport() {
  importing.value = true
  try {
    let projectId = store.targetProjectId
    if (store.useNewProject) {
      const resp = await projectsApi.create({
        name: store.newProjectName.trim(),
        prefix: store.newProjectPrefix.trim().toUpperCase(),
      })
      projectId = resp.data.id
    }
    await store.startImport(projectId)
  } catch (e) {
    uploadError.value = 'Error: ' + (e?.response?.data?.detail || e.message)
  } finally {
    importing.value = false
  }
}

async function goToQA() {
  // Switch to the project where cases were imported
  if (store.targetProjectId) {
    const proj = currentProjectStore.projects.find(p => p.id === store.targetProjectId)
    if (proj) {
      currentProjectStore.setProject(proj)
    } else {
      await currentProjectStore.fetchProjects()
      const fresh = currentProjectStore.projects.find(p => p.id === store.targetProjectId)
      if (fresh) currentProjectStore.setProject(fresh)
    }
  }
  router.push('/qa')
}

onMounted(async () => {
  try {
    const resp = await projectsApi.list()
    projects.value = Array.isArray(resp.data) ? resp.data : (resp.data?.items || [])
  } catch { /* silent */ }
  // Default: import into current project
  if (currentProjectStore.currentProjectId) {
    store.useNewProject = false
    store.targetProjectId = currentProjectStore.currentProjectId
  }
})

onUnmounted(() => { store.stopPolling() })
</script>

<style scoped>
.import-view { max-width: 860px; margin: 0 auto; padding: 32px 24px; min-height: 100vh; }
.import-header { margin-bottom: 40px; }
.import-title { font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 24px; }
.import-steps-bar { display: flex; gap: 0; align-items: center; }
.step-item { display: flex; align-items: center; gap: 8px; opacity: 0.4; transition: opacity 0.2s; }
.step-item.active { opacity: 1; }
.step-item.done { opacity: 0.7; }
.step-item:not(:last-child)::after { content: '→'; margin: 0 12px; color: var(--text-secondary); }
.step-dot {
  width: 28px; height: 28px; border-radius: 50%; border: 2px solid var(--border-color);
  display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; color: var(--text-secondary);
}
.step-item.active .step-dot { border-color: var(--accent); color: var(--accent); background: var(--accent-muted); }
.step-item.done .step-dot { border-color: var(--success); color: var(--success); background: rgba(16,185,129,0.1); }
.step-label { font-size: 13px; color: var(--text-secondary); }
.step-item.active .step-label { color: var(--text-primary); font-weight: 600; }

.dropzone {
  border: 2px dashed var(--border-color); border-radius: 16px; padding: 60px 40px;
  text-align: center; cursor: pointer; transition: all 0.2s; background: var(--bg-secondary);
  min-height: 280px; display: flex; align-items: center; justify-content: center;
}
.dropzone:hover, .dropzone.dragover { border-color: var(--accent); background: var(--accent-muted); }
.dropzone-icon { font-size: 56px; margin-bottom: 16px; }
.dropzone-main { font-size: 18px; font-weight: 600; color: var(--text-primary); margin: 0 0 8px; }
.dropzone-sub { font-size: 14px; color: var(--text-secondary); margin: 0 0 8px; }
.dropzone-hint { font-size: 12px; color: var(--text-secondary); }
.dropzone-loading { display: flex; flex-direction: column; align-items: center; gap: 12px; }
.spinner { width: 40px; height: 40px; border: 4px solid var(--border-color); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.error-banner { margin-top: 12px; padding: 10px 14px; background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); border-radius: 8px; color: var(--error); font-size: 13px; }

.preview-section { margin-bottom: 32px; }
.preview-meta { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.preview-badge { padding: 4px 10px; background: var(--bg-tertiary); border-radius: 6px; font-size: 12px; color: var(--text-secondary); }
.preview-count { font-size: 14px; font-weight: 600; color: var(--accent); }
.preview-table { width: 100%; border-collapse: collapse; font-size: 12px; background: var(--bg-card); border-radius: 8px; overflow: hidden; }
.preview-table th { padding: 8px 10px; background: var(--bg-secondary); color: var(--text-secondary); text-align: left; font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
.preview-table td { padding: 8px 10px; color: var(--text-primary); border-top: 1px solid var(--border-color); }
.tc-id { color: var(--text-secondary); font-size: 11px; }
.tc-folder { color: var(--text-secondary); font-family: monospace; }
.tc-title { max-width: 200px; }
.priority-badge { padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; text-transform: uppercase; }
.priority-badge.high { background: rgba(249,115,22,0.15); color: #f97316; }
.priority-badge.medium { background: rgba(245,158,11,0.15); color: #f59e0b; }
.priority-badge.low { background: rgba(107,114,128,0.15); color: #6b7280; }
.status-badge-sm { padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; text-transform: uppercase; }
.status-badge-sm.ready { background: rgba(16,185,129,0.15); color: var(--success); }
.status-badge-sm.draft { background: rgba(107,114,128,0.15); color: var(--text-secondary); }
.status-badge-sm.needs_work { background: rgba(239,68,68,0.15); color: var(--error); }

.project-section { margin-bottom: 32px; }
.section-title { font-size: 16px; font-weight: 600; color: var(--text-primary); margin: 0 0 16px; }
.radio-group { display: flex; gap: 20px; margin-bottom: 16px; }
.radio-label { display: flex; align-items: center; gap: 6px; font-size: 14px; color: var(--text-primary); cursor: pointer; }
.new-project-form, .existing-project-form { display: flex; flex-direction: column; gap: 12px; padding: 16px; background: var(--bg-secondary); border-radius: 8px; }
.form-row { display: flex; flex-direction: column; gap: 4px; }
.form-row label { font-size: 12px; color: var(--text-secondary); }
.form-input { padding: 8px 12px; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary); font-size: 14px; outline: none; }
.form-input:focus { border-color: var(--accent); }
.prefix-input { width: 100px; text-transform: uppercase; }

.import-actions { display: flex; gap: 12px; justify-content: flex-end; }
.btn-primary { padding: 10px 24px; background: var(--accent); border: none; border-radius: 8px; color: white; font-size: 14px; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }
.btn-primary:hover:not(:disabled) { opacity: 0.85; }
.btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-secondary { padding: 10px 20px; background: none; border: 1px solid var(--border-color); border-radius: 8px; color: var(--text-secondary); font-size: 14px; cursor: pointer; }
.btn-secondary:hover { color: var(--text-primary); }

.import-progress { text-align: center; padding-top: 40px; }
.progress-title { font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 32px; }
.progress-bar-wrap { height: 10px; background: var(--bg-tertiary); border-radius: 5px; overflow: hidden; margin: 0 auto 12px; max-width: 500px; }
.progress-bar { height: 100%; background: var(--accent); border-radius: 5px; transition: width 0.5s ease; }
.progress-pct { font-size: 20px; font-weight: 700; color: var(--accent); margin-bottom: 32px; }
.progress-counters { display: flex; justify-content: center; gap: 48px; margin-bottom: 24px; }
.counter-item { text-align: center; }
.counter-value { font-size: 28px; font-weight: 700; color: var(--text-primary); }
.counter-label { font-size: 12px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }
.progress-hint { font-size: 13px; color: var(--text-secondary); }

.import-result { text-align: center; padding-top: 40px; }
.result-title { font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 32px; }
.result-stats { display: flex; justify-content: center; gap: 40px; margin-bottom: 32px; flex-wrap: wrap; }
.stat-item { text-align: center; }
.stat-value { font-size: 36px; font-weight: 700; color: var(--text-primary); }
.stat-item.success .stat-value { color: var(--success); }
.stat-label { font-size: 12px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }
.error-list { text-align: left; padding: 16px; background: rgba(239,68,68,0.06); border-radius: 8px; margin-bottom: 24px; max-width: 500px; margin-left: auto; margin-right: auto; }
.error-list h4 { margin: 0 0 8px; font-size: 13px; color: var(--error); }
.error-item { font-size: 12px; color: var(--text-secondary); font-family: monospace; padding: 2px 0; }
.error-more { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }
.error-text { color: var(--error); font-size: 14px; margin-bottom: 20px; }
.result-actions { display: flex; justify-content: center; gap: 12px; flex-wrap: wrap; }
.import-body { max-width: 760px; }
</style>
