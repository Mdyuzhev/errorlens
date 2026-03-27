<template>
  <div class="eva-tab">

    <!-- Upload zone -->
    <div
      class="upload-zone"
      :class="{ dragging: isDragging, 'has-file': selectedFile }"
      @dragenter.prevent="isDragging = true"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
    >
      <template v-if="!selectedFile">
        <div class="upload-icon">📦</div>
        <p class="upload-title">Drop a .zip archive with your tests</p>
        <p class="upload-hint">or click to browse</p>
        <input
          type="file"
          accept=".zip"
          class="file-input"
          @change="onFileSelect"
        />
      </template>
      <template v-else>
        <div class="file-info">
          <span class="file-name">{{ selectedFile.name }}</span>
          <span class="file-size">{{ formatBytes(selectedFile.size) }}</span>
          <button class="btn-clear" @click.stop="clearFile">x</button>
        </div>
      </template>
    </div>

    <!-- Actions -->
    <div class="actions-row">
      <button
        class="btn-run"
        :disabled="!selectedFile || running"
        @click="runEva"
      >
        <span v-if="running" class="spinner-sm"></span>
        <span v-if="running">Analyzing...</span>
        <span v-else>Run EVA</span>
      </button>
    </div>

    <!-- Error -->
    <div v-if="error" class="error-box">{{ error }}</div>

    <!-- Results -->
    <div v-if="result" class="eva-results">

      <!-- Score hero -->
      <div class="score-hero">
        <div class="score-circle" :style="{ borderColor: scoreColor(result.total) }">
          <span class="score-value">{{ result.total }}</span>
          <span class="score-label">/ 100</span>
        </div>
        <div class="score-meta">
          <span
            class="grade-badge"
            :class="'grade-' + result.grade.toLowerCase()"
          >{{ result.grade }}</span>
          <p class="grade-desc">{{ result.grade_desc }}</p>
          <div class="file-test-counts">
            <span>{{ result.files }} files</span>
            <span>{{ result.tests }} tests</span>
          </div>
        </div>
      </div>

      <!-- Metric bars -->
      <div class="metrics-section">
        <h3 class="section-heading">Metrics</h3>
        <div
          v-for="(meta, key) in metricsDisplay"
          :key="key"
          class="metric-row"
        >
          <div class="metric-header">
            <span class="metric-label">{{ meta.label }}</span>
            <span class="metric-weight">weight {{ meta.weight }}</span>
            <span
              class="metric-score"
              :style="{ color: scoreColor(result.scores[key]) }"
            >{{ Math.round(result.scores[key] || 0) }}</span>
          </div>
          <div class="bar-track">
            <div
              class="bar-fill"
              :style="{
                width: (result.scores[key] || 0) + '%',
                background: scoreColor(result.scores[key] || 0)
              }"
            ></div>
          </div>
        </div>
      </div>

      <!-- Anti-patterns -->
      <div v-if="result.anti_patterns?.length" class="section-block">
        <h3 class="section-heading">Anti-patterns</h3>
        <ul class="issue-list">
          <li v-for="(ap, i) in result.anti_patterns" :key="i" class="issue-item issue-error">
            <span class="issue-location">{{ ap.file }}</span>
            <span class="issue-msg">{{ ap.pattern }} (x{{ ap.count }}, -{{ ap.penalty }}pts)</span>
          </li>
        </ul>
      </div>

      <!-- Copy-paste warning -->
      <div v-if="result.copy_paste?.detected" class="warning-box">
        <strong>Copy-paste detected:</strong> {{ result.copy_paste.sequence }} sequential tests ({{ result.copy_paste.prefix }}*) — consider parameterizing
      </div>

      <!-- Bad naming warning -->
      <div v-if="result.bad_naming?.count" class="warning-box">
        <strong>Bad naming:</strong> {{ result.bad_naming.found?.join(', ') }} — use descriptive test names
      </div>

      <!-- Recommendations -->
      <div v-if="result.recommendations?.length" class="section-block">
        <h3 class="section-heading">Recommendations</h3>
        <ul class="rec-list">
          <li v-for="(rec, i) in result.recommendations" :key="i" class="rec-item">
            {{ rec }}
          </li>
        </ul>
      </div>

      <!-- Coverage breakdown -->
      <div class="section-block">
        <h3 class="section-heading">Coverage Breakdown</h3>
        <div class="coverage-grid">
          <div class="coverage-card">
            <span class="coverage-num" :style="{ color: scoreColor(negativePct) }">
              {{ negativePct }}%
            </span>
            <span class="coverage-label">Negative scenarios</span>
            <span class="coverage-detail">{{ result.negative_covered }}/{{ result.negative_total }}</span>
          </div>
          <div class="coverage-card">
            <span class="coverage-num" :style="{ color: scoreColor(edgePct) }">
              {{ edgePct }}%
            </span>
            <span class="coverage-label">Edge cases</span>
            <span class="coverage-detail">{{ result.edge_covered }}/{{ result.edge_total }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { evaApi } from '@/services/api'

const selectedFile = ref(null)
const isDragging = ref(false)
const running = ref(false)
const result = ref(null)
const error = ref(null)

const negativePct = computed(() => result.value ? Math.round(result.value.negative_covered / result.value.negative_total * 100) : 0)
const edgePct = computed(() => result.value ? Math.round(result.value.edge_covered / result.value.edge_total * 100) : 0)

const metricsDisplay = {
  oracle:    { label: 'Oracle Strength',   weight: '30%' },
  mutation:  { label: 'Mutation Score',    weight: '25%' },
  negative:  { label: 'Negative Coverage', weight: '20%' },
  edge:      { label: 'Edge Cases',        weight: '15%' },
  structure: { label: 'Structural',        weight: '10%' },
}

function scoreColor(score) {
  if (score >= 80) return 'var(--success)'
  if (score >= 60) return 'var(--warning)'
  return 'var(--error)'
}

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

function onDrop(e) {
  isDragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file && file.name.endsWith('.zip')) {
    selectedFile.value = file
    error.value = null
  }
}

