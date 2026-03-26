<template>
  <div class="dashboard-placeholder">
    <div class="placeholder-icon">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    </div>
    <h3>Dashboard</h3>
    <p>Charts and statistics will appear here.</p>
  </div>
</template>

<script setup>
defineProps({
  projectId: { type: [String, Number], default: null }
})
</script>

<style scoped>
.dashboard-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: var(--text-secondary);
  text-align: center;
}

.placeholder-icon {
  margin-bottom: 16px;
  opacity: 0.4;
}

.dashboard-placeholder h3 {
  margin: 0 0 8px;
  font-size: 18px;
  color: var(--text-primary);
}

.dashboard-placeholder p {
  margin: 0;
  font-size: 14px;
}
</style>
