<template>
  <div class="tree-node" :style="{ paddingLeft: depth * 24 + 'px' }">
    <div class="tree-node__row" @click="$emit('open', node)">
      <!-- Expand toggle -->
      <button
        v-if="node.children && node.children.length"
        class="tree-node__toggle"
        @click.stop="$emit('toggle', node.id)"
      >
        <span :class="['toggle-icon', { 'toggle-icon--open': isExpanded }]">&#9654;</span>
      </button>
      <span v-else class="tree-node__toggle-placeholder" />

      <!-- Type color dot -->
      <span
        class="tree-node__dot"
        :style="{ background: node.type_color || 'var(--accent)' }"
      />

      <!-- Human ID badge -->
      <span class="tree-node__id">{{ node.human_id }}</span>

      <!-- Title -->
      <span class="tree-node__title">{{ node.title }}</span>

      <span class="tree-node__spacer" />

      <!-- Story points -->
      <span v-if="node.story_points != null" class="tree-node__points">
        {{ node.story_points }} SP
      </span>

      <!-- Progress bar (done / total children) -->
      <span
        v-if="node.children && node.children.length"
        class="tree-node__progress"
      >
        <span class="progress-bar">
          <span
            class="progress-bar__fill"
            :style="{ width: progressPercent + '%' }"
          />
        </span>
        <span class="progress-bar__label">{{ doneCount }}/{{ node.children.length }}</span>
      </span>

      <!-- Assignee -->
      <span v-if="node.assignee_name" class="tree-node__assignee">
        {{ node.assignee_name }}
      </span>

      <!-- Status badge -->
      <span
        v-if="node.status_name"
        class="tree-node__status"
        :style="{
          background: node.status_color ? node.status_color + '22' : 'var(--accent-muted)',
          color: node.status_color || 'var(--accent)',
        }"
      >
        {{ node.status_name }}
      </span>
    </div>

    <!-- Children (recursive) -->
    <template v-if="isExpanded && node.children && node.children.length">
      <IssueTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :depth="depth + 1"
        :expanded-ids="expandedIds"
        @toggle="$emit('toggle', $event)"
        @open="$emit('open', $event)"
      />
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'

defineOptions({ name: 'IssueTreeNode' })

const props = defineProps({
  node: { type: Object, required: true },
  depth: { type: Number, default: 0 },
  expandedIds: { type: Set, default: () => new Set() },
})

defineEmits(['toggle', 'open'])

const isExpanded = computed(() => props.expandedIds.has(props.node.id))

const doneCount = computed(() => {
  if (!props.node.children) return 0
  return props.node.children.filter(c => c.is_done).length
})

const progressPercent = computed(() => {
  if (!props.node.children || !props.node.children.length) return 0
  return Math.round((doneCount.value / props.node.children.length) * 100)
})
</script>

<style scoped>
.tree-node__row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
  min-height: 36px;
}

.tree-node__row:hover {
  background: var(--bg-tertiary);
}

.tree-node__toggle {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  font-size: 10px;
  flex-shrink: 0;
}

.tree-node__toggle-placeholder {
  width: 18px;
  flex-shrink: 0;
}

.toggle-icon {
  display: inline-block;
  transition: transform 0.15s;
}

.toggle-icon--open {
  transform: rotate(90deg);
}

.tree-node__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tree-node__id {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
  flex-shrink: 0;
}

.tree-node__title {
  font-size: 14px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.tree-node__spacer {
  flex: 1;
}

.tree-node__points {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  flex-shrink: 0;
}

.tree-node__progress {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.progress-bar {
  width: 60px;
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar__fill {
  height: 100%;
  background: var(--success);
  border-radius: 3px;
  transition: width 0.2s;
}

.progress-bar__label {
  font-size: 11px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.tree-node__assignee {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  flex-shrink: 0;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tree-node__status {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
  flex-shrink: 0;
}
</style>
