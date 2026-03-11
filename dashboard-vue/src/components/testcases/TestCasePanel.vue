<template>
  <div class="tc-panel">
    <!-- Header: title input + actions -->
    <div class="panel-header">
      <input
        v-model="localForm.title"
        class="panel-title-input"
        placeholder="Test case title *"
        required
        @input="emitForm"
      />
      <div class="panel-actions">
        <button v-if="testCase" type="button" class="btn btn-danger btn-sm" @click="$emit('delete', testCase.id)">
          Delete
        </button>
        <button type="button" class="btn btn-secondary btn-sm" @click="$emit('close')">Cancel</button>
        <button type="button" class="btn btn-primary btn-sm" @click="$emit('save', localForm)">Save</button>
      </div>
    </div>

    <!-- Three-column layout -->
    <div class="panel-columns">
      <!-- Left: section navigation -->
      <nav class="panel-nav">
        <button
          v-for="section in sections"
          :key="section.id"
          type="button"
          class="nav-link"
          :class="{ 'nav-link--active': activeSection === section.id }"
          @click="scrollTo(section.id)"
        >{{ section.label }}</button>
      </nav>

      <!-- Center: scrollable content -->
      <div class="panel-content" ref="contentRef" @scroll="onScroll">
        <!-- Steps (always open) -->
        <div id="section-steps" ref="sectionSteps" class="panel-section">
          <h3 class="section-title">Steps</h3>
          <StepsTable :steps="localForm.steps" @update:steps="onStepsUpdate" />
        </div>

        <!-- Description -->
        <div id="section-description" ref="sectionDescription" class="panel-section">
          <CollapsibleSection title="Description" :defaultOpen="true" :hasContent="!!localForm.descriptionJson">
            <RichEditor
              v-model="localForm.descriptionJson"
              placeholder="Brief description"
              :maxLength="5000"
              @update:modelValue="emitForm"
            />
          </CollapsibleSection>
        </div>

        <!-- Preconditions -->
        <div id="section-preconditions" ref="sectionPreconditions" class="panel-section">
          <CollapsibleSection title="Preconditions" :hasContent="!!localForm.preconditionsJson">
            <RichEditor
              v-model="localForm.preconditionsJson"
              placeholder="What needs to be set up before test"
              :maxLength="5000"
              @update:modelValue="emitForm"
            />
          </CollapsibleSection>
        </div>

        <!-- Postconditions -->
        <div id="section-postconditions" ref="sectionPostconditions" class="panel-section">
          <CollapsibleSection title="Postconditions" :hasContent="!!localForm.postconditionsJson">
            <RichEditor
              v-model="localForm.postconditionsJson"
              placeholder="Expected state after test"
              :maxLength="5000"
              @update:modelValue="emitForm"
            />
          </CollapsibleSection>
        </div>
      </div>

      <!-- Right: sticky metadata -->
      <aside class="panel-sidebar">
        <TestCaseMeta v-model="localForm" @update:modelValue="onMetaUpdate" />

        <!-- Backlinks -->
        <div v-if="testCase && backlinks.length" class="backlinks-section">
          <label>Mentioned in articles ({{ backlinks.length }}):</label>
          <div v-for="bl in backlinks" :key="bl.article_id" class="backlink-item" @click="$emit('go-to-article', bl)">
            {{ bl.article_title }}
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import RichEditor from '@/components/common/RichEditor.vue'
import CollapsibleSection from './CollapsibleSection.vue'
import StepsTable from './StepsTable.vue'
import TestCaseMeta from './TestCaseMeta.vue'

const props = defineProps({
  testCase: { type: Object, default: null },
  modelValue: { type: Object, required: true },
  backlinks: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue', 'save', 'delete', 'close', 'go-to-article'])

const localForm = ref({ ...props.modelValue })

watch(() => props.modelValue, (val) => {
  localForm.value = { ...val }
}, { deep: true })

function emitForm() {
  emit('update:modelValue', { ...localForm.value })
}

function onStepsUpdate(steps) {
  localForm.value.steps = steps
  emitForm()
}

function onMetaUpdate(meta) {
  localForm.value = { ...localForm.value, ...meta }
  emitForm()
}

// Section navigation
const sections = [
  { id: 'steps', label: 'Steps' },
  { id: 'description', label: 'Description' },
  { id: 'preconditions', label: 'Preconditions' },
  { id: 'postconditions', label: 'Postconditions' }
]

const activeSection = ref('steps')
const contentRef = ref(null)
const sectionSteps = ref(null)
const sectionDescription = ref(null)
const sectionPreconditions = ref(null)
const sectionPostconditions = ref(null)

const sectionRefs = { steps: sectionSteps, description: sectionDescription, preconditions: sectionPreconditions, postconditions: sectionPostconditions }

function scrollTo(id) {
  const el = sectionRefs[id]?.value
  if (el && contentRef.value) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  activeSection.value = id
}

function onScroll() {
  if (!contentRef.value) return
  const scrollTop = contentRef.value.scrollTop + 40
  const offsets = sections.map(s => {
    const el = sectionRefs[s.id]?.value
    return { id: s.id, top: el ? el.offsetTop : 0 }
  })
  for (let i = offsets.length - 1; i >= 0; i--) {
    if (scrollTop >= offsets[i].top) {
      activeSection.value = offsets[i].id
      break
    }
  }
}
</script>

<style scoped>
.tc-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 16px;
  flex-shrink: 0;
}

.panel-title-input {
  flex: 1;
  font-size: 18px;
  font-weight: 600;
  background: transparent;
  border: none;
  border-bottom: 2px solid var(--border-color);
  color: var(--text-primary);
  padding: 4px 0;
  outline: none;
}

.panel-title-input:focus {
  border-bottom-color: var(--accent);
}

.panel-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.panel-columns {
  display: flex;
  gap: 0;
  flex: 1;
  min-height: 0;
}

/* Left nav */
.panel-nav {
  width: 140px;
  min-width: 140px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-right: 12px;
  border-right: 1px solid var(--border-color);
}

.nav-link {
  display: block;
  width: 100%;
  text-align: left;
  padding: 8px 10px;
  background: none;
  border: none;
  border-left: 2px solid transparent;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  border-radius: 0 4px 4px 0;
  transition: all 0.15s;
}

.nav-link:hover {
  color: var(--text-primary);
  background: var(--bg-secondary);
}

.nav-link--active {
  color: var(--accent);
  border-left-color: var(--accent);
  background: rgba(99, 102, 241, 0.05);
}

/* Center content */
.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 0 16px;
  min-width: 0;
}

.panel-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 12px 0;
}

/* Right sidebar */
.panel-sidebar {
  width: 200px;
  min-width: 200px;
  padding-left: 16px;
  border-left: 1px solid var(--border-color);
}

/* Button styles */
.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

/* Backlinks */
.backlinks-section {
  margin-top: 16px;
  padding: 12px;
  background: rgba(99, 102, 241, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(99, 102, 241, 0.15);
}

.backlinks-section label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

.backlink-item {
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.15s;
}

.backlink-item:hover {
  background: rgba(99, 102, 241, 0.1);
}

@media (max-width: 768px) {
  .panel-nav { display: none; }
  .panel-sidebar { display: none; }
}
</style>
