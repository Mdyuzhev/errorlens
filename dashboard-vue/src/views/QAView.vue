<template>
  <div class="qa-page">
    <!-- Topbar -->
    <div class="qa-topbar">
      <h1 class="qa-title">QA</h1>
      <button class="btn-new-case" @click="showCreateModal = true">+ New Test Case</button>
    </div>

    <!-- Tab nav -->
    <nav class="qa-tabs">
      <button
        v-for="t in tabs"
        :key="t.key"
        class="qa-tab"
        :class="{ active: activeTab === t.key }"
        @click="switchTab(t.key)"
      >
        {{ t.label }}
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
    </div>

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
import { ref, onMounted, computed, watch, defineAsyncComponent } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQAStore } from '@/stores/qa'
import { projectsApi } from '@/services/api'
import QATree from '@/components/qa/QATree.vue'

const QAPlans = defineAsyncComponent(() => import('@/components/qa/QAPlans.vue'))
const QARuns = defineAsyncComponent(() => import('@/components/qa/QARuns.vue'))
const QADashboard = defineAsyncComponent(() => import('@/components/qa/QADashboard.vue'))

const route = useRoute()
const router = useRouter()
const store = useQAStore()

const tabs = [
  { key: 'tree', label: 'Tree' },
  { key: 'plans', label: 'Test Plans' },
  { key: 'runs', label: 'Runs' },
  { key: 'dashboard', label: 'Dashboard' },
]

const activeTab = ref('tree')
const projectId = ref(null)
const showCreateModal = ref(false)
const newCase = ref({ title: '', priority: 'medium' })

onMounted(async () => {
  if (route.query.tab && tabs.some(t => t.key === route.query.tab)) {
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
})

function switchTab(key) {
  activeTab.value = key
  store.activeTab = key
  router.replace({ query: { ...route.query, tab: key } })
}

function openCase(id) {
  store.fetchTestCase(id)
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
  background: #0f0e17;
  color: #e8e6f0;
}

.qa-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 46px;
  min-height: 46px;
  padding: 0 20px;
  background: #16152a;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
}

.qa-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: #e8e6f0;
}

.btn-new-case {
  padding: 6px 16px;
  background: #7c5cbf;
  color: #e8e6f0;
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
  background: #16152a;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  padding: 0 20px;
}

.qa-tab {
  padding: 10px 18px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: #7a788a;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}
.qa-tab:hover {
  color: #e8e6f0;
}
.qa-tab.active {
  color: #e8e6f0;
  border-bottom-color: #7c5cbf;
}

.qa-content {
  flex: 1;
  overflow-y: auto;
  background: #0f0e17;
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
  background: #16152a;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  padding: 24px;
  width: 400px;
  max-width: 90vw;
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px;
  color: #e8e6f0;
}

.modal-label {
  display: block;
  font-size: 12px;
  color: #7a788a;
  margin-bottom: 6px;
  margin-top: 12px;
}

.modal-input,
.modal-select {
  width: 100%;
  padding: 8px 12px;
  background: #22203a;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 6px;
  color: #e8e6f0;
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
}
.modal-input:focus,
.modal-select:focus {
  border-color: #7c5cbf;
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
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 6px;
  color: #7a788a;
  font-size: 13px;
  cursor: pointer;
}
.btn-cancel:hover {
  color: #e8e6f0;
}

.btn-create {
  padding: 7px 16px;
  background: #7c5cbf;
  border: none;
  border-radius: 6px;
  color: #e8e6f0;
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
