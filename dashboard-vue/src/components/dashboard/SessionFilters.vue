<template>
  <div class="filters">
    <button
      v-for="f in filters"
      :key="f.value"
      class="filter-btn"
      :class="{ active: modelValue === f.value }"
      @click="$emit('update:modelValue', f.value)"
    >
      {{ f.label }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  modelValue: {
    type: String,
    default: 'all'
  }
})

defineEmits(['update:modelValue'])

const filters = [
  { label: 'All', value: 'all' },
  { label: 'Bugs', value: 'bug' },
  { label: 'Chains', value: 'chain' }
]
</script>

<style scoped>
.filters {
  display: flex;
  gap: 8px;
}

.filter-btn {
  padding: 8px 16px;
  background: var(--bg-card);
  border: none;
  border-radius: 8px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.filter-btn:hover,
.filter-btn.active {
  background: var(--accent);
  color: white;
}
</style>
