<template>
  <div class="history-panel">
    <div class="history-header">
      <h3>История генераций</h3>
      <button
        v-if="history.length > 0"
        class="clear-all-btn"
        @click="clearHistory"
        title="Очистить всю историю"
      >
        🗑️
      </button>
    </div>

    <div v-if="history.length === 0" class="empty-history">
      <div style="font-size:48px">📜</div>
      <p>История пуста</p>
      <p style="color:var(--text-secondary);font-size:13px">
        Сгенерированные тесты будут появляться здесь
      </p>
    </div>

    <div v-else class="history-list">
      <div
        v-for="item in history"
        :key="item.id"
        class="history-item"
      >
        <div class="item-meta">
          <span class="framework">{{ getFrameworkIcon(item.framework) }} {{ item.framework }}</span>
          <span class="endpoints">{{ item.endpoints }} endpoints</span>
          <span class="date">{{ formatDate(item.created_at) }}</span>
        </div>
        <div class="item-actions">
          <button
            class="action-btn"
            @click="redownload(item.result_id)"
            title="Скачать повторно"
          >
            📥
          </button>
          <button
            class="action-btn"
            @click="regenerate(item)"
            title="Регенерировать"
          >
            🔄
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const emit = defineEmits(['regenerate', 'redownload'])

const MAX_HISTORY_ITEMS = 20
const history = ref([])

onMounted(() => {
  loadHistory()
})

function loadHistory() {
  try {
    const stored = localStorage.getItem('generation_history')
    if (stored) {
      history.value = JSON.parse(stored)
    }
  } catch (e) {
    console.error('Failed to load history:', e)
    history.value = []
  }
}

function addToHistory(item) {
  const newItem = {
    id: Date.now(),
    created_at: new Date().toISOString(),
    ...item
  }

  history.value.unshift(newItem)

  if (history.value.length > MAX_HISTORY_ITEMS) {
    history.value = history.value.slice(0, MAX_HISTORY_ITEMS)
  }

  saveHistory()
}

function saveHistory() {
  try {
    localStorage.setItem('generation_history', JSON.stringify(history.value))
  } catch (e) {
    console.error('Failed to save history:', e)
  }
}

function clearHistory() {
  if (confirm('Очистить всю историю генераций?')) {
    history.value = []
    localStorage.removeItem('generation_history')
  }
}

function redownload(resultId) {
  emit('redownload', resultId)
}

function regenerate(item) {
  emit('regenerate', item)
}

function getFrameworkIcon(framework) {
  const icons = {
    pytest: '🐍',
    restassured: '☕',
    postman: '📮',
    cypress: '🌲',
    k6: '⚡'
  }
  return icons[framework] || '📄'
}

function formatDate(dateStr) {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMins < 1) return 'Только что'
  if (diffMins < 60) return `${diffMins} мин назад`
  if (diffHours < 24) return `${diffHours} ч назад`
  if (diffDays < 7) return `${diffDays} дн назад`

  return date.toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}

defineExpose({
  addToHistory
})
</script>

<style scoped>
.history-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--text-primary);
}

.clear-all-btn {
  padding: 6px 10px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.2s;
}

.clear-all-btn:hover {
  border-color: var(--error);
  background: rgba(244, 67, 54, 0.05);
}

.empty-history {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.empty-history p:first-of-type {
  color: var(--text-primary);
  font-weight: 600;
  margin: 12px 0 4px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  max-height: calc(100vh - 200px);
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  transition: all 0.2s;
}

.history-item:hover {
  background: var(--bg-tertiary);
  border-color: rgba(102, 126, 234, 0.3);
}

.item-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.framework {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
}

.endpoints {
  font-size: 12px;
  color: var(--text-secondary);
}

.date {
  font-size: 11px;
  color: var(--text-secondary);
}

.item-actions {
  display: flex;
  gap: 6px;
}

.action-btn {
  padding: 6px 10px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.2s;
}

.action-btn:hover {
  border-color: var(--accent);
  background: rgba(102, 126, 234, 0.05);
}

.history-list::-webkit-scrollbar {
  width: 6px;
}

.history-list::-webkit-scrollbar-track {
  background: var(--bg-secondary);
}

.history-list::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
}

.history-list::-webkit-scrollbar-thumb:hover {
  background: var(--text-secondary);
}
</style>
