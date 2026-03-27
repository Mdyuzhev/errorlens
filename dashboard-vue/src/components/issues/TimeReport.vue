<template>
  <div class="time-report">
    <!-- Toolbar -->
    <div class="tr-toolbar">
      <div class="tr-filters">
        <label class="tr-label">From</label>
        <input v-model="dateFrom" type="date" class="tr-input" />
        <label class="tr-label">To</label>
        <input v-model="dateTo" type="date" class="tr-input" />
        <button class="tr-btn" @click="resetDates">All time</button>
      </div>
      <div class="tr-summary">
        <span class="tr-total">Total: <strong>{{ totalHours }}h</strong></span>
        <span class="tr-entries">{{ totalEntries }} entries</span>
      </div>
      <button class="tr-btn tr-btn-accent" @click="showLogModal = true">+ Log Work</button>
    </div>

    <!-- Loading -->
    <div v-if="store.projectWorkLogsLoading" class="tr-loading">Loading...</div>

    <!-- Table -->
    <table v-else-if="groupedUsers.length" class="tr-table">
      <thead>
        <tr>
          <th class="th-user">User</th>
          <th class="th-hours">Total Hours</th>
          <th class="th-count">Entries</th>
          <th class="th-toggle"></th>
        </tr>
      </thead>
      <tbody v-for="user in groupedUsers" :key="user.userId">
        <tr class="tr-user-row" @click="toggleUser(user.userId)">
          <td class="td-user">
            <span class="tr-avatar">{{ user.initials }}</span>
            <span>{{ user.name }}</span>
          </td>
          <td class="td-hours">
            <div class="tr-bar-wrap">
              <div class="tr-bar" :style="{ width: barWidth(user.total) }"></div>
            </div>
            <span>{{ user.total }}h</span>
          </td>
          <td class="td-count">{{ user.entries.length }}</td>
          <td class="td-toggle">{{ expanded[user.userId] ? '\u25B2' : '\u25BC' }}</td>
        </tr>
        <template v-if="expanded[user.userId]">
          <tr v-for="entry in user.entries" :key="entry.id" class="tr-detail-row">
            <td class="td-detail-task" colspan="1">
              <span class="tr-human-id">{{ entry.task_human_id || '---' }}</span>
              <span class="tr-task-title">{{ entry.task_title || '' }}</span>
            </td>
            <td>{{ entry.hours }}h</td>
            <td>{{ formatDate(entry.logged_at || entry.created_at) }}</td>
            <td class="td-comment">{{ entry.comment || '' }}</td>
          </tr>
        </template>
      </tbody>
      <tfoot>
        <tr class="tr-footer">
          <td><strong>Total</strong></td>
          <td><strong>{{ totalHours }}h</strong></td>
          <td><strong>{{ totalEntries }}</strong></td>
          <td></td>
        </tr>
      </tfoot>
    </table>

    <div v-else class="tr-empty">No work logs found for this period.</div>

    <!-- Log Work Modal -->
    <teleport to="body">
      <div v-if="showLogModal" class="tr-overlay" @click.self="showLogModal = false">
        <div class="tr-modal">
          <h3>Log Work</h3>
          <div class="tr-field">
            <label>Issue</label>
            <input
              v-model="searchQuery"
              placeholder="Search by title or ID..."
              class="tr-input tr-input-full"
              @input="searchIssues"
            />
            <div v-if="searchResults.length" class="tr-search-results">
              <div
                v-for="t in searchResults"
                :key="t.id"
                class="tr-search-item"
                @click="selectIssue(t)"
              >
                <span class="tr-human-id">{{ t.human_id }}</span> {{ t.title }}
              </div>
            </div>
            <div v-if="selectedIssue" class="tr-selected-issue">
              {{ selectedIssue.human_id }} — {{ selectedIssue.title }}
              <button class="tr-btn-x" @click="selectedIssue = null">&times;</button>
            </div>
          </div>
          <div class="tr-field">
            <label>Hours</label>
            <input v-model.number="logForm.hours" type="number" step="0.25" min="0.25" class="tr-input tr-input-full" />
          </div>
          <div class="tr-field">
            <label>Date</label>
            <input v-model="logForm.log_date" type="date" class="tr-input tr-input-full" />
          </div>
          <div class="tr-field">
            <label>Comment</label>
            <input v-model="logForm.comment" placeholder="Optional comment" class="tr-input tr-input-full" />
          </div>
          <div class="tr-modal-actions">
            <button class="tr-btn tr-btn-accent" :disabled="!canSubmit" @click="submitLog">Save</button>
            <button class="tr-btn" @click="showLogModal = false">Cancel</button>
          </div>
        </div>
      </div>
    </teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useIssuesStore } from '@/stores/issues'
import { tasksApi } from '@/services/api'

const props = defineProps({
  projectId: { type: String, required: true },
})

const store = useIssuesStore()

const dateFrom = ref('')
const dateTo = ref('')
const expanded = ref({})
const showLogModal = ref(false)
const searchQuery = ref('')
const searchResults = ref([])
const selectedIssue = ref(null)
const logForm = ref({
  hours: '',
  log_date: new Date().toISOString().slice(0, 10),
  comment: '',
})

const canSubmit = computed(() => selectedIssue.value && logForm.value.hours > 0)

function buildParams() {
  const p = {}
  if (dateFrom.value) p.date_from = dateFrom.value
  if (dateTo.value) p.date_to = dateTo.value
  return p
}

function loadData() {
  store.fetchProjectWorkLogs(props.projectId, buildParams())
}

onMounted(loadData)
watch([dateFrom, dateTo], loadData)
watch(() => props.projectId, loadData)

