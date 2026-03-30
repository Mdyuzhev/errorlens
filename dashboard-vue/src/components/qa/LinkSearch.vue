<template>
  <div class="links-section">
    <div class="links-section-header">
      <span class="links-section-title">{{ title }}</span>
    </div>

    <div v-if="items.length > 0" class="links-list">
      <div
        v-for="item in items"
        :key="item.id"
        class="link-item"
        :class="{ clickable: !!item.href }"
        @click="item.href && $emit('click-item', item)"
      >
        <span v-if="item.badge" class="link-id">{{ item.badge }}</span>
        <span class="link-title">{{ item.label }}</span>
        <button class="link-remove" @click.stop="$emit('remove', item.id)">&times;</button>
      </div>
    </div>
    <div v-else class="empty-links">{{ emptyText }}</div>

    <div class="link-search-wrap">
      <input
        v-model="query"
        class="link-search-input"
        :placeholder="placeholder"
        @input="onInput"
      />
      <div v-if="results.length > 0" class="link-search-results">
        <div
          v-for="r in results"
          :key="r.id"
          class="link-search-item"
          @click="select(r)"
        >
          <span v-if="r.badge" class="link-result-id">{{ r.badge }}</span>
          <span class="link-result-title">{{ r.label }}</span>
        </div>
      </div>
      <div v-if="loading" class="link-search-loading">Searching...</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
  emptyText: { type: String, default: 'No linked items' },
  placeholder: { type: String, default: 'Search...' },
  items: { type: Array, default: () => [] },
  searchFn: { type: Function, required: true },
  excludeIds: { type: Array, default: () => [] },
})

const emit = defineEmits(['add', 'remove', 'click-item'])

const query = ref('')
const results = ref([])
const loading = ref(false)
let timer = null

function onInput() {
  clearTimeout(timer)
  if (query.value.length < 2) { results.value = []; return }
  timer = setTimeout(doSearch, 300)
}

async function doSearch() {
  loading.value = true
  try {
    const raw = await props.searchFn(query.value)
    results.value = raw.filter(r => !props.excludeIds.includes(r.id))
  } catch (e) {
    results.value = []
  } finally {
    loading.value = false
  }
}

function select(item) {
  emit('add', item)
  query.value = ''
  results.value = []
}
</script>

<style scoped>
.links-section {
  margin-bottom: 24px;
}

.links-section-header {
  margin-bottom: 10px;
}

.links-section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.empty-links {
  color: var(--text-secondary);
  font-size: 13px;
  padding: 8px 0 10px;
}

.links-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
}

.link-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  background: var(--bg-tertiary);
  border-radius: 6px;
  font-size: 13px;
}
.link-item.clickable {
  cursor: pointer;
}
.link-item.clickable:hover .link-title {
  color: var(--accent);
}

.link-id {
  font-family: monospace;
  font-size: 11px;
  color: var(--accent);
  flex-shrink: 0;
  background: var(--bg-secondary);
  padding: 1px 6px;
  border-radius: 4px;
}

.link-title {
  flex: 1;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.link-remove {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 16px;
  padding: 0 2px;
  flex-shrink: 0;
  line-height: 1;
}
.link-remove:hover { color: #ef4444; }

.link-search-wrap {
  position: relative;
}

.link-search-input {
  width: 100%;
  padding: 7px 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
}
.link-search-input:focus { border-color: var(--accent); }
.link-search-input::placeholder { color: var(--placeholder-color); }

.link-search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  box-shadow: var(--shadow-dropdown);
  z-index: 100;
  max-height: 200px;
  overflow-y: auto;
  margin-top: 2px;
}

.link-search-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.1s;
}
.link-search-item:hover { background: var(--bg-secondary); }

.link-result-id {
  font-family: monospace;
  font-size: 11px;
  color: var(--accent);
  flex-shrink: 0;
}

.link-result-title {
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.link-search-loading {
  font-size: 12px;
  color: var(--text-secondary);
  padding: 6px 0;
}
</style>
