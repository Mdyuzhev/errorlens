<template>
  <div class="run-card">
    <div class="run-header" @click="$emit('toggle')">
      <div class="run-status" :class="run.status">
        {{ run.status === 'passed' ? '✓' : '✗' }}
      </div>
      <div class="run-info">
        <div class="run-title">{{ run.test_type }} — {{ formatDate(run.started_at) }}</div>
        <div class="run-stats">
          <span class="passed">{{ run.passed }} passed</span>
          <span class="failed">{{ run.failed }} failed</span>
          <span class="duration">{{ formatDuration(run.duration_ms) }}</span>
        </div>
      </div>
      <div class="expand-icon">
        {{ expanded ? '▼' : '▶' }}
      </div>
    </div>

    <!-- Expanded: Test Cases -->
    <div v-if="expanded && run.results" class="run-details">
      <div
        v-for="test in run.results"
        :key="test.name"
        class="test-case"
        :class="test.status"
      >
        <div class="test-header" @click="toggleTest(test.name)">
          <span class="test-status">{{ test.status === 'passed' ? '✓' : '✗' }}</span>
          <span class="test-name">{{ test.name }}</span>
          <span class="test-duration">{{ test.duration || 0 }}ms</span>
        </div>

        <!-- Expanded test details -->
        <div v-if="expandedTests.includes(test.name)" class="test-details">
          <!-- Metadata -->
          <div v-if="test.feature || test.story" class="test-meta">
            <span v-if="test.feature" class="meta-tag feature">{{ test.feature }}</span>
            <span v-if="test.story" class="meta-tag story">{{ test.story }}</span>
            <span v-if="test.severity && test.severity !== 'normal'" class="meta-tag severity" :class="test.severity">{{ test.severity }}</span>
          </div>

          <!-- Steps -->
          <div v-if="test.steps && test.steps.length" class="test-steps">
            <div class="steps-title">Steps</div>
            <div
              v-for="(step, idx) in test.steps"
              :key="idx"
              class="step"
              :class="step.status"
            >
              <span class="step-num">{{ idx + 1 }}</span>
              <span class="step-action">{{ step.name }}</span>
              <span class="step-status">{{ step.status === 'passed' ? '✓' : '✗' }}</span>
            </div>
            <!-- Step-level error -->
            <div v-for="(step, idx) in test.steps" :key="'err-'+idx">
              <div v-if="step.statusDetails && step.statusDetails.message" class="error-message step-error">
                <div class="error-label">Step {{ idx + 1 }} error:</div>
                <pre>{{ step.statusDetails.message }}</pre>
              </div>
            </div>
          </div>

          <!-- Error message -->
          <div v-if="test.statusDetails && test.statusDetails.message" class="error-message">
            <pre>{{ test.statusDetails.message }}</pre>
          </div>

          <!-- Stack trace (collapsed) -->
          <div v-if="test.statusDetails && test.statusDetails.trace" class="trace-block">
            <div class="trace-toggle" @click.stop="toggleTrace(test.name)">
              {{ expandedTraces.includes(test.name) ? '▼' : '▶' }} Stack trace
            </div>
            <pre v-if="expandedTraces.includes(test.name)" class="trace-content">{{ test.statusDetails.trace }}</pre>
          </div>

          <!-- Attachments -->
          <div v-if="test.attachments && test.attachments.length" class="attachments">
            <div class="attachments-title">Attachments ({{ test.attachments.length }})</div>
            <div v-for="(att, idx) in test.attachments" :key="idx" class="attachment">
              <span class="att-icon">📎</span>
              <span class="att-name">{{ att.name }}</span>
              <span class="att-type">{{ att.type }}</span>
            </div>
          </div>

          <!-- No details fallback -->
          <div v-if="!test.steps?.length && !test.statusDetails?.message && !test.attachments?.length" class="no-details">
            <span class="test-fullname">{{ test.fullName }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  run: {
    type: Object,
    required: true
  },
  expanded: {
    type: Boolean,
    default: false
  }
})

defineEmits(['toggle'])

const expandedTests = ref([])
const expandedTraces = ref([])

function toggleTest(testName) {
  const idx = expandedTests.value.indexOf(testName)
  if (idx >= 0) {
    expandedTests.value.splice(idx, 1)
  } else {
    expandedTests.value.push(testName)
  }
}

