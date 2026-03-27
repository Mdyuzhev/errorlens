<template>
  <div class="issue-tree">
    <!-- Toolbar -->
    <div class="issue-tree__toolbar">
      <div class="issue-tree__actions">
        <button class="btn-sm" @click="expandAll">Expand All</button>
        <button class="btn-sm" @click="collapseAll">Collapse All</button>
      </div>
      <span class="issue-tree__summary">
        {{ totalCount }} items
      </span>
    </div>

    <!-- Loading -->
    <div v-if="store.treeLoading" class="issue-tree__loading">
      Loading tree...
    </div>

    <!-- Empty -->
    <div v-else-if="!store.treeData.length" class="issue-tree__empty">
      No items to display
    </div>

    <!-- Tree -->
    <div v-else class="issue-tree__body">
      <IssueTreeNode
        v-for="node in store.treeData"
        :key="node.id"
        :node="node"
        :depth="0"
        :expanded-ids="expandedIds"
        @toggle="toggleNode"
        @open="(id) => $emit('open-task', id)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useIssuesStore } from '@/stores/issues'
import IssueTreeNode from './IssueTreeNode.vue'

const props = defineProps({
  projectId: { type: String, default: null },
})

defineEmits(['open-task'])

const store = useIssuesStore()
const expandedIds = ref(new Set())

function toggleNode(id) {
  const next = new Set(expandedIds.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  expandedIds.value = next
}

function collectAllIds(nodes) {
  const ids = []
  for (const n of nodes) {
    if (n.children && n.children.length) {
      ids.push(n.id)
      ids.push(...collectAllIds(n.children))
    }
  }
  return ids
}

function expandAll() {
  expandedIds.value = new Set(collectAllIds(store.treeData))
}

function collapseAll() {
  expandedIds.value = new Set()
}

const totalCount = computed(() => {
  function count(nodes) {
    let c = 0
    for (const n of nodes) {
      c += 1
      if (n.children) c += count(n.children)
    }
    return c
  }
  return count(store.treeData)
})

async function load() {
  if (!props.projectId) return
  await store.fetchTree(props.projectId)
  // Auto-expand first level
  const firstLevel = new Set()
  for (const n of store.treeData) {
    if (n.children && n.children.length) {
      firstLevel.add(n.id)
    }
  }
  expandedIds.value = firstLevel
}

onMounted(load)

watch(() => props.projectId, load)
</script>

<style scoped>
.issue-tree {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.issue-tree__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.issue-tree__actions {
  display: flex;
  gap: 8px;
}

.btn-sm {
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  cursor: pointer;
  transition: background 0.15s;
}

.btn-sm:hover {
  background: var(--bg-tertiary);
}

.issue-tree__summary {
  font-size: 13px;
  color: var(--text-secondary);
}

.issue-tree__loading,
.issue-tree__empty {
  padding: 32px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 14px;
}

.issue-tree__body {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 8px 0;
}
</style>
