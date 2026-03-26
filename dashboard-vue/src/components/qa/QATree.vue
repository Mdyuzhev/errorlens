<template>
  <div class="qa-tree-layout">
    <!-- Left: Folder sidebar -->
    <aside class="qa-sidebar">
      <FolderTree
        :folders="store.treeFolders"
        :selected-folder-id="store.selectedFolderId"
        :expanded-ids="store.expandedFolders"
        @select="store.selectFolder($event)"
        @toggle="store.toggleFolder($event)"
        @create="handleCreateFolder"
        @delete="store.deleteFolder($event)"
      />
    </aside>

    <!-- Right: Toolbar + list -->
    <div class="qa-main">
      <!-- Toolbar -->
      <div class="qa-toolbar">
        <div class="toolbar-left">
          <select v-model="store.filters.status" class="filter-select" @change="store.fetchTestCases()">
            <option value="">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="ready">Ready</option>
            <option value="approved">Approved</option>
          </select>
          <select v-model="store.filters.priority" class="filter-select" @change="store.fetchTestCases()">
            <option value="">All Priorities</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>
        <div class="toolbar-right">
          <!-- Bulk actions -->
          <template v-if="store.selectedIds.size > 0">
            <span class="bulk-count">{{ store.selectedIds.size }} selected</span>
            <button class="btn-bulk" @click="$emit('add-to-plan')">Add to Plan</button>
            <button class="btn-bulk btn-bulk-danger" @click="store.bulkDeleteSelected()">Delete</button>
          </template>
          <button class="btn-export" @click="store.exportCsv(projectId)">Export CSV</button>
        </div>
      </div>

      <!-- Header row -->
      <div class="tc-header">
        <div class="col-check">
          <input type="checkbox" :checked="allChecked" @change="toggleAll" />
        </div>
        <div class="col-id">ID</div>
        <div class="col-title">Title</div>
        <div class="col-priority">Priority</div>
        <div class="col-status">Status</div>
        <div class="col-auto">Automation</div>
        <div class="col-steps">Steps</div>
        <div class="col-date">Updated</div>
      </div>

      <!-- Rows -->
      <div v-if="store.loading" class="tc-empty">Loading...</div>
      <div v-else-if="store.testCases.length === 0" class="tc-empty">No test cases found</div>
      <div
        v-for="tc in store.testCases"
        :key="tc.id"
        class="tc-row"
        :class="{ selected: store.selectedIds.has(tc.id) }"
        @click="$emit('open-case', tc.id)"
      >
        <div class="col-check" @click.stop>
          <input
            type="checkbox"
            :checked="store.selectedIds.has(tc.id)"
            @change="store.toggleSelect(tc.id)"
          />
        </div>
        <div class="col-id">
          <span class="human-id">{{ tc.human_id || tc.id?.slice(0, 8) }}</span>
        </div>
        <div class="col-title">{{ tc.title }}</div>
        <div class="col-priority">
          <span class="badge" :class="'priority-' + (tc.priority || 'medium')">
            {{ tc.priority || 'medium' }}
          </span>
        </div>
        <div class="col-status">
          <span class="badge" :class="'status-' + (tc.status || 'draft')">
            {{ tc.status || 'draft' }}
          </span>
        </div>
        <div class="col-auto">
          <span v-if="tc.automation_status" class="badge auto-badge">
            {{ tc.automation_status }}
          </span>
          <span v-else class="text-subtle">-</span>
        </div>
        <div class="col-steps text-subtle">
          {{ (tc.steps || []).length }}
        </div>
        <div class="col-date text-subtle">
          {{ formatDate(tc.updated_at) }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useQAStore } from '@/stores/qa'
import FolderTree from '@/components/testcases/FolderTree.vue'

const props = defineProps({
  projectId: { type: String, required: true }
})

const emit = defineEmits(['open-case', 'add-to-plan'])

const store = useQAStore()

const allChecked = computed(() => {
  return store.testCases.length > 0 && store.testCases.every(tc => store.selectedIds.has(tc.id))
})

function toggleAll() {
  if (allChecked.value) store.clearSelection()
  else store.selectAll()
}

function handleCreateFolder({ parentId, name }) {
  store.createFolder(name, parentId)
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

onMounted(() => {
  store.fetchFoldersTree()
  store.fetchTestCases()
})
</script>

<style scoped>
.qa-tree-layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  height: 100%;
}

.qa-sidebar {
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  overflow-y: auto;
  padding: 12px 0;
}

.qa-main {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.qa-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-color);
  gap: 8px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-select {
  padding: 5px 10px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 5px;
  color: var(--text-primary);
  font-size: 12px;
  outline: none;
  cursor: pointer;
}

.bulk-count {
  font-size: 12px;
  color: var(--accent);
  font-weight: 500;
}

.btn-bulk {
  padding: 5px 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 5px;
  color: var(--text-primary);
  font-size: 12px;
  cursor: pointer;
}
.btn-bulk:hover {
  background: var(--bg-tertiary);
}
.btn-bulk-danger {
  color: #ef4444;
}
.btn-bulk-danger:hover {
  background: rgba(239, 68, 68, 0.15);
}

.btn-export {
  padding: 5px 12px;
  background: none;
  border: 1px solid var(--border-color);
  border-radius: 5px;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
}
.btn-export:hover {
  color: var(--text-primary);
}

/* Header & rows */
.tc-header,
.tc-row {
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 8px;
  font-size: 13px;
}

.tc-header {
  height: 36px;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-color);
}

.tc-row {
  height: 42px;
  cursor: pointer;
  border-bottom: 1px solid var(--border-color);
  transition: background 0.1s;
}
.tc-row:hover {
  background: var(--bg-tertiary);
}
.tc-row.selected {
  background: var(--accent-muted);
}

.tc-empty {
  padding: 40px 16px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
}

.col-check { width: 28px; flex-shrink: 0; }
.col-id { width: 90px; flex-shrink: 0; }
.col-title { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-primary); }
.col-priority { width: 80px; flex-shrink: 0; }
.col-status { width: 80px; flex-shrink: 0; }
.col-auto { width: 90px; flex-shrink: 0; }
.col-steps { width: 50px; flex-shrink: 0; text-align: center; }
.col-date { width: 80px; flex-shrink: 0; }

.human-id {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 12px;
  padding: 2px 6px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  color: var(--accent);
}

.text-subtle {
  color: var(--text-secondary);
  font-size: 12px;
}

/* Badges */
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  text-transform: capitalize;
}

.priority-critical { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
.priority-high { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.priority-medium { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
.priority-low { background: rgba(107, 114, 128, 0.15); color: #9ca3af; }

.status-draft { background: rgba(107, 114, 128, 0.15); color: #9ca3af; }
.status-ready { background: rgba(16, 185, 129, 0.15); color: #10b981; }
.status-approved { background: var(--accent-muted); color: var(--accent); }

.auto-badge { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }

input[type="checkbox"] {
  accent-color: var(--accent);
  cursor: pointer;
}
</style>
