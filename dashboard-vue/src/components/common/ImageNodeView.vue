<template>
  <NodeViewWrapper as="span" class="image-node-view">
    <img
      :src="node.attrs.src"
      :alt="node.attrs.alt || ''"
      class="image-thumbnail"
      @click="handleClick"
    />
  </NodeViewWrapper>
</template>

<script setup>
import { inject } from 'vue'
import { NodeViewWrapper } from '@tiptap/vue-3'

const props = defineProps({
  node: { type: Object, required: true }
})

const openLightbox = inject('openLightbox', null)

function handleClick() {
  if (openLightbox) {
    openLightbox(props.node.attrs.src, props.node.attrs.alt || '')
  }
}
</script>

<style scoped>
.image-thumbnail {
  width: 200px;
  height: 140px;
  object-fit: cover;
  border-radius: 8px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: border-color 0.15s;
  display: inline-block;
}

.image-thumbnail:hover {
  border-color: var(--accent, #6366f1);
}
</style>
