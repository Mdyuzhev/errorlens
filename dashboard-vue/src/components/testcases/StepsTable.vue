<template>
  <div class="steps-table">
    <table>
      <thead>
        <tr>
          <th class="col-num">#</th>
          <th class="col-action">Action</th>
          <th class="col-expected">Expected Result</th>
          <th class="col-remove"></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(step, idx) in localSteps"
          :key="step._key"
          class="step-row"
          :class="{
            'step-row--dragging': dragIdx === idx,
            'step-row--drop-above': dropIdx === idx && dropPos === 'above',
            'step-row--drop-below': dropIdx === idx && dropPos === 'below'
          }"
          :draggable="true"
          @dragstart="onDragStart($event, idx)"
          @dragover.prevent="onDragOver($event, idx)"
          @dragleave="onDragLeave"
          @drop="onDrop($event, idx)"
          @dragend="onDragEnd"
        >
          <td class="col-num">
            <span class="step-num">{{ idx + 1 }}</span>
          </td>
          <td class="col-action">
            <RichEditor
              :modelValue="step.action"
              @update:modelValue="updateStep(idx, 'action', $event)"
              placeholder="Step action..."
              :editable="true"
              :uploadEnabled="false"
              :maxLength="2000"
            />
          </td>
          <td class="col-expected">
            <RichEditor
              :modelValue="step.expected"
              @update:modelValue="updateStep(idx, 'expected', $event)"
              placeholder="Expected result..."
              :editable="true"
              :uploadEnabled="false"
              :maxLength="2000"
            />
          </td>
          <td class="col-remove">
            <button
              v-if="localSteps.length > 1"
              type="button"
              class="btn-remove"
              @click="removeStep(idx)"
              title="Remove step"
            >×</button>
          </td>
        </tr>
      </tbody>
    </table>

    <button type="button" class="btn-add-step" @click="addStep" data-testid="add-step">
      + Add Step
    </button>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import RichEditor from '@/components/common/RichEditor.vue'

const props = defineProps({
  steps: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:steps'])

let keyCounter = 0

function parseContent(raw) {
  if (!raw) return null
  if (typeof raw === 'object' && raw.type === 'doc') return raw
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw)
      if (parsed && parsed.type === 'doc') return parsed
    } catch {}
    return { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: raw }] }] }
  }
  return null
}

function toLocal(step) {
  return {
    _key: keyCounter++,
    action: parseContent(step.action),
    expected: parseContent(step.expected),
    testData: step.testData || ''
  }
}

const localSteps = ref(props.steps.map(toLocal))
if (localSteps.value.length === 0) {
  localSteps.value = [toLocal({ action: '', expected: '', testData: '' })]
}

watch(() => props.steps, (newSteps) => {
  if (JSON.stringify(newSteps.map(s => ({ a: s.action, e: s.expected }))) !==
      JSON.stringify(localSteps.value.map(s => ({ a: s.action, e: s.expected })))) {
    localSteps.value = newSteps.map(toLocal)
  }
}, { deep: true })

function emitUpdate() {
  emit('update:steps', localSteps.value.map(s => ({
    action: s.action,
    expected: s.expected,
    testData: s.testData
  })))
}

function updateStep(idx, field, value) {
  localSteps.value[idx][field] = value
  emitUpdate()
}

function addStep() {
  localSteps.value.push(toLocal({ action: '', expected: '', testData: '' }))
  emitUpdate()
}

function removeStep(idx) {
  localSteps.value.splice(idx, 1)
  emitUpdate()
}

// Drag and drop
const dragIdx = ref(null)
const dropIdx = ref(null)
const dropPos = ref(null)

function onDragStart(e, idx) {
  dragIdx.value = idx
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', String(idx))
}

function onDragOver(e, idx) {
  if (dragIdx.value === null || dragIdx.value === idx) return
  const rect = e.currentTarget.getBoundingClientRect()
  const midY = rect.top + rect.height / 2
  dropIdx.value = idx
  dropPos.value = e.clientY < midY ? 'above' : 'below'
}

function onDragLeave() {
  dropIdx.value = null
  dropPos.value = null
}

function onDrop(e, idx) {
  e.preventDefault()
  if (dragIdx.value === null || dragIdx.value === idx) return

  const item = localSteps.value.splice(dragIdx.value, 1)[0]
  let targetIdx = idx
  if (dragIdx.value < idx) targetIdx--
  if (dropPos.value === 'below') targetIdx++
  localSteps.value.splice(targetIdx, 0, item)

  dragIdx.value = null
  dropIdx.value = null
  dropPos.value = null
  emitUpdate()
}

function onDragEnd() {
  dragIdx.value = null
  dropIdx.value = null
  dropPos.value = null
}
</script>

<style scoped>
.steps-table table {
  width: 100%;
  border-collapse: collapse;
}

.steps-table th {
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  padding: 6px 8px;
  border-bottom: 1px solid var(--border-color);
}

.col-num { width: 36px; text-align: center; }
.col-action { width: 45%; }
.col-expected { width: 45%; }
.col-remove { width: 32px; }

.step-row {
  cursor: grab;
  transition: opacity 0.15s;
}

.step-row td {
  padding: 4px 8px;
  vertical-align: top;
  border-bottom: 1px solid var(--border-color);
}

.step-row--dragging {
  opacity: 0.4;
}

.step-row--drop-above td {
  border-top: 2px solid var(--accent);
}

.step-row--drop-below td {
  border-bottom: 2px solid var(--accent);
}

.step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  background: var(--accent);
  color: white;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 600;
}

.btn-remove {
  visibility: hidden;
  background: none;
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #f87171;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.step-row:hover .btn-remove {
  visibility: visible;
}

.btn-remove:hover {
  background: rgba(239, 68, 68, 0.15);
}

.btn-add-step {
  margin-top: 8px;
  padding: 6px 14px;
  background: rgba(99, 102, 241, 0.1);
  border: 1px dashed rgba(99, 102, 241, 0.3);
  color: var(--accent);
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

.btn-add-step:hover {
  background: rgba(99, 102, 241, 0.2);
}

/* Minimize RichEditor in cells */
:deep(.rich-editor) {
  min-height: 60px;
}

:deep(.editor-toolbar) {
  display: none;
}
</style>
