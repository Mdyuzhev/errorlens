<template>
  <div
    v-if="state.active"
    class="entity-mention-popup"
    :style="popupStyle"
  >
    <div class="popup-header">Mention entity</div>
    <div
      v-for="(item, idx) in state.items"
      :key="`${item.entityType}-${item.entityId}`"
      class="popup-item"
      :class="{ selected: idx === state.selectedIndex }"
      @mouseenter="state.selectedIndex = idx"
      @click="selectItem(item)"
    >
      <span class="item-icon">{{ item.icon }}</span>
      <div class="item-info">
        <span class="item-title">{{ item.entityTitle }}</span>
        <span class="item-type">{{ item.typeLabel }}</span>
      </div>
      <span v-if="item.status" class="item-status" :class="'status-' + item.status?.toLowerCase().replace(/\\s+/g, '-')">
        {{ item.status }}
      </span>
    </div>
    <div v-if="state.items.length === 0 && state.query" class="popup-empty">
      No results
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { suggestionState } from './EntityMentionSuggestion.js'

const state = suggestionState

const popupStyle = computed(() => {
  if (!state.clientRect) return {}
  const rect = typeof state.clientRect === 'function' ? state.clientRect() : state.clientRect
  if (!rect) return {}
  return {
    position: 'fixed',
    left: `${rect.left}px`,
    top: `${rect.bottom + 4}px`,
    zIndex: 9999,
  }
})

function selectItem(item) {
  if (state.command) {
    state.command(item)
  }
}
</script>

<style scoped>
.entity-mention-popup {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: var(--shadow-dropdown);
  min-width: 280px;
  max-width: 400px;
  max-height: 300px;
  overflow-y: auto;
  padding: 4px;
}

.popup-header {
  padding: 6px 10px;
  font-size: 11px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.popup-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.1s;
}

.popup-item:hover,
.popup-item.selected {
  background: rgba(99, 102, 241, 0.15);
}

.item-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.item-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.item-title {
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-type {
  font-size: 11px;
  color: var(--text-secondary);
}

.item-status {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 8px;
  background: var(--bg-secondary);
  flex-shrink: 0;
}

.popup-empty {
  padding: 12px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
}

/* Status colors */
.status-draft { color: #f59e0b; }
.status-published { color: #10b981; }
.status-ready { color: #3b82f6; }
.status-approved { color: #10b981; }
.status-todo { color: #9ca3af; }
.status-in-progress, .status-in_progress { color: #3b82f6; }
.status-review { color: #f59e0b; }
.status-done { color: #10b981; }
</style>
