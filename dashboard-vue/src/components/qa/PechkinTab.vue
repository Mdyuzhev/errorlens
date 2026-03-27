<template>
  <div class="pechkin-wrapper">
    <div v-if="store.activeCollectionId" class="pechkin-header">
      <span class="pechkin-header-title">{{ activeCollectionName }}</span>
      <EnvSelector :collection-id="store.activeCollectionId" />
    </div>
    <div class="pechkin-tab">
      <div class="pechkin-sidebar">
        <div class="sidebar-toggle">
          <button
            class="toggle-btn"
            :class="{ active: sidebarView === 'collections' }"
            @click="sidebarView = 'collections'"
          >Collections</button>
          <button
            class="toggle-btn"
            :class="{ active: sidebarView === 'history' }"
            @click="sidebarView = 'history'"
          >History</button>
        </div>
        <CollectionTree v-if="sidebarView === 'collections'" :project-id="projectId" class="sidebar-panel" />
        <GlobalHistory v-else :project-id="projectId" class="sidebar-panel" @replay="onReplay" />
      </div>
      <div class="pechkin-center">
        <RequestEditor v-if="store.activeRequest" />
        <div v-else class="pechkin-empty">
          <div class="pechkin-empty-icon">&#9889;</div>
          <p class="pechkin-empty-text">Select a request or create a new one</p>
          <button class="pechkin-new-btn" @click="createQuickRequest">+ New Request</button>
        </div>
      </div>
      <ResponseViewer class="pechkin-response" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { usePechkinStore } from '@/stores/pechkin'
import CollectionTree from '@/components/qa/pechkin/CollectionTree.vue'
import GlobalHistory from '@/components/qa/pechkin/GlobalHistory.vue'
import RequestEditor from '@/components/qa/pechkin/RequestEditor.vue'
import ResponseViewer from '@/components/qa/pechkin/ResponseViewer.vue'
import EnvSelector from '@/components/qa/pechkin/EnvSelector.vue'

const props = defineProps({
  projectId: { type: String, required: true }
})

const store = usePechkinStore()
const sidebarView = ref('collections')

const activeCollectionName = computed(() => {
  const col = store.collections.find(c => c.id === store.activeCollectionId)
  return col?.name || 'Collection'
})

async function createQuickRequest() {
  let col = store.collections[0]
  if (!col) {
    col = await store.createCollection(props.projectId, 'Default')
  }
  const req = await store.createRequest(col.id, {
    name: 'New Request',
    method: 'GET',
    url: '',
  })
  await store.openRequest(req.id)
}

async function onReplay(historyItem) {
  if (historyItem.request_id) {
    await store.openRequest(historyItem.request_id)
    sidebarView.value = 'collections'
  }
}
</script>

<style scoped>
.pechkin-wrapper {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 160px);
}

.pechkin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.pechkin-header-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.pechkin-tab {
  display: grid;
  grid-template-columns: 280px 1fr 380px;
  gap: 1px;
  flex: 1;
  min-height: 0;
  background: var(--border-color);
}
.pechkin-sidebar {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-secondary);
}
.sidebar-toggle {
  display: flex;
  border-bottom: 1px solid var(--border-color);
}
.toggle-btn {
  flex: 1;
  padding: 8px 0;
  font-size: 11px;
  font-weight: 600;
  text-align: center;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}
.toggle-btn:hover {
  color: var(--text-primary);
}
.toggle-btn.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}
.sidebar-panel {
  flex: 1;
  overflow: hidden;
}
.pechkin-center,
.pechkin-response {
  overflow: hidden;
}
.pechkin-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  background: var(--bg-card);
  gap: 12px;
}
.pechkin-empty-icon {
  font-size: 48px;
}
.pechkin-empty-text {
  color: var(--text-secondary);
  font-size: 14px;
}
.pechkin-new-btn {
  padding: 8px 20px;
  background: var(--accent);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.pechkin-new-btn:hover {
  background: var(--accent-hover);
}

@media (max-width: 1000px) {
  .pechkin-tab {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr auto;
  }
}
</style>
