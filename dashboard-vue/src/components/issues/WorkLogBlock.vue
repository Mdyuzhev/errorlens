<template>
  <div class="worklog-block">
    <h4>Time Tracking</h4>

    <!-- Progress bar -->
    <div v-if="estimated && estimated > 0" class="progress-section">
      <div class="progress-labels">
        <span>{{ spent || 0 }}h / {{ estimated }}h</span>
        <span :class="{ over: pct >= 100 }">{{ pct }}%</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" :class="{ over: pct >= 100 }" :style="{ width: Math.min(pct, 100) + '%' }"></div>
      </div>
    </div>
    <div v-else class="no-estimate">No estimate set</div>

    <!-- Log work button / form -->
    <div v-if="!showForm" class="log-btn-row">
      <button class="btn-sm btn-primary" @click="showForm = true">Log Work</button>
    </div>

    <div v-else class="log-form">
      <div class="form-row">
        <label>Hours</label>
        <input v-model.number="form.hours" type="number" step="0.25" min="0.25" placeholder="0" />
      </div>
      <div class="form-row">
        <label>Date</label>
        <input v-model="form.date" type="date" />
      </div>
      <div class="form-row">
        <label>Comment</label>
        <input v-model="form.comment" placeholder="What did you work on?" />
      </div>
      <div class="form-actions">
        <button class="btn-sm btn-primary" @click="submitLog" :disabled="!form.hours">Save</button>
        <button class="btn-sm" @click="showForm = false">Cancel</button>
      </div>
    </div>

    <!-- Log entries -->
    <div v-if="logs?.length" class="log-list">
      <div v-for="log in logs" :key="log.id" class="log-entry">
        <span class="log-author">{{ log.user?.display_name || log.user?.username || 'User' }}</span>
        <span class="log-hours">{{ log.hours }}h</span>
        <span class="log-date">{{ formatDate(log.logged_at || log.created_at) }}</span>
        <span v-if="log.comment" class="log-comment">{{ log.comment }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useIssuesStore } from '@/stores/issues'

const props = defineProps({
  issueId: { type: String, required: true },
  estimated: { type: Number, default: null },
  spent: { type: Number, default: null },
  logs: { type: Array, default: () => [] },
})

const store = useIssuesStore()
const showForm = ref(false)
const form = ref({ hours: '', date: new Date().toISOString().slice(0, 10), comment: '' })

const pct = computed(() => {
  if (!props.estimated || props.estimated <= 0) return 0
  return Math.round(((props.spent || 0) / props.estimated) * 100)
})

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString()
}

async function submitLog() {
  if (!form.value.hours) return
  await store.createWorkLog(props.issueId, {
    hours: form.value.hours,
    logged_at: form.value.date,
    comment: form.value.comment || null,
  })
  form.value = { hours: '', date: new Date().toISOString().slice(0, 10), comment: '' }
  showForm.value = false
}
</script>

<style scoped>
.worklog-block h4 {
  margin: 0 0 12px 0;
  font-size: 13px;
  text-transform: uppercase;
  color: var(--text-secondary);
  letter-spacing: 0.5px;
}

.progress-section { margin-bottom: 12px; }

.progress-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.progress-labels .over { color: #ef4444; font-weight: 600; }

.progress-track {
  height: 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 4px;
  transition: width 0.3s;
}

.progress-fill.over { background: #ef4444; }

.no-estimate {
  font-size: 12px;
  color: var(--text-secondary);
  font-style: italic;
  margin-bottom: 12px;
}

.log-btn-row { margin-bottom: 12px; }

.log-form {
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.form-row label {
  font-size: 12px;
  color: var(--text-secondary);
  width: 60px;
  flex-shrink: 0;
}

.form-row input {
  flex: 1;
  padding: 6px 8px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 13px;
}

.form-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.btn-sm {
  padding: 6px 14px;
  font-size: 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.btn-sm:hover { opacity: 0.9; }
.btn-sm.btn-primary { background: var(--accent); color: white; }
.btn-sm:disabled { opacity: 0.5; cursor: default; }

.log-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.log-entry {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding: 6px 0;
  border-bottom: 1px solid var(--bg-secondary);
  font-size: 12px;
}

.log-entry:last-child { border-bottom: none; }
.log-author { font-weight: 600; color: var(--text-primary); }
.log-hours { color: var(--accent); font-weight: 600; }
.log-date { color: var(--text-secondary); }
.log-comment { width: 100%; color: var(--text-secondary); font-style: italic; }
</style>