function resetDates() {
  dateFrom.value = ''
  dateTo.value = ''
}

const groupedUsers = computed(() => {
  const map = {}
  for (const log of store.projectWorkLogs) {
    const uid = log.user_id || log.user?.id || 'unknown'
    if (!map[uid]) {
      const name = log.user?.display_name || log.user?.username || 'Unknown'
      const initials = name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
      map[uid] = { userId: uid, name, initials, total: 0, entries: [] }
    }
    map[uid].total = Math.round((map[uid].total + (log.hours || 0)) * 100) / 100
    map[uid].entries.push(log)
  }
  return Object.values(map).sort((a, b) => b.total - a.total)
})

const totalHours = computed(() => {
  return Math.round(groupedUsers.value.reduce((s, u) => s + u.total, 0) * 100) / 100
})

const totalEntries = computed(() => {
  return groupedUsers.value.reduce((s, u) => s + u.entries.length, 0)
})

const maxUserHours = computed(() => {
  return Math.max(...groupedUsers.value.map(u => u.total), 1)
})

function barWidth(hours) {
  return Math.round((hours / maxUserHours.value) * 100) + '%'
}

function toggleUser(uid) {
  expanded.value[uid] = !expanded.value[uid]
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString()
}

let searchTimeout = null
function searchIssues() {
  clearTimeout(searchTimeout)
  if (!searchQuery.value || searchQuery.value.length < 2) {
    searchResults.value = []
    return
  }
  searchTimeout = setTimeout(async () => {
    try {
      const r = await tasksApi.list({ project_id: props.projectId, search: searchQuery.value, limit: 10 })
      searchResults.value = r.data?.items || r.data || []
    } catch (e) {
      searchResults.value = []
    }
  }, 300)
}

function selectIssue(t) {
  selectedIssue.value = t
  searchQuery.value = ''
  searchResults.value = []
}

async function submitLog() {
  if (!canSubmit.value) return
  const ok = await store.createWorkLogGlobal({
    issue_id: selectedIssue.value.id,
    hours: logForm.value.hours,
    log_date: logForm.value.log_date,
    comment: logForm.value.comment || null,
  })
  if (ok) {
    showLogModal.value = false
    selectedIssue.value = null
    logForm.value = { hours: '', log_date: new Date().toISOString().slice(0, 10), comment: '' }
    loadData()
  }
}
</script>

<style scoped>
.time-report {
  padding: 16px;
}

.tr-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.tr-filters {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tr-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.tr-input {
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 13px;
}

.tr-input-full {
  width: 100%;
}

.tr-summary {
  margin-left: auto;
  display: flex;
  gap: 12px;
  font-size: 13px;
  color: var(--text-secondary);
}

.tr-total strong {
  color: var(--text-primary);
}

.tr-btn {
  padding: 6px 14px;
  font-size: 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.tr-btn:hover {
  background: var(--bg-tertiary);
}

.tr-btn-accent {
  background: var(--accent);
  color: var(--text-primary);
  border-color: var(--accent);
}

.tr-btn-accent:hover {
  background: var(--accent-hover);
}

.tr-btn-accent:disabled {
  opacity: 0.5;
  cursor: default;
}

.tr-loading {
  text-align: center;
  padding: 32px;
  color: var(--text-secondary);
}

.tr-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.tr-table th {
  text-align: left;
  padding: 8px 12px;
  color: var(--text-secondary);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-color);
}

.th-user { width: 40%; }
.th-hours { width: 30%; }
.th-count { width: 15%; }
.th-toggle { width: 15%; text-align: right; }

.tr-user-row {
  cursor: pointer;
}

.tr-user-row:hover td {
  background: var(--bg-tertiary);
}

.tr-user-row td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
}

.td-user {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tr-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--accent-muted);
  color: var(--accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}

.td-hours {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tr-bar-wrap {
  flex: 1;
  height: 6px;
  background: var(--bg-secondary);
  border-radius: 3px;
  overflow: hidden;
}

.tr-bar {
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
  transition: width 0.3s;
}

.td-toggle {
  text-align: right;
  color: var(--text-secondary);
  font-size: 10px;
}

.tr-detail-row td {
  padding: 6px 12px 6px 50px;
  font-size: 12px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--bg-tertiary);
}

.td-detail-task {
  display: flex;
  gap: 6px;
}

.tr-human-id {
  font-weight: 600;
  color: var(--accent);
  font-size: 12px;
}

.tr-task-title {
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 250px;
}

.td-comment {
  font-style: italic;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tr-footer td {
  padding: 10px 12px;
  border-top: 2px solid var(--border-color);
  color: var(--text-primary);
}

.tr-empty {
  text-align: center;
  padding: 32px;
  color: var(--text-secondary);
  font-size: 13px;
}

/* Modal */
.tr-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.tr-modal {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 24px;
  width: 420px;
  max-width: 90vw;
  box-shadow: var(--shadow-dropdown);
}

.tr-modal h3 {
  margin: 0 0 16px 0;
  color: var(--text-primary);
  font-size: 16px;
}

.tr-field {
  margin-bottom: 12px;
  position: relative;
}

.tr-field label {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.tr-search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  max-height: 200px;
  overflow-y: auto;
  z-index: 10;
  box-shadow: var(--shadow-dropdown);
}

.tr-search-item {
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-primary);
}

.tr-search-item:hover {
  background: var(--bg-tertiary);
}

.tr-selected-issue {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: var(--accent-muted);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-primary);
  margin-top: 6px;
}

.tr-btn-x {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 16px;
  padding: 0 4px;
}

.tr-btn-x:hover {
  color: var(--error);
}

.tr-modal-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
