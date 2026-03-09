<template>
  <div class="tc-meta">
    <div class="meta-field">
      <label>Status</label>
      <select :value="modelValue.status" @change="update('status', $event.target.value)">
        <option value="Draft">Draft</option>
        <option value="Ready">Ready</option>
        <option value="Approved">Approved</option>
      </select>
    </div>

    <div class="meta-field">
      <label>Priority</label>
      <select :value="modelValue.priority" @change="update('priority', $event.target.value)">
        <option value="Critical">🔴 Critical</option>
        <option value="High">🟠 High</option>
        <option value="Medium">🔵 Medium</option>
        <option value="Low">⚫ Low</option>
      </select>
    </div>

    <div class="meta-field">
      <label>Automation</label>
      <select :value="modelValue.automation_status" @change="update('automation_status', $event.target.value)">
        <option value="Manual">Manual</option>
        <option value="Automated">Automated</option>
        <option value="NotAutomatable">Not Automatable</option>
      </select>
    </div>

    <div class="meta-field">
      <label>Tags</label>
      <div class="chips-input">
        <div class="chips-list">
          <span v-for="(tag, idx) in tags" :key="tag" class="chip" @click="removeTag(idx)">
            {{ tag }}
            <span class="chip-x">×</span>
          </span>
        </div>
        <input
          v-model="tagInput"
          placeholder="Add tag..."
          @keydown.enter.prevent="addTag"
          class="chip-input"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Object, required: true }
})

const emit = defineEmits(['update:modelValue'])

const tagInput = ref('')
const tags = ref([...(props.modelValue.tags || [])])

watch(() => props.modelValue.tags, (val) => {
  tags.value = [...(val || [])]
}, { deep: true })

function update(field, value) {
  emit('update:modelValue', { ...props.modelValue, [field]: value })
}

function addTag() {
  const val = tagInput.value.trim()
  if (val && !tags.value.includes(val)) {
    tags.value.push(val)
    emit('update:modelValue', { ...props.modelValue, tags: [...tags.value] })
  }
  tagInput.value = ''
}

function removeTag(idx) {
  tags.value.splice(idx, 1)
  emit('update:modelValue', { ...props.modelValue, tags: [...tags.value] })
}
</script>

<style scoped>
.tc-meta {
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.meta-field label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary, #9ca3af);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.meta-field select {
  width: 100%;
  padding: 6px 8px;
  background: var(--bg-secondary, #1a1a2e);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.1));
  border-radius: 6px;
  color: var(--text-primary, #e5e7eb);
  font-size: 13px;
}

.chips-input {
  background: var(--bg-secondary, #1a1a2e);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.1));
  border-radius: 6px;
  padding: 6px 8px;
  min-height: 36px;
}

.chips-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 4px;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: var(--accent, #6366f1);
  color: white;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
}

.chip:hover {
  opacity: 0.8;
}

.chip-x {
  font-size: 14px;
  line-height: 1;
}

.chip-input {
  width: 100%;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text-primary, #e5e7eb);
  font-size: 13px;
  padding: 2px 0;
}
</style>
