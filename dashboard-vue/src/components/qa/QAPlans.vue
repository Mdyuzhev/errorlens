<template>
  <div class="qa-plans">
    <!-- Detail View -->
    <div v-if="selectedPlan" class="plan-detail">
      <button class="back-btn" @click="selectedPlan = null">
        <span class="back-arrow">&#8592;</span> Back to Plans
      </button>

      <div class="plan-header">
        <h3 class="plan-name">{{ selectedPlan.name }}</h3>
        <span class="status-badge" :class="selectedPlan.status">
          {{ selectedPlan.status }}
        </span>
      </div>

      <div class="plan-actions">
        <button class="action-btn" @click="showAddCases = true">Add Cases</button>
        <button class="action-btn accent" @click="startRun">Start Run</button>
      </div>

      <!-- Cases list with drag reorder -->
      <div class="cases-section">
        <h4 class="section-title">
          Test Cases ({{ planCases.length }})
        </h4>
        <div
          v-for="(tc, idx) in planCases"
          :key="tc.id"
          class="case-row"
          draggable="true"
          @dragstart="onDragStart(idx)"
          @dragover.prevent="onDragOver(idx)"
          @drop="onDrop(idx)"
        >
          <span class="drag-handle">&#9776;</span>
          <span class="case-title">{{ tc.title || tc.name }}</span>
          <button class="remove-btn" @click="removeCase(tc.id)">&#215;</button>
        </div>
        <div v-if="!planCases.length" class="empty-cases">
          No cases added yet
        </div>
      </div>

      <!-- Runs Matrix -->
      <div class="matrix-section" v-if="planCases.length && store.planRuns.length">
        <h4 class="section-title">Runs Matrix</h4>
        <RunsMatrix :cases="planCases" :runs="store.planRuns" />
      </div>

      <!-- Past runs list -->
      <div class="past-runs" v-if="store.planRuns.length">
        <h4 class="section-title">Past Runs</h4>
        <div
          v-for="run in store.planRuns"
          :key="run.id"
          class="run-row"
        >
          <span class="run-name">{{ run.name || `Run #${run.id}` }}</span>
          <span class="run-date">{{ formatDate(run.created_at) }}</span>
          <span class="run-badge" :class="run.status">{{ run.status }}</span>
        </div>
      </div>

      <!-- Add Cases Modal -->
      <div v-if="showAddCases" class="modal-overlay" @click.self="showAddCases = false">
        <div class="modal-box">
          <h4 class="modal-title">Add Test Cases</h4>
          <div class="modal-body">
            <div
              v-for="tc in availableCases"
              :key="tc.id"
              class="modal-row"
              @click="toggleAdd(tc.id)"
            >
              <input
                type="checkbox"
                :checked="addIds.has(tc.id)"
                @click.stop="toggleAdd(tc.id)"
              />
              <span>{{ tc.title || tc.name }}</span>
            </div>
            <div v-if="!availableCases.length" class="empty-cases">
              No more cases to add
            </div>
          </div>
          <div class="modal-footer">
            <button class="action-btn" @click="showAddCases = false">Cancel</button>
            <button class="action-btn accent" @click="confirmAdd">
              Add ({{ addIds.size }})
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- List View -->
    <div v-else>
      <h3 class="plans-title">Test Plans</h3>

      <div v-if="store.loading" class="plans-loading">Loading...</div>

      <div v-else-if="!store.plans.length" class="plans-empty">
        No test plans found
      </div>

      <div v-else class="plans-list">
        <div
          v-for="plan in store.plans"
          :key="plan.id"
          class="plan-row"
          @click="selectPlan(plan)"
        >
          <div class="plan-info">
            <span class="plan-row-name">{{ plan.name }}</span>
            <span class="plan-badge" :class="plan.status">{{ plan.status }}</span>
          </div>
          <div class="plan-stats">
            <span class="stat">{{ plan.cases_count || 0 }} cases</span>
            <span class="stat">{{ plan.runs_count || 0 }} runs</span>
            <span class="stat accent">{{ passPercent(plan) }}% passed</span>
          </div>
          <span class="plan-date">{{ formatDate(plan.created_at) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useQAStore } from '@/stores/qa'
import { testPlansApi } from '@/services/api'
import RunsMatrix from './RunsMatrix.vue'

const props = defineProps({
  projectId: { type: String, required: true }
})

const store = useQAStore()
const selectedPlan = ref(null)
const showAddCases = ref(false)
const addIds = reactive(new Set())
let dragIdx = null

const planCases = computed(() => selectedPlan.value?.cases || [])

const availableCases = computed(() => {
  const existing = new Set(planCases.value.map(c => c.id))
  return store.testCases.filter(tc => !existing.has(tc.id))
})

onMounted(() => {
  store.fetchPlans(props.projectId)
  store.fetchTestCases()
})

async function selectPlan(plan) {
  const full = await store.fetchPlan(plan.id)
  if (full) {
    selectedPlan.value = full
    store.fetchPlanRuns(plan.id)
  }
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString()
}

function passPercent(plan) {
  if (!plan.pass_rate && plan.pass_rate !== 0) return 0
  return Math.round(plan.pass_rate * 100)
}

async function startRun() {
  if (!selectedPlan.value) return
  try {
    await testPlansApi.startRun(selectedPlan.value.id, {
      name: `Run ${new Date().toLocaleDateString()}`
    })
    await store.fetchPlanRuns(selectedPlan.value.id)
  } catch { /* handled by store */ }
}

async function removeCase(tcId) {
  if (!selectedPlan.value) return
  try {
    await testPlansApi.removeCase(selectedPlan.value.id, tcId)
    const refreshed = await store.fetchPlan(selectedPlan.value.id)
    if (refreshed) selectedPlan.value = refreshed
  } catch { /* handled */ }
}

function toggleAdd(id) {
  if (addIds.has(id)) addIds.delete(id)
  else addIds.add(id)
}

async function confirmAdd() {
  if (!addIds.size || !selectedPlan.value) return
  await store.addCasesToPlan(selectedPlan.value.id, [...addIds])
  selectedPlan.value = store.currentPlan
  addIds.clear()
  showAddCases.value = false
}

function onDragStart(idx) {
  dragIdx = idx
}

function onDragOver(idx) {
  /* allow drop */
}

async function onDrop(idx) {
  if (dragIdx === null || dragIdx === idx) return
  const cases = [...planCases.value]
  const [moved] = cases.splice(dragIdx, 1)
  cases.splice(idx, 0, moved)
  dragIdx = null

  const orderedIds = cases.map(c => c.id)
  try {
    await testPlansApi.reorderCases(selectedPlan.value.id, orderedIds)
    const refreshed = await store.fetchPlan(selectedPlan.value.id)
    if (refreshed) selectedPlan.value = refreshed
  } catch { /* handled */ }
}
</script>

<style scoped>
.qa-plans { padding: 0; }
.plans-title { color: var(--text-primary); font-size: 16px; font-weight: 600; margin: 0 0 16px 0; }
.plans-loading, .plans-empty, .empty-cases { color: var(--text-secondary); text-align: center; padding: 32px; font-size: 13px; }
.empty-cases { padding: 16px; }
.plans-list { display: flex; flex-direction: column; gap: 2px; }
.plan-row, .run-row, .case-row { display: flex; align-items: center; border-bottom: 1px solid var(--border-color); }
.plan-row { gap: 16px; padding: 12px 16px; border-radius: 6px; cursor: pointer; transition: background 0.15s; }
.plan-row:hover, .run-row:hover, .case-row:hover, .modal-row:hover { background: var(--bg-tertiary); }
.plan-info { flex: 1; display: flex; align-items: center; gap: 8px; min-width: 0; }
.plan-row-name { color: var(--text-primary); font-size: 14px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.plan-badge, .status-badge, .run-badge { font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 500; text-transform: capitalize; }
.plan-badge.draft, .status-badge.draft { color: #6b7280; background: rgba(107,114,128,0.12); }
.plan-badge.ready, .status-badge.ready, .plan-badge.active, .status-badge.active { color: #10b981; background: rgba(16,185,129,0.12); }
.plan-badge.approved, .status-badge.approved { color: var(--accent); background: rgba(155,125,224,0.12); }
.plan-badge.completed, .status-badge.completed { color: #3b82f6; background: rgba(59,130,246,0.12); }
.plan-stats { display: flex; gap: 12px; }
.stat { color: var(--text-secondary); font-size: 12px; }
.stat.accent { color: var(--accent); font-weight: 500; }
.plan-date { color: var(--text-secondary); font-size: 12px; white-space: nowrap; }
.back-btn { background: none; border: none; color: var(--accent); cursor: pointer; font-size: 13px; padding: 4px 0; margin-bottom: 12px; }
.back-btn:hover { color: var(--accent-hover); }
.back-arrow { margin-right: 4px; }
.plan-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.plan-name { color: var(--text-primary); font-size: 18px; font-weight: 600; margin: 0; }
.plan-actions { display: flex; gap: 8px; margin-bottom: 20px; }
.action-btn { padding: 6px 14px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-secondary); color: var(--text-primary); font-size: 13px; cursor: pointer; transition: background 0.15s; }
.action-btn:hover { background: var(--bg-tertiary); }
.action-btn.accent { background: var(--accent); border-color: var(--accent); color: #fff; }
.action-btn.accent:hover { background: var(--accent-hover); }
.section-title { color: var(--text-secondary); font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; margin: 0 0 10px 0; }
.cases-section, .matrix-section, .past-runs { margin-bottom: 24px; }
.case-row { gap: 8px; padding: 8px 12px; cursor: grab; }
.drag-handle { color: var(--text-secondary); font-size: 14px; cursor: grab; user-select: none; }
.case-title { flex: 1; color: var(--text-primary); font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.remove-btn { background: none; border: none; color: #ef4444; cursor: pointer; font-size: 16px; padding: 0 4px; opacity: 0.6; }
.remove-btn:hover { opacity: 1; }
.run-row { gap: 12px; padding: 8px 12px; }
.run-name { color: var(--text-primary); font-size: 13px; flex: 1; }
.run-date { color: var(--text-secondary); font-size: 12px; }
.run-badge.completed, .run-badge.finished { color: #10b981; background: rgba(16,185,129,0.12); }
.run-badge.in_progress, .run-badge.active { color: #3b82f6; background: rgba(59,130,246,0.12); }
.run-badge.aborted { color: #ef4444; background: rgba(239,68,68,0.12); }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal-box { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 10px; width: 480px; max-height: 70vh; display: flex; flex-direction: column; }
.modal-title { color: var(--text-primary); font-size: 15px; font-weight: 600; padding: 16px 20px; margin: 0; border-bottom: 1px solid var(--border-color); }
.modal-body { padding: 12px 20px; overflow-y: auto; flex: 1; }
.modal-row { display: flex; align-items: center; gap: 10px; padding: 8px 4px; color: var(--text-primary); font-size: 13px; cursor: pointer; border-radius: 4px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; padding: 12px 20px; border-top: 1px solid var(--border-color); }
</style>
