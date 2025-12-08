<template>
  <div class="framework-selector">
    <h3>Фреймворк тестирования</h3>
    <div class="framework-grid">
      <div
        v-for="f in frameworks"
        :key="f.id"
        :class="['framework-card', { selected: modelValue === f.id }]"
        @click="$emit('update:modelValue', f.id)"
      >
        <span class="icon">{{ f.icon }}</span>
        <span class="name">{{ f.name }}</span>
        <span class="lang">{{ f.language }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  modelValue: {
    type: String,
    default: 'pytest'
  }
})

defineEmits(['update:modelValue'])

const frameworks = ref([
  {
    id: 'pytest',
    name: 'pytest',
    icon: '🐍',
    language: 'Python'
  },
  {
    id: 'restassured',
    name: 'REST Assured',
    icon: '☕',
    language: 'Java'
  },
  {
    id: 'postman',
    name: 'Postman',
    icon: '📮',
    language: 'JSON'
  },
  {
    id: 'cypress',
    name: 'Cypress',
    icon: '🌲',
    language: 'JavaScript'
  },
  {
    id: 'k6',
    name: 'k6',
    icon: '⚡',
    language: 'JavaScript'
  }
])
</script>

<style scoped>
.framework-selector h3 {
  margin: 0 0 16px;
  font-size: 16px;
  color: var(--text-primary);
}

.framework-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.framework-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px 16px;
  background: var(--bg-secondary);
  border: 2px solid var(--border-color);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.framework-card:hover {
  background: var(--bg-tertiary);
  border-color: rgba(102, 126, 234, 0.5);
  transform: translateY(-2px);
}

.framework-card.selected {
  border-color: #667eea;
  background: rgba(102, 126, 234, 0.1);
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.framework-card .icon {
  font-size: 32px;
}

.framework-card .name {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
}

.framework-card .lang {
  font-size: 12px;
  color: var(--text-secondary);
}

.framework-card.selected .name {
  color: #667eea;
}

@media (max-width: 768px) {
  .framework-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