function toggleTrace(testName) {
  const idx = expandedTraces.value.indexOf(testName)
  if (idx >= 0) {
    expandedTraces.value.splice(idx, 1)
  } else {
    expandedTraces.value.push(testName)
  }
}

function formatDate(isoDate) {
  if (!isoDate) return ''
  return new Date(isoDate).toLocaleString('en-US', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatDuration(ms) {
  if (!ms) return '-'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}
</script>

<style scoped>
.run-card {
  background: var(--bg-card);
  border-radius: 12px;
  margin-bottom: 12px;
  overflow: hidden;
}

.run-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  cursor: pointer;
  transition: background 0.2s;
}

.run-header:hover {
  background: var(--bg-secondary);
}

.run-status {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
}

.run-status.passed {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.run-status.failed {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.run-info {
  flex: 1;
}

.run-title {
  font-weight: 600;
  margin-bottom: 4px;
}

.run-stats {
  font-size: 12px;
  color: var(--text-secondary);
  display: flex;
  gap: 12px;
}

.run-stats .passed { color: #10b981; }
.run-stats .failed { color: #ef4444; }

.expand-icon {
  color: var(--text-secondary);
}

/* Test Cases */
.run-details {
  border-top: 1px solid var(--bg-secondary);
  padding: 16px;
}

.test-case {
  margin-bottom: 8px;
  border-radius: 8px;
  overflow: hidden;
}

.test-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-secondary);
  cursor: pointer;
}

.test-status {
  width: 20px;
  text-align: center;
}

.test-case.passed .test-status { color: #10b981; }
.test-case.failed .test-status { color: #ef4444; }

.test-name {
  flex: 1;
  font-family: monospace;
  font-size: 13px;
}

.test-duration {
  color: var(--text-secondary);
  font-size: 12px;
}

/* Test details */
.test-details {
  padding: 8px 12px 8px 40px;
}

.test-meta {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.meta-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.meta-tag.feature { color: #818cf8; background: rgba(129, 140, 248, 0.15); }
.meta-tag.story { color: #67e8f9; background: rgba(103, 232, 249, 0.15); }
.meta-tag.severity.critical { color: #ef4444; background: rgba(239, 68, 68, 0.15); }
.meta-tag.severity.blocker { color: #ef4444; background: rgba(239, 68, 68, 0.2); }
.meta-tag.severity.minor { color: #a3a3a3; }

/* Steps */
.test-steps {
  margin-bottom: 8px;
}

.steps-title {
  font-size: 11px;
  color: var(--text-secondary);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 12px;
  border-left: 2px solid var(--bg-secondary);
  padding-left: 12px;
  margin-left: 8px;
}

.step.passed { border-color: #10b981; }
.step.failed { border-color: #ef4444; }

.step-num {
  color: var(--text-secondary);
  min-width: 20px;
}

.step-action {
  flex: 1;
}

.step-status {
  width: 16px;
}

.step.passed .step-status { color: #10b981; }
.step.failed .step-status { color: #ef4444; }

/* Error */
.error-message {
  margin-top: 8px;
  padding: 12px;
  background: rgba(239, 68, 68, 0.1);
  border-radius: 8px;
  border-left: 3px solid #ef4444;
}

.error-message pre {
  margin: 0;
  font-size: 11px;
  color: #f87171;
  white-space: pre-wrap;
  word-break: break-all;
}

.error-label {
  font-size: 10px;
  color: #ef4444;
  margin-bottom: 4px;
  font-weight: 600;
}

.step-error {
  margin-left: 20px;
}

/* Stack trace */
.trace-block {
  margin-top: 8px;
}

.trace-toggle {
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px 0;
}

.trace-toggle:hover {
  color: var(--text-primary);
}

.trace-content {
  margin-top: 4px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  font-size: 10px;
  color: #a3a3a3;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
}

/* Attachments */
.attachments {
  margin-top: 8px;
}

.attachments-title {
  font-size: 11px;
  color: var(--text-secondary);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.attachment {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
  font-size: 12px;
}

.att-icon { font-size: 14px; }
.att-name { flex: 1; }
.att-type { color: var(--text-secondary); font-size: 11px; }

/* Fallback */
.no-details {
  padding: 4px 0;
}

.test-fullname {
  font-size: 11px;
  color: var(--text-secondary);
  font-family: monospace;
}
</style>
