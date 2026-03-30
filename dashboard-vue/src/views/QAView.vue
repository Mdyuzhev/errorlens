<template>
  <div class="qa-page">
    <!-- Topbar -->
    <div class="qa-topbar">
      <h1 class="qa-title">{{ t('qa.title') }}</h1>
      <button class="btn-new-case" @click="showCreateModal = true">{{ t('qa.newCase') }}</button>
    </div>

    <!-- Tab nav -->
    <nav class="qa-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="qa-tab"
        :class="{ active: activeTab === tab.key }"
        @click="switchTab(tab.key)"
      >
        {{ tab.label }}
      </button>
    </nav>

    <!-- Content -->
    <div class="qa-content">
      <QATree
        v-if="activeTab === 'tree' && projectId"
        :project-id="projectId"
        @open-case="openCase"
      />
      <component
        v-else-if="activeTab === 'plans'"
        :is="QAPlans"
        :project-id="projectId"
      />
      <component
        v-else-if="activeTab === 'runs'"
        :is="QARuns"
        :project-id="projectId"
      />
      <component
        v-else-if="activeTab === 'dashboard'"
        :is="QADashboard"
        :project-id="projectId"
      />
      <component
        v-else-if="activeTab === 'sessions'"
        :is="SessionsTab"
      />
      <component
        v-else-if="activeTab === 'results'"
        :is="ResultsTab"
      />
      <component
        v-else-if="activeTab === 'generator'"
        :is="GeneratorTab"
        :project-id="projectId"
      />
      <component
        v-else-if="activeTab === 'coverage'"
        :is="QACoverage"
        :project-id="projectId"
        @open-case="openCase"
      />
    </div>

    <!-- TestCase Viewer -->
    <QATestCaseViewer
      v-if="viewingTestCase"
      :test-case="viewingTestCase"
      @close="closeViewer"
      @save="saveTestCase"
      @delete="deleteTestCase"
    />

    <!-- Create modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal-box">
        <h2 class="modal-title">New Test Case</h2>
        <label class="modal-label">Title</label>
        <input
          v-model="newCase.title"
          class="modal-input"
          placeholder="Test case title"
          @keydown.enter="createCase"
        />
        <label class="modal-label">Priority</label>
        <select v-model="newCase.priority" class="modal-select">
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
        <div class="modal-actions">
          <button class="btn-cancel" @click="showCreateModal = false">Cancel</button>
          <button class="btn-create" @click="createCase" :disabled="!newCase.title.trim()">Create</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed, defineAsyncComponent } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQAStore } from '@/stores/qa'
import { useLocaleStore } from '@/stores/locale'
import { projectsApi } from '@/services/api'
import QATree from '@/components/qa/QATree.vue'
import QATestCaseViewer from '@/components/qa/QATestCaseViewer.vue'

const QAPlans      = defineAsyncComponent(() => import('@/components/qa/QAPlans.vue'))
const QARuns       = defineAsyncComponent(() => import('@/components/qa/QARuns.vue'))
const QADashboard  = defineAsyncComponent(() => import('@/components/qa/QADashboard.vue'))
const SessionsTab  = defineAsyncComponent(() => import('@/views/DashboardView.vue'))
const ResultsTab   = defineAsyncComponent(() => import('@/views/ResultsView.vue'))
const GeneratorTab = defineAsyncComponent(() => import('@/components/qa/SpecGeneratorTab.vue'))
const QACoverage   = defineAsyncComponent(() => import('@/components/qa/QACoverage.vue'))

const route = useRoute()
const router = useRouter()
const store = useQAStore()
const localeStore = useLocaleStore()
function t(key) { return localeStore.t(key) }

const tabs = computed(() => [
  { key: 'tree',      label: t('qa.tabs.tree') },
  { key: 'plans',     label: t('qa.tabs.plans') },
  { key: 'runs',      label: t('qa.tabs.runs') },
  { key: 'dashboard', label: t('qa.tabs.dashboard') },
  { key: 'sessions',  label: t('qa.tabs.sessions') },
  { key: 'results',   label: t('qa.tabs.results') },
  { key: 'generator', label: t('qa.tabs.generator') },
  { key: 'coverage', label: t('qa.tabs.coverage') },
])

const activeTab = ref('tree')
const projectId = ref(null)
const viewingTestCase = ref(null)
const showCreateModal = ref(false)
const newCase = ref({ title: '', priority: 'medium' })

onMounted(async () => {
  if (route.query.tab && tabs.value.some(tab => tab.key === route.query.tab)) {
    activeTab.value = route.query.tab
  }
  try {
    const res = await projectsApi.list()
    const projects = res.data
    if (projects.length > 0) {
      projectId.value = projects[0].id
    }
  } catch {
    // no projects
  }

  if (route.query.open) {
    openCase(route.query.open)
  }

  if (route.query.tcId) {
    activeTab.value = 'tree'
    openCase(route.query.tcId)
  }
})

// Handle tcId query param for navigation from issue/task views
watch(() => route.query.tcId, async (tcId) => {
  if (!tcId) return
  activeTab.value = 'tree'
  await openCase(tcId)
}, { immediate: false })

function switchTab(key) {
  activeTab.value = key
  store.activeTab = key
  router.replace({ query: { ...route.query, tab: key } })
}

async function openCase(id) {
  const tc = await store.fetchTestCase(id)
  if (tc) viewingTestCase.value = tc
}

function closeViewer() {
  viewingTestCase.value = null
}

async function saveTestCase(formData) {
  if (!viewingTestCase.value) return
  const ok = await store.updateTestCase(viewingTestCase.value.id, formData)
  if (ok) {
    viewingTestCase.value = null
    await store.fetchTestCases()
  }
}

async function deleteTestCase(id) {
  if (!confirm('Удалить тест-кейс?')) return
  const ok = await store.deleteTestCase(id)
  if (ok) viewingTestCase.value = null
}

async function createCase() {
  if (!newCase.value.title.trim()) return
  const data = {
    title: newCase.value.title.trim(),
    priority: newCase.value.priority,
    project_id: projectId.value,
  }
  const ok = await store.createTestCase(data)
  if (ok) {
    showCreateModal.value = false
    newCase.value = { title: '', priority: 'medium' }
  }
}
</script>

<style scoped>
.qa-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.qa-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 46px;
  min-height: 46px;
  padding: 0 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.qa-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary);
}

.btn-new-case {
  padding: 6px 16px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.15s;
}
.btn-new-case:hover {
  opacity: 0.85;
}

.qa-tabs {
  display: flex;
  gap: 0;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  padding: 0 20px;
  overflow-x: auto;
}

.qa-tab {
  padding: 10px 18px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}
.qa-tab:hover {
  color: var(--text-primary);
}
.qa-tab.active {
  color: var(--text-primary);
  border-bottom-color: var(--accent);
}

.qa-content {
  flex: 1;
  overflow-y: auto;
  background: var(--bg-primary);
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.modal-box {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 24px;
  width: 400px;
  max-width: 90vw;
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px;
  color: var(--text-primary);
}

.modal-label {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 6px;
  margin-top: 12px;
}

.modal-input,
.modal-select {
  width: 100%;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
}
.modal-input:focus,
.modal-select:focus {
  border-color: var(--accent);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}

.btn-cancel {
  padding: 7px 16px;
  background: none;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
}
.btn-cancel:hover {
  color: var(--text-primary);
}

.btn-create {
  padding: 7px 16px;
  background: var(--accent);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
.btn-create:hover {
  opacity: 0.85;
}
.btn-create:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
