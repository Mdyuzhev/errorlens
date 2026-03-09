<template>
  <div class="test-plans-page">
    <!-- List mode -->
    <div v-if="currentView === 'list'" class="plans-list-view">
      <div class="list-header">
        <h2>Test Plans</h2>
        <button class="btn-create" @click="showCreateModal = true">+ New Plan</button>
      </div>

      <div v-if="store.loading" class="loading-state">Loading...</div>
      <div v-else-if="store.plans.length === 0" class="empty-state">
        No test plans yet. Create one to get started.
      </div>
      <div v-else class="plans-list" data-testid="plans-list">
        <div
          v-for="plan in store.plans"
          :key="plan.id"
          class="plan-row"
          @click="openPlan(plan)"
        >
          <span class="row-icon">📋</span>
          <span v-if="plan.human_id" class="human-id-badge">{{ plan.human_id }}</span>
          <span class="row-title">{{ plan.name }}</span>
          <span class="row-status" :class="plan.status">{{ plan.status }}</span>
          <span class="row-stat">{{ plan.cases_count }} cases</span>
          <span class="row-stat">{{ plan.runs_count }} runs</span>
          <span v-if="plan.last_run_passed_pct !== null" class="row-pct">
            {{ plan.last_run_passed_pct }}% passed
          </span>
          <span class="row-date">{{ formatDate(plan.created_at) }}</span>
        </div>
      </div>
    </div>

    <!-- Detail mode -->
    <div v-if="currentView === 'detail' && store.currentPlan" class="plan-detail-view">
      <div class="detail-layout">
        <!-- Left panel: plan info + cases -->
        <div class="detail-left">
          <div class="detail-header">
            <button class="btn-back" @click="goBackToList">&larr; Back</button>
            <div class="detail-title-row">
              <span v-if="store.currentPlan.human_id" class="human-id-badge">{{ store.currentPlan.human_id }}</span>
              <h2>{{ store.currentPlan.name }}</h2>
              <span class="row-status" :class="store.currentPlan.status">{{ store.currentPlan.status }}</span>
            </div>
            <p v-if="store.currentPlan.description" class="detail-desc">{{ store.currentPlan.description }}</p>
            <div class="detail-actions">
              <button class="btn-secondary" @click="showEditModal = true">Edit Plan</button>
              <button class="btn-secondary" @click="showPicker = true">Add Cases</button>
              <button class="btn-danger" @click="confirmDeletePlan">Delete</button>
            </div>
          </div>

          <div class="cases-section">
            <h3>Test Cases ({{ store.currentPlan.cases?.length || 0 }})</h3>
            <div v-if="!store.currentPlan.cases?.length" class="empty-state">
              No test cases added yet.
            </div>
            <div v-else class="cases-list" data-testid="plan-cases">
              <div
                v-for="c in store.currentPlan.cases"
                :key="c.testcase_id"
                class="case-row"
              >
                <span v-if="c.human_id" class="human-id-badge">{{ c.human_id }}</span>
                <span class="case-title">{{ c.title }}</span>
                <span class="tc-priority" :class="c.priority?.toLowerCase()">{{ c.priority }}</span>
                <button class="btn-remove" @click.stop="removeCaseFromPlan(c.testcase_id)">&times;</button>
              </div>
            </div>
          </div>

          <div class="run-actions">
            <button class="btn-primary" @click="promptStartRun">+ Start Run</button>
          </div>
        </div>

        <!-- Right panel: runs history -->
        <div class="detail-right">
          <h3>Runs History</h3>
          <div v-if="store.runs.length === 0" class="empty-state">No runs yet.</div>
          <div v-else class="runs-list">
            <div
              v-for="run in store.runs"
              :key="run.id"
              class="run-row"
              @click="openRun(run)"
            >
              <div class="run-info">
                <span class="run-name">{{ run.name }}</span>
                <span class="run-date">{{ formatDate(run.started_at) }}</span>
              </div>
              <span class="row-status" :class="run.status">{{ run.status }}</span>
              <div class="run-counters">
                <span class="counter passed" v-if="run.passed">{{ run.passed }} passed</span>
                <span class="counter failed" v-if="run.failed">{{ run.failed }} failed</span>
                <span class="counter blocked" v-if="run.blocked">{{ run.blocked }} blocked</span>
                <span class="counter skipped" v-if="run.skipped">{{ run.skipped }} skipped</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit modal -->
    <div v-if="showCreateModal || showEditModal" class="modal-overlay" @click.self="closeModals">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ showEditModal ? 'Edit Plan' : 'New Test Plan' }}</h3>
          <button class="modal-close" @click="closeModals">&times;</button>
        </div>
        <div class="modal-body">
          <label>Name</label>
          <input v-model="form.name" type="text" class="form-input" placeholder="Plan name" />
          <label>Description</label>
          <textarea v-model="form.description" class="form-textarea" rows="3" placeholder="Optional description"></textarea>
          <label>Status</label>
          <select v-model="form.status" class="form-input">
            <option value="draft">Draft</option>
            <option value="active">Active</option>
            <option value="archived">Archived</option>
          </select>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="closeModals">Cancel</button>
          <button class="btn-primary" @click="savePlan">{{ showEditModal ? 'Save' : 'Create' }}</button>
        </div>
      </div>
    </div>

    <!-- Test Case Picker -->
    <TestCasePicker
      v-if="showPicker"
      :existingIds="existingCaseIds"
      @add="onAddCases"
      @close="showPicker = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTestPlansStore } from '@/stores/testPlans'
