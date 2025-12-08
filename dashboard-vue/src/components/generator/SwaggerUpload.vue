<template>
  <div class="upload-zone" :class="{ 'drag-over': isDragOver, 'has-file': file }"
       @dragover.prevent="isDragOver = true" @dragleave.prevent="isDragOver = false"
       @drop.prevent="handleDrop" @click="$refs.input.click()">
    <input ref="input" type="file" accept=".json,.yaml,.yml" @change="e => setFile(e.target.files[0])" hidden />
    <div v-if="!file">
      <div style="font-size:48px">📄</div>
      <p>Перетащите Swagger/OpenAPI файл</p>
      <p style="color:var(--text-secondary);font-size:13px">.json, .yaml, .yml</p>
    </div>
    <div v-else>
      <div style="font-size:48px;color:#4CAF50">✓</div>
      <p style="font-weight:600">{{ file.name }}</p>
      <button @click.stop="file = null; $emit('file-removed')" style="color:#f44336">✕ Удалить</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['file-selected', 'file-removed'])
const file = ref(null)
const isDragOver = ref(false)

function handleDrop(e) {
  isDragOver.value = false
  setFile(e.dataTransfer.files[0])
}

function setFile(f) {
  file.value = f
  emit('file-selected', f)
}
</script>

<style scoped>
.upload-zone {
  border: 2px dashed #444;
  border-radius: 12px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-zone:hover,
.upload-zone.drag-over {
  border-color: #667eea;
  background: rgba(102, 126, 234, 0.1);
}

.upload-zone.has-file {
  border-style: solid;
  border-color: #4CAF50;
  cursor: default;
}
</style>
