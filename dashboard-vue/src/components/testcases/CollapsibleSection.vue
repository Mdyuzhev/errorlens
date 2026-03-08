<template>
  <div class="collapsible-section" :class="{ 'collapsible-section--open': isOpen }">
    <button type="button" class="collapsible-header" @click="toggle">
      <span class="collapsible-arrow">{{ isOpen ? '▼' : '▶' }}</span>
      <span class="collapsible-title">{{ title }}</span>
    </button>
    <div class="collapsible-body" ref="bodyRef" :style="bodyStyle">
      <div class="collapsible-content" ref="contentRef">
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
  defaultOpen: { type: Boolean, default: false },
  hasContent: { type: Boolean, default: false }
})

const isOpen = ref(props.defaultOpen || props.hasContent)
const contentRef = ref(null)
const contentHeight = ref(0)

function measureContent() {
  if (contentRef.value) {
    contentHeight.value = contentRef.value.scrollHeight
  }
}

const bodyStyle = computed(() => ({
  maxHeight: isOpen.value ? contentHeight.value + 200 + 'px' : '0px'
}))

function toggle() {
  isOpen.value = !isOpen.value
  nextTick(measureContent)
}

watch(() => props.hasContent, (val) => {
  if (val) isOpen.value = true
})

onMounted(() => {
  nextTick(measureContent)
})
</script>

<style scoped>
.collapsible-section {
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  margin-bottom: 12px;
  overflow: hidden;
}

.collapsible-header {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.03);
  border: none;
  color: var(--text-primary, #e5e7eb);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s;
}

.collapsible-header:hover {
  background: rgba(255, 255, 255, 0.06);
}

.collapsible-arrow {
  font-size: 10px;
  width: 14px;
  text-align: center;
  transition: transform 0.2s;
}

.collapsible-body {
  overflow: hidden;
  transition: max-height 0.25s ease;
}

.collapsible-content {
  padding: 12px 14px;
}
</style>