import TestCasePicker from '@/components/testplans/TestCasePicker.vue'

const route = useRoute()
const router = useRouter()
const store = useTestPlansStore()

const currentView = ref('list')
const showCreateModal = ref(false)
const showEditModal = ref(false)
const showPicker = ref(false)
const form = ref({ name: '', description: '', status: 'draft' })

const existingCaseIds = computed(() => {
  const ids = new Set()
  if (store.currentPlan?.cases) {
    store.currentPlan.cases.forEach(c => ids.add(c.testcase_id))
  }
  return ids
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString()
}

async function openPlan(plan) {
  currentView.value = 'detail'
  await store.fetchPlan(plan.id)
  await store.fetchRuns(plan.id)
}

function goBackToList() {
  currentView.value = 'list'
  store.currentPlan = null
  store.runs = []
}

function closeModals() {
  showCreateModal.value = false
  showEditModal.value = false
  form.value = { name: '', description: '', status: 'draft' }
}

async function savePlan() {
  if (!form.value.name.trim()) return
  if (showEditModal.value && store.currentPlan) {
    await store.updatePlan(store.currentPlan.id, form.value)
    await store.fetchPlan(store.currentPlan.id)
  } else {
    await store.createPlan(form.value)
  }
  closeModals()
}

function confirmDeletePlan() {
  if (confirm('Delete this plan?')) {
    store.deletePlan(store.currentPlan.id)
    goBackToList()
    store.fetchPlans()
  }
}

async function removeCaseFromPlan(testcaseId) {
  await store.removeCase(store.currentPlan.id, testcaseId)
}

async function onAddCases(ids) {
  showPicker.value = false
  if (ids.length > 0) {
    await store.addCases(store.currentPlan.id, ids)
  }
}

function promptStartRun() {
  const name = prompt('Run name:', `Run ${new Date().toLocaleDateString('ru-RU')}`)
  if (name) {
    startNewRun(name)
  }
}

async function startNewRun(name) {
  const run = await store.startRun(store.currentPlan.id, name)
  if (run) {
    router.push(`/test-plans/runs/${run.id}`)
  }
}

function openRun(run) {
  router.push(`/test-plans/runs/${run.id}`)
}

onMounted(() => {
  store.fetchPlans()

  // If editing plan
  if (store.currentPlan) {
    form.value = {
      name: store.currentPlan.name,
      description: store.currentPlan.description || '',
      status: store.currentPlan.status,
    }
  }
})

watch(showEditModal, (val) => {
  if (val && store.currentPlan) {
    form.value = {
      name: store.currentPlan.name,
      description: store.currentPlan.description || '',
      status: store.currentPlan.status,
    }
  }
})
</script>

<style scoped>
.test-plans-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.list-header h2 {
  color: var(--text-primary);
  margin: 0;
}

.btn-create {
  padding: 8px 16px;
  background: var(--accent);
  border: none;
  border-radius: 8px;
  color: white;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
}

.loading-state,
.empty-state {
  padding: 40px;
  text-align: center;
  color: var(--text-secondary);
}

.plans-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.plan-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-card);
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.plan-row:hover {
  background: var(--bg-secondary);
}

