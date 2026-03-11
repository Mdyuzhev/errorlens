<template>
  <div class="transition-popover" ref="popoverRef" :style="popoverStyle">
    <div class="popover-header">
      <span class="popover-badge" :style="{ background: fromStatus?.color }">{{ fromStatus?.name }}</span>
      <span class="popover-arrow">→</span>
      <span class="popover-badge" :style="{ background: toStatus?.color }">{{ toStatus?.name }}</span>
    </div>

    <div class="popover-section">
      <div class="popover-subtitle">Fields that must be filled before this transition</div>
      <label
        v-for="f in AVAILABLE_FIELDS"
        :key="f.key"
        class="field-checkbox"
      >
        <input
          type="checkbox"
          :checked="selectedFields.includes(f.key)"
          @change="toggleField(f.key)"
        />
        {{ f.label }}
      </label>
    </div>

    <div class="popover-footer">
      <button
        v-if="!confirmRemove"
        class="btn-remove"
        @click="confirmRemove = true"
      >Remove transition</button>
      <template v-else>
        <span class="confirm-text">Are you sure?</span>
        <button class="btn-confirm-yes" @click="$emit('remove')">Yes</button>
        <button class="btn-confirm-no" @click="confirmRemove = false">No</button>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

const AVAILABLE_FIELDS = [
  { key: 'assignee_id', label: 'Assignee' },
  { key: 'due_date', label: 'Due Date' },
  { key: 'estimated_hours', label: 'Estimated Hours' },
  { key: 'severity', label: 'Severity' },
  { key: 'environment', label: 'Environment' },
  { key: 'reporter_id', label: 'Reporter' },
  { key: 'labels', label: 'Labels (at least one)' },
]

const props = defineProps({
  transition: { type: Object, required: true },
  fromStatus: { type: Object, default: null },
  toStatus: { type: Object, default: null },
  anchorRect: { type: Object, default: null },
})

const emit = defineEmits(['update', 'remove', 'close'])

const popoverRef = ref(null)
const confirmRemove = ref(false)
const selectedFields = ref([...(props.transition.required_fields || [])])

const popoverStyle = computed(() => {
  if (!props.anchorRect) return {}
  return {
    top: `${props.anchorRect.bottom + 4}px`,
    left: `${props.anchorRect.left}px`,
  }
})

function toggleField(key) {
  const idx = selectedFields.value.indexOf(key)
  if (idx >= 0) {
    selectedFields.value.splice(idx, 1)
  } else {
    selectedFields.value.push(key)
  }
  emit('update', [...selectedFields.value])
}

function handleClickOutside(e) {
  if (popoverRef.value && !popoverRef.value.contains(e.target)) {
    emit('close')
  }
}

function handleEscape(e) {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => {
  setTimeout(() => {
    document.addEventListener('click', handleClickOutside)
  }, 0)
  document.addEventListener('keydown', handleEscape)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleEscape)
})
</script>

<style scoped>
.transition-popover {
  position: fixed;
  z-index: 100;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: var(--shadow-dropdown);
  padding: 12px;
  min-width: 240px;
  max-width: 300px;
}
.popover-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  font-size: 13px;
  font-weight: 600;
}
.popover-badge {
  padding: 2px 8px;
  border-radius: 4px;
  color: #fff;
  font-size: 12px;
  font-weight: 500;
}
.popover-arrow {
  color: var(--text-secondary);
}
.popover-section {
  margin-bottom: 12px;
}
.popover-subtitle {
  font-size: 11px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}
.field-checkbox {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-primary);
  padding: 3px 0;
  cursor: pointer;
}
.field-checkbox input[type="checkbox"] {
  accent-color: var(--accent);
}
.popover-footer {
  border-top: 1px solid var(--border-color);
  padding-top: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.btn-remove {
  background: none;
  border: none;
  color: #ef4444;
  font-size: 12px;
  cursor: pointer;
  padding: 4px 0;
}
.btn-remove:hover { text-decoration: underline; }
.confirm-text {
  font-size: 12px;
  color: var(--text-secondary);
}
.btn-confirm-yes {
  background: #ef4444;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 2px 10px;
  font-size: 12px;
  cursor: pointer;
}
.btn-confirm-no {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: none;
  border-radius: 4px;
  padding: 2px 10px;
  font-size: 12px;
  cursor: pointer;
}
</style>
