<template>
  <span class="result-badge" :class="status || 'none'">
    {{ label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, default: null }
})

const label = computed(() => {
  const labels = {
    passed: 'Passed',
    failed: 'Failed',
    blocked: 'Blocked',
    skipped: 'Skipped',
  }
  return labels[props.status] || 'Not tested'
})
</script>

<style scoped>
.result-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  white-space: nowrap;
}
.result-badge.passed {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
}
.result-badge.failed {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}
.result-badge.blocked {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}
.result-badge.skipped {
  background: rgba(107, 114, 128, 0.2);
  color: #6b7280;
}
.result-badge.none {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
}
</style>