.row-icon {
  font-size: 18px;
}

.human-id-badge {
  flex-shrink: 0;
  padding: 2px 6px;
  background: rgba(99, 102, 241, 0.2);
  color: #818cf8;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.row-title {
  flex: 1;
  color: var(--text-primary);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row-status {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}
.row-status.draft { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
.row-status.active { background: rgba(16, 185, 129, 0.2); color: #10b981; }
.row-status.archived { background: rgba(107, 114, 128, 0.2); color: #6b7280; }
.row-status.in_progress { background: rgba(59, 130, 246, 0.2); color: #3b82f6; }
.row-status.completed { background: rgba(16, 185, 129, 0.2); color: #10b981; }

.row-stat {
  color: var(--text-secondary);
  font-size: 13px;
  white-space: nowrap;
}

.row-pct {
  color: #10b981;
  font-size: 13px;
  font-weight: 600;
}

.row-date {
  color: var(--text-secondary);
  font-size: 13px;
  white-space: nowrap;
}

/* Detail view */
.detail-layout {
  display: flex;
  gap: 24px;
}

.detail-left {
  flex: 1;
  min-width: 0;
}

.detail-right {
  width: 380px;
  flex-shrink: 0;
}

.detail-header {
  margin-bottom: 24px;
}

.btn-back {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px 0;
  margin-bottom: 8px;
  font-size: 14px;
}

.btn-back:hover {
  color: var(--text-primary);
}

.detail-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.detail-title-row h2 {
  margin: 0;
  color: var(--text-primary);
}

.detail-desc {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0 0 12px;
}

.detail-actions {
  display: flex;
  gap: 8px;
}

.btn-secondary {
  padding: 6px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  cursor: pointer;
  font-size: 13px;
}

.btn-danger {
  padding: 6px 12px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: #ef4444;
  cursor: pointer;
  font-size: 13px;
}

.btn-primary {
  padding: 8px 16px;
  background: var(--accent);
  border: none;
  border-radius: 8px;
  color: white;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
}

.cases-section {
  margin-bottom: 24px;
}

.cases-section h3 {
  color: var(--text-primary);
  margin: 0 0 12px;
}

.cases-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.case-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-card);
  border-radius: 6px;
}

.case-title {
  flex: 1;
  color: var(--text-primary);
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tc-priority {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}
.tc-priority.critical { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
.tc-priority.high { background: rgba(249, 115, 22, 0.2); color: #f97316; }
.tc-priority.medium { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
.tc-priority.low { background: rgba(107, 114, 128, 0.2); color: #6b7280; }

.btn-remove {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 18px;
  padding: 0 4px;
}
.btn-remove:hover { color: #ef4444; }

.run-actions {
  margin-top: 16px;
}

/* Runs */
.detail-right h3 {
  color: var(--text-primary);
  margin: 0 0 12px;
}

.runs-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.run-row {
  padding: 12px;
  background: var(--bg-card);
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}
.run-row:hover { background: var(--bg-secondary); }

.run-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}

.run-name {
  color: var(--text-primary);
  font-weight: 500;
  font-size: 14px;
}

.run-date {
  color: var(--text-secondary);
  font-size: 12px;
}

.run-counters {
  display: flex;
  gap: 8px;
  margin-top: 6px;
}

.counter {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}
.counter.passed { background: rgba(16, 185, 129, 0.2); color: #10b981; }
.counter.failed { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
.counter.blocked { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
.counter.skipped { background: rgba(107, 114, 128, 0.2); color: #6b7280; }

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-card);
  border-radius: 12px;
  width: 500px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  margin: 0;
  color: var(--text-primary);
}

.modal-close {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 24px;
  cursor: pointer;
}

.modal-body {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.modal-body label {
  color: var(--text-secondary);
  font-size: 13px;
}

.form-input,
.form-textarea {
  padding: 8px 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
  font-family: inherit;
}

.form-textarea {
  resize: vertical;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 20px;
  border-top: 1px solid var(--border-color);
}

.btn-cancel {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-secondary);
  cursor: pointer;
}
</style>
