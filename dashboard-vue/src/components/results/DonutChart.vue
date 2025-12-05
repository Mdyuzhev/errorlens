<template>
  <div class="chart-section">
    <div class="donut-chart">
      <svg viewBox="0 0 100 100">
        <!-- Background circle -->
        <circle
          cx="50" cy="50" r="40"
          fill="none"
          stroke="var(--bg-secondary)"
          stroke-width="12"
        />

        <!-- Passed segment -->
        <circle
          cx="50" cy="50" r="40"
          fill="none"
          stroke="#10b981"
          stroke-width="12"
          :stroke-dasharray="passedDash"
          stroke-dashoffset="0"
          transform="rotate(-90 50 50)"
        />

        <!-- Failed segment -->
        <circle
          cx="50" cy="50" r="40"
          fill="none"
          stroke="#ef4444"
          stroke-width="12"
          :stroke-dasharray="failedDash"
          :stroke-dashoffset="failedOffset"
          transform="rotate(-90 50 50)"
        />

        <!-- Center text -->
        <text x="50" y="45" text-anchor="middle" class="chart-percent">
          {{ stats.pass_rate }}%
        </text>
        <text x="50" y="60" text-anchor="middle" class="chart-label">
          pass rate
        </text>
      </svg>
    </div>

    <!-- Legend -->
    <div class="chart-legend">
      <div class="legend-item">
        <span class="dot passed"></span>
        Passed ({{ stats.passed }})
      </div>
      <div class="legend-item">
        <span class="dot failed"></span>
        Failed ({{ stats.failed }})
      </div>
      <div class="legend-item">
        <span class="dot skipped"></span>
        Skipped ({{ stats.skipped }})
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stats: {
    type: Object,
    required: true
  }
})

const circumference = 2 * Math.PI * 40

const passedDash = computed(() => {
  const percent = props.stats.total_tests > 0
    ? props.stats.passed / props.stats.total_tests
    : 0
  return `${percent * circumference} ${circumference}`
})

const failedDash = computed(() => {
  const percent = props.stats.total_tests > 0
    ? props.stats.failed / props.stats.total_tests
    : 0
  return `${percent * circumference} ${circumference}`
})

const failedOffset = computed(() => {
  const passedPercent = props.stats.total_tests > 0
    ? props.stats.passed / props.stats.total_tests
    : 0
  return -passedPercent * circumference
})
</script>

<style scoped>
.chart-section {
  display: flex;
  align-items: center;
  gap: 40px;
  background: var(--bg-card);
  padding: 32px;
  border-radius: 16px;
  margin-bottom: 32px;
}

.donut-chart {
  width: 200px;
  height: 200px;
}

.donut-chart svg {
  width: 100%;
  height: 100%;
}

.chart-percent {
  font-size: 20px;
  font-weight: 700;
  fill: var(--text-primary);
}

.chart-label {
  font-size: 10px;
  fill: var(--text-secondary);
}

.chart-legend {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
}

.legend-item .dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.dot.passed { background: #10b981; }
.dot.failed { background: #ef4444; }
.dot.skipped { background: #f59e0b; }

@media (max-width: 768px) {
  .chart-section {
    flex-direction: column;
  }
}
</style>
