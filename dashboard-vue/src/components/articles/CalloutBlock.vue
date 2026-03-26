<template>
  <div class="callout-block" :class="`callout-${variant}`">
    <span class="callout-icon">{{ icon }}</span>
    <div class="callout-body">
      <RichEditor
        :modelValue="content"
        @update:modelValue="$emit('update:content', $event)"
        :editable="!readonly"
        :showToolbar="false"
        placeholder="Текст callout..."
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import RichEditor from '@/components/common/RichEditor.vue'

const props = defineProps({
  variant: { type: String, default: 'info' },
  content: { type: Object, default: () => ({ type: 'doc', content: [] }) },
  readonly: { type: Boolean, default: false }
})

defineEmits(['update:content'])

const VARIANTS = {
  info: { icon: '\u2139\uFE0F' },
  warning: { icon: '\u26A0\uFE0F' },
  note: { icon: '\uD83D\uDCDD' },
  success: { icon: '\u2705' }
}

const icon = computed(() => VARIANTS[props.variant]?.icon || VARIANTS.info.icon)
</script>

<style scoped>
.callout-block {
  display: flex;
  gap: 12px;
  border-radius: 8px;
  padding: 12px 16px;
  border-left: 4px solid;
}

.callout-info {
  background: rgba(59, 130, 246, 0.1);
  border-left-color: rgba(59, 130, 246, 0.6);
}

.callout-warning {
  background: rgba(249, 115, 22, 0.1);
  border-left-color: rgba(249, 115, 22, 0.6);
}

.callout-note {
  background: rgba(234, 179, 8, 0.1);
  border-left-color: rgba(234, 179, 8, 0.6);
}

.callout-success {
  background: rgba(34, 197, 94, 0.1);
  border-left-color: rgba(34, 197, 94, 0.6);
}

.callout-icon {
  font-size: 20px;
  line-height: 1.4;
  flex-shrink: 0;
}

.callout-body {
  flex: 1;
  min-width: 0;
}

.callout-body :deep(.rich-editor) {
  background: transparent;
}

.callout-body :deep(.ProseMirror) {
  min-height: 40px;
  padding: 0;
}
</style>
