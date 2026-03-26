<template>
  <div class="steps-editor">
    <table class="steps-table">
      <thead>
        <tr>
          <th class="col-num">#</th>
          <th class="col-action">Action</th>
          <th class="col-expected">Expected Result</th>
          <th class="col-data">Data</th>
          <th class="col-del"></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(step, idx) in localSteps"
          :key="step._key"
          class="step-row"
          :class="{ 'drag-over': dragOverIdx === idx }"
          draggable="true"
          @dragstart="onDragStart(idx, $event)"
          @dragover.prevent="onDragOver(idx)"
          @dragleave="onDragLeave"
          @drop="onDrop(idx)"
          @dragend="onDragEnd"
        >
          <td class="col-num">
            <span class="step-num">{{ idx + 1 }}</span>
          </td>
          <td class="col-action">
            <textarea
              v-model="step.action"
              class="cell-input"
              placeholder="Step action..."
              rows="1"
              @input="autoResize($event); emitUpdate()"
              @keydown.tab="handleTab(idx, 'action', $event)"
            />
          </td>
          <td class="col-expected">
            <textarea
              v-model="step.expected"
              class="cell-input"
              placeholder="Expected result..."
              rows="1"
              @input="autoResize($event); emitUpdate()"
              @keydown.tab="handleTab(idx, 'expected', $event)"
            />
          </td>
          <td class="col-data">
            <textarea
              v-model="step.data"
              class="cell-input"
              placeholder="Test data..."
              rows="1"
              @input="autoResize($event); emitUpdate()"
              @keydown.tab="handleTab(idx, 'data', $event)"
            />
          </td>
          <td class="col-del">
            <button class="btn-del" @click="removeStep(idx)" title="Delete step">&times;</button>
          </td>
        </tr>
      </tbody>
    </table>

    <button class="btn-add-step" @click="addStep">+ Step</button>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

let keyCounter = 0

const props = defineProps({
  modelValue: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue'])

function makeStep(s = {}) {
  return {
    _key: ++keyCounter,
    action: s.action || '',
    expected: s.expected || '',
    data: s.data || ''
  }
}

const localSteps = ref(props.modelValue.map(makeStep))

watch(() => props.modelValue, (val) => {
  if (JSON.stringify(stripKeys(localSteps.value)) !== JSON.stringify(val)) {
    localSteps.value = val.map(makeStep)
  }
}, { deep: true })

function stripKeys(steps) {
  return steps.map(({ action, expected, data }) => ({ action, expected, data }))
}

function emitUpdate() {
  emit('update:modelValue', stripKeys(localSteps.value))
}

function addStep() {
  localSteps.value.push(makeStep())
  emitUpdate()
}

function removeStep(idx) {
  localSteps.value.splice(idx, 1)
  emitUpdate()
}

function handleTab(idx, field, e) {
  if (field === 'data' && idx === localSteps.value.length - 1 && !e.shiftKey) {
    e.preventDefault()
    addStep()
  }
}

function autoResize(e) {
  const el = e.target
  el.style.height = 'auto'
  el.style.height = el.scrollHeight + 'px'
}

// Drag & drop
const dragIdx = ref(null)
const dragOverIdx = ref(null)

function onDragStart(idx, e) {
  dragIdx.value = idx
  e.dataTransfer.effectAllowed = 'move'
}

function onDragOver(idx) {
  dragOverIdx.value = idx
}

function onDragLeave() {
  dragOverIdx.value = null
}

function onDrop(idx) {
  dragOverIdx.value = null
  if (dragIdx.value === null || dragIdx.value === idx) return
  const item = localSteps.value.splice(dragIdx.value, 1)[0]
  localSteps.value.splice(idx, 0, item)
  dragIdx.value = null
  emitUpdate()
}

function onDragEnd() {
  dragIdx.value = null
  dragOverIdx.value = null
}
</script>

<style scoped>
.steps-editor {
  width: 100%;
}

.steps-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.steps-table thead th {
  padding: 8px 10px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #7a788a;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  background: #16152a;
}

.col-num { width: 40px; }
.col-action { width: 35%; }
.col-expected { width: 30%; }
.col-data { width: 20%; }
.col-del { width: 36px; }

.step-row {
  cursor: grab;
  transition: background 0.1s;
}
.step-row:hover {
  background: #22203a;
}
.step-row.drag-over {
  border-top: 2px solid #7c5cbf;
}

.step-row td {
  padding: 6px 10px;
  vertical-align: top;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 4px;
  background: #22203a;
  color: #7a788a;
  font-size: 11px;
  font-weight: 600;
}

.cell-input {
  width: 100%;
  min-height: 28px;
  padding: 6px 8px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
  color: #e8e6f0;
  font-size: 13px;
  font-family: inherit;
  resize: none;
  overflow: hidden;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
}
.cell-input:focus {
  border-color: #7c5cbf;
  background: #1a1930;
}
.cell-input::placeholder {
  color: #4a4858;
}

.btn-del {
  background: none;
  border: none;
  color: #4a4858;
  font-size: 18px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  line-height: 1;
  transition: all 0.15s;
}
.btn-del:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.15);
}

.btn-add-step {
  width: 100%;
  padding: 10px;
  margin-top: 4px;
  background: none;
  border: 1px dashed #4a4858;
  border-radius: 6px;
  color: #7a788a;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-add-step:hover {
  border-color: #7c5cbf;
  color: #9b7de0;
}
</style>
