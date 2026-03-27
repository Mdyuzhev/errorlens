<template>
  <div class="step-tree">
    <div
      v-for="(step, idx) in steps"
      :key="idx"
      class="step-item"
      :class="step.status"
      :style="{ paddingLeft: depth * 16 + 'px' }"
    >
      <span class="step-status-icon">{{ step.status === 'passed' ? '✓' : '✗' }}</span>
      <span class="step-name">{{ step.name }}</span>
      <span class="step-duration">{{ step.duration_ms }}ms</span>

      <div v-if="step.parameters?.length" class="step-params">
        <span v-for="p in step.parameters" :key="p.name" class="step-param">
          {{ p.name }}: {{ p.value }}
        </span>
      </div>

      <StepTree
        v-if="step.steps?.length"
        :steps="step.steps"
        :depth="depth + 1"
      />
    </div>
  </div>
</template>

<script setup>
defineProps({
  steps: { type: Array, default: () => [] },
  depth: { type: Number, default: 0 }
})
</script>

<style scoped>
.step-item {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 12px;
  border-left: 2px solid var(--bg-tertiary);
  padding-left: 12px;
  margin-left: 8px;
}

.step-item.passed { border-color: var(--success); }
.step-item.failed { border-color: var(--error); }

.step-status-icon { width: 16px; text-align: center; }
.step-item.passed .step-status-icon { color: var(--success); }
.step-item.failed .step-status-icon { color: var(--error); }

.step-name { flex: 1; min-width: 0; }

.step-duration {
  color: var(--text-secondary);
  font-size: 11px;
  white-space: nowrap;
}

.step-params {
  width: 100%;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  padding-left: 24px;
}

.step-param {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  background: var(--accent-muted);
  color: var(--text-secondary);
}
</style>
