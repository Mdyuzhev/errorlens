<template>
  <div class="expand-block">
    <template v-if="readonly">
      <details class="expand-details" :open="expanded || undefined">
        <summary class="expand-summary" @click.prevent="expanded = !expanded">
          <span class="expand-arrow" :class="{ 'expand-arrow--open': expanded }">&#9654;</span>
          <span class="expand-title">{{ summary || 'Подробнее' }}</span>
        </summary>
        <div v-if="expanded" class="expand-body">
          <RichEditor
            :modelValue="content"
            :editable="false"
            :showToolbar="false"
          />
        </div>
      </details>
    </template>

    <template v-else>
      <div class="expand-edit">
        <div class="expand-edit-header">
          <span class="expand-arrow expand-arrow--open">&#9654;</span>
          <input
            class="expand-summary-input"
            :value="summary"
            @input="$emit('update:summary', $event.target.value)"
            placeholder="Заголовок раскрывающегося блока..."
          />
        </div>
        <div class="expand-edit-body">
          <RichEditor
            :modelValue="content"
            @update:modelValue="$emit('update:content', $event)"
            :editable="true"
            :showToolbar="false"
            placeholder="Содержимое блока..."
          />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import RichEditor from '@/components/common/RichEditor.vue'

defineProps({
  summary: { type: String, default: 'Подробнее' },
  content: { type: Object, default: () => ({ type: 'doc', content: [] }) },
  readonly: { type: Boolean, default: false }
})

defineEmits(['update:summary', 'update:content'])

const expanded = ref(false)
</script>

<style scoped>
.expand-block {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.expand-details {
  width: 100%;
}

.expand-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  cursor: pointer;
  user-select: none;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-weight: 500;
  font-size: 14px;
  list-style: none;
}

.expand-summary::-webkit-details-marker {
  display: none;
}

.expand-arrow {
  font-size: 10px;
  color: var(--text-secondary);
  transition: transform 0.15s;
  flex-shrink: 0;
}

.expand-arrow--open {
  transform: rotate(90deg);
}

.expand-title {
  flex: 1;
  min-width: 0;
}

.expand-body {
  padding: 12px 14px;
  border-top: 1px solid var(--border-color);
}

.expand-body :deep(.ProseMirror) {
  min-height: 40px;
  padding: 0;
}

.expand-edit-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: var(--bg-secondary);
}

.expand-summary-input {
  flex: 1;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 6px 10px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 500;
  outline: none;
}

.expand-summary-input:focus {
  border-color: var(--accent);
}

.expand-edit-body {
  padding: 12px 14px;
  border-top: 1px solid var(--border-color);
}

.expand-edit-body :deep(.ProseMirror) {
  min-height: 60px;
  padding: 0;
}
</style>