function onFileSelect(e) {
  const file = e.target?.files?.[0]
  if (file) {
    selectedFile.value = file
    error.value = null
  }
}

function clearFile() {
  selectedFile.value = null
  result.value = null
  error.value = null
}

async function runEva() {
  if (!selectedFile.value) return
  running.value = true
  error.value = null
  result.value = null
  try {
    const resp = await evaApi.analyze(selectedFile.value)
    result.value = resp.data
  } catch (e) {
    error.value = e.response?.data?.detail || 'EVA analysis failed'
  } finally {
    running.value = false
  }
}
</script>

<style scoped>
.eva-tab { display: flex; flex-direction: column; gap: 16px; }
.upload-zone {
  position: relative; border: 2px dashed var(--border-color); border-radius: 12px;
  padding: 40px 20px; text-align: center; cursor: pointer; transition: all 0.2s; background: var(--bg-card);
}
.upload-zone.dragging { border-color: var(--accent); background: var(--accent-muted); }
.upload-zone.has-file { padding: 16px 20px; border-style: solid; }
.upload-icon { font-size: 40px; margin-bottom: 8px; }
.upload-title { font-size: 14px; font-weight: 600; color: var(--text-primary); margin: 0 0 4px; }
.upload-hint { font-size: 12px; color: var(--text-secondary); margin: 0; }
.file-input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
.file-info { display: flex; align-items: center; gap: 12px; }
.file-name { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.file-size { font-size: 12px; color: var(--text-secondary); }
.btn-clear {
  margin-left: auto; background: var(--bg-tertiary); border: 1px solid var(--border-color);
  border-radius: 4px; color: var(--text-secondary); cursor: pointer; padding: 2px 8px; font-size: 12px;
}
.btn-clear:hover { color: var(--error); }
.actions-row { display: flex; gap: 8px; }
.btn-run {
  display: flex; align-items: center; gap: 8px; padding: 10px 24px; background: var(--accent);
  border: none; border-radius: 8px; color: white; font-size: 14px; font-weight: 600;
  cursor: pointer; transition: opacity 0.15s;
}
.btn-run:hover { opacity: 0.85; }
.btn-run:disabled { opacity: 0.4; cursor: not-allowed; }
.spinner-sm {
  width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white; border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.error-box {
  background: var(--accent-muted); border: 1px solid var(--error);
  border-radius: 8px; padding: 12px; color: var(--error); font-size: 13px;
}
.eva-results { display: flex; flex-direction: column; gap: 20px; }
.score-hero {
  display: flex; align-items: center; gap: 24px; background: var(--bg-card);
  border: 1px solid var(--border-color); border-radius: 12px; padding: 24px;
}
.score-circle {
  width: 100px; height: 100px; border: 4px solid; border-radius: 50%;
  display: flex; flex-direction: column; align-items: center; justify-content: center; flex-shrink: 0;
}
.score-value { font-size: 32px; font-weight: 800; color: var(--text-primary); }
.score-label { font-size: 12px; color: var(--text-secondary); }
.score-meta { display: flex; flex-direction: column; gap: 6px; }
.grade-badge {
  display: inline-block; padding: 4px 14px; border-radius: 6px;
  font-size: 18px; font-weight: 800; width: fit-content;
}
.grade-s { background: rgba(168,85,247,0.15); color: #a855f7; }
.grade-a { background: rgba(16,185,129,0.15); color: var(--success); }
.grade-b { background: rgba(59,130,246,0.15); color: #3b82f6; }
.grade-c { background: rgba(245,158,11,0.15); color: var(--warning); }
.grade-d, .grade-f { background: rgba(239,68,68,0.15); color: var(--error); }
.grade-desc { font-size: 13px; color: var(--text-secondary); margin: 0; }
.file-test-counts { display: flex; gap: 16px; font-size: 12px; color: var(--text-secondary); }
.metrics-section, .section-block {
  background: var(--bg-card); border: 1px solid var(--border-color);
  border-radius: 12px; padding: 20px;
}
.metrics-section { display: flex; flex-direction: column; gap: 14px; }
.section-heading { font-size: 14px; font-weight: 600; color: var(--text-primary); margin: 0; }
.metric-row { display: flex; flex-direction: column; gap: 4px; }
.metric-header { display: flex; align-items: center; gap: 8px; }
.metric-label { font-size: 13px; font-weight: 500; color: var(--text-primary); flex: 1; }
.metric-weight { font-size: 11px; color: var(--text-secondary); }
.metric-score { font-size: 14px; font-weight: 700; min-width: 28px; text-align: right; }
.bar-track { height: 6px; background: var(--bg-tertiary); border-radius: 3px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
.issue-list {
  list-style: none; padding: 0; margin: 12px 0 0;
  display: flex; flex-direction: column; gap: 8px;
}
.issue-item {
  display: flex; gap: 10px; align-items: baseline;
  font-size: 13px; padding: 8px 12px; border-radius: 6px;
}
.issue-error { background: rgba(239,68,68,0.08); }
.issue-location { font-family: monospace; font-size: 12px; color: var(--text-secondary); white-space: nowrap; }
.issue-msg { color: var(--text-primary); }
.warning-box {
  background: rgba(245,158,11,0.08); border: 1px solid var(--warning);
  border-radius: 8px; padding: 12px 16px; font-size: 13px; color: var(--text-primary);
}
.warning-box strong { color: var(--warning); }
.rec-list {
  list-style: none; padding: 0; margin: 12px 0 0;
  display: flex; flex-direction: column; gap: 6px;
}
.rec-item {
  font-size: 13px; color: var(--text-primary); padding: 8px 12px;
  background: var(--bg-secondary); border-radius: 6px;
}
.rec-item::before { content: '\2192 '; color: var(--accent); }
.coverage-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }
.coverage-card {
  display: flex; flex-direction: column; align-items: center;
  gap: 4px; padding: 16px; background: var(--bg-secondary); border-radius: 8px;
}
.coverage-num { font-size: 24px; font-weight: 700; }
.coverage-label { font-size: 12px; font-weight: 500; color: var(--text-primary); }
.coverage-detail { font-size: 11px; color: var(--text-secondary); }
@media (max-width: 600px) {
  .score-hero { flex-direction: column; text-align: center; }
  .coverage-grid { grid-template-columns: 1fr; }
}
</style>
