<template>
  <div class="summary-cards">
    <div class="card total">
      <div class="value">{{ stats.total_tests }}</div>
      <div class="label">Total Tests</div>
    </div>
    <div class="card passed">
      <div class="value">{{ stats.passed }}</div>
      <div class="label">Passed</div>
    </div>
    <div class="card failed">
      <div class="value">{{ stats.failed }}</div>
      <div class="label">Failed</div>
    </div>
    <div class="card skipped">
      <div class="value">{{ stats.skipped }}</div>
      <div class="label">Skipped</div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  stats: {
    type: Object,
    required: true
  }
})
</script>

<style scoped>
.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.card {
  background: var(--bg-card);
  padding: 20px;
  border-radius: 12px;
  text-align: center;
}

.card .value {
  font-size: 32px;
  font-weight: 700;
}

.card .label {
  color: var(--text-secondary);
  font-size: 12px;
  margin-top: 4px;
}

.card.passed .value { color: #10b981; }
.card.failed .value { color: #ef4444; }
.card.skipped .value { color: #f59e0b; }

@media (max-width: 768px) {
  .summary-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
