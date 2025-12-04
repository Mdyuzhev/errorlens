<template>
  <div
    ref="widgetRef"
    class="recorder-widget"
    :class="{ 'is-recording': isRecording, 'is-collapsed': isCollapsed }"
    :style="{ left: position.x + 'px', top: position.y + 'px' }"
    @mousedown="startDrag"
  >
    <!-- Collapsed state -->
    <div v-if="isCollapsed" class="widget-collapsed" @click.stop="toggleCollapse">
      <span class="status-dot" :class="{ recording: isRecording }"></span>
      <span class="collapse-icon">◀</span>
    </div>

    <!-- Expanded state -->
    <div v-else class="widget-expanded">
      <!-- Header with drag handle -->
      <div class="widget-header">
        <div class="drag-handle">⋮⋮</div>
        <span class="widget-title">ErrorLens</span>
        <button class="collapse-btn" @click.stop="toggleCollapse">▶</button>
      </div>

      <!-- Recording controls -->
      <div class="widget-body">
        <div class="status-row">
          <span class="status-dot" :class="{ recording: isRecording }"></span>
          <span class="status-text">{{ statusText }}</span>
        </div>

        <div class="stats-row" v-if="isRecording">
          <span class="stat">
            <span class="stat-value">{{ requestCount }}</span>
            <span class="stat-label">requests</span>
          </span>
          <span class="stat">
            <span class="stat-value">{{ errorCount }}</span>
            <span class="stat-label">errors</span>
          </span>
          <span class="stat">
            <span class="stat-value">{{ formatDuration(duration) }}</span>
            <span class="stat-label">time</span>
          </span>
        </div>

        <div class="controls">
          <button
            v-if="!isRecording"
            class="btn btn-start"
            @click.stop="startRecording"
          >
            ● Start
          </button>
          <template v-else>
            <button class="btn btn-stop" @click.stop="stopRecording">
              ■ Stop
            </button>
            <button class="btn btn-pause" @click.stop="togglePause">
              {{ isPaused ? '▶' : '❚❚' }}
            </button>
          </template>
        </div>

        <!-- Recent errors preview -->
        <div v-if="recentErrors.length > 0" class="errors-preview">
          <div class="errors-header">Recent errors:</div>
          <div
            v-for="(error, idx) in recentErrors.slice(0, 3)"
            :key="idx"
            class="error-item"
          >
            <span class="error-status">{{ error.status }}</span>
            <span class="error-url">{{ truncateUrl(error.url) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRecorderStore } from '@/stores/recorder'
import { storeToRefs } from 'pinia'

const recorderStore = useRecorderStore()
const { isRecording, isPaused, requestCount, errorCount, duration, recentErrors } = storeToRefs(recorderStore)

const widgetRef = ref(null)
const isCollapsed = ref(false)
const position = ref({ x: 20, y: 100 })
const isDragging = ref(false)
const dragOffset = ref({ x: 0, y: 0 })

const statusText = computed(() => {
  if (!isRecording.value) return 'Ready to record'
  if (isPaused.value) return 'Paused'
  return 'Recording...'
})

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}

function startRecording() {
  recorderStore.start()
}

function stopRecording() {
  recorderStore.stop()
}

function togglePause() {
  recorderStore.togglePause()
}

function formatDuration(ms) {
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${minutes}:${secs.toString().padStart(2, '0')}`
}

function truncateUrl(url) {
  try {
    const parsed = new URL(url)
    const path = parsed.pathname
    return path.length > 25 ? '...' + path.slice(-22) : path
  } catch {
    return url.slice(0, 25)
  }
}

// Drag functionality
function startDrag(e) {
  if (e.target.closest('.btn') || e.target.closest('.collapse-btn')) return

  isDragging.value = true
  const rect = widgetRef.value.getBoundingClientRect()
  dragOffset.value = {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top
  }

  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
}

function onDrag(e) {
  if (!isDragging.value) return

  const newX = e.clientX - dragOffset.value.x
  const newY = e.clientY - dragOffset.value.y

  // Keep within viewport bounds
  const maxX = window.innerWidth - (widgetRef.value?.offsetWidth || 200)
  const maxY = window.innerHeight - (widgetRef.value?.offsetHeight || 150)

  position.value = {
    x: Math.max(0, Math.min(newX, maxX)),
    y: Math.max(0, Math.min(newY, maxY))
  }
}

function stopDrag() {
  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)

  // Save position to localStorage
  localStorage.setItem('errorlens-widget-pos', JSON.stringify(position.value))
}

onMounted(() => {
  // Restore saved position
  const saved = localStorage.getItem('errorlens-widget-pos')
  if (saved) {
    try {
      position.value = JSON.parse(saved)
    } catch {}
  }
})

onUnmounted(() => {
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
})
</script>

<style scoped>
.recorder-widget {
  position: fixed;
  z-index: 9999;
  font-family: system-ui, -apple-system, sans-serif;
  font-size: 12px;
  user-select: none;
}

.widget-collapsed {
  background: var(--color-bg-secondary, #1e1e2e);
  border: 1px solid var(--color-border, #363649);
  border-radius: 8px;
  padding: 8px 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}

.widget-collapsed:hover {
  border-color: var(--color-primary, #a855f7);
}

.collapse-icon {
  color: var(--color-text-muted, #71717a);
  font-size: 10px;
}

.widget-expanded {
  background: var(--color-bg-secondary, #1e1e2e);
  border: 1px solid var(--color-border, #363649);
  border-radius: 12px;
  min-width: 200px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.widget-header {
  background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: move;
}

.drag-handle {
  color: rgba(255, 255, 255, 0.6);
  font-size: 14px;
  letter-spacing: -2px;
}

.widget-title {
  flex: 1;
  color: white;
  font-weight: 600;
}

.collapse-btn {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.8);
  cursor: pointer;
  padding: 2px 6px;
  font-size: 10px;
}

.collapse-btn:hover {
  color: white;
}

.widget-body {
  padding: 12px;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-text-muted, #71717a);
}

.status-dot.recording {
  background: #ef4444;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text {
  color: var(--color-text, #e4e4e7);
}

.stats-row {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  padding: 8px;
  background: var(--color-bg, #0f0f17);
  border-radius: 6px;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-weight: 600;
  color: var(--color-text, #e4e4e7);
}

.stat-label {
  font-size: 10px;
  color: var(--color-text-muted, #71717a);
}

.controls {
  display: flex;
  gap: 8px;
}

.btn {
  flex: 1;
  padding: 8px 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  font-size: 12px;
  transition: all 0.2s;
}

.btn-start {
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  color: white;
}

.btn-start:hover {
  filter: brightness(1.1);
}

.btn-stop {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
}

.btn-stop:hover {
  filter: brightness(1.1);
}

.btn-pause {
  background: var(--color-bg, #0f0f17);
  color: var(--color-text, #e4e4e7);
  border: 1px solid var(--color-border, #363649);
  flex: 0;
  padding: 8px 14px;
}

.btn-pause:hover {
  border-color: var(--color-primary, #a855f7);
}

.errors-preview {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border, #363649);
}

.errors-header {
  color: var(--color-text-muted, #71717a);
  font-size: 10px;
  margin-bottom: 6px;
  text-transform: uppercase;
}

.error-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
}

.error-status {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
}

.error-url {
  color: var(--color-text-muted, #71717a);
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Recording state glow effect */
.is-recording .widget-expanded {
  box-shadow: 0 0 20px rgba(239, 68, 68, 0.3);
}
</style>
