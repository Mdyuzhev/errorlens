<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h1>Sessions</h1>
      <SessionFilters v-model="currentFilter" />
    </div>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <span>Loading sessions...</span>
    </div>

    <div v-else-if="filteredSessions.length === 0" class="empty-state">
      <p>No sessions found</p>
      <p class="hint">Record a session using the bookmarklet</p>
    </div>

    <div v-else class="sessions-grid">
      <SessionCard
        v-for="session in filteredSessions"
        :key="session.id"
        :session="session"
        @select="openSession"
      />
    </div>

    <!-- Session Detail Modal -->
    <SessionDetailModal
      v-if="selectedSession"
      :session="selectedSession"
      :test-it-status="testItStatus"
      :sending-to-test-it="sendingToTestIt"
      @close="closeSession"
      @analyze="analyzeSession"
      @export="exportSession"
      @delete="deleteSession"
      @send-to-testit="sendToTestIt"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionsStore } from '@/stores/sessions'
import { sessionsApi, integrationsApi } from '@/services/api'
import SessionFilters from '@/components/dashboard/SessionFilters.vue'
import SessionCard from '@/components/dashboard/SessionCard.vue'
import SessionDetailModal from '@/components/dashboard/SessionDetailModal.vue'

const route = useRoute()
const router = useRouter()
const store = useSessionsStore()

const selectedSession = ref(null)
const testItStatus = ref({ enabled: false, connected: false })
const sendingToTestIt = ref(false)

const currentFilter = computed({
  get: () => store.filter,
  set: (value) => store.setFilter(value)
})
const loading = computed(() => store.loading)
const filteredSessions = computed(() => store.filteredSessions)

function openSession(session) {
  selectedSession.value = session
  router.push(`/sessions/${session.id}`)
}

function closeSession() {
  selectedSession.value = null
  router.push('/')
}

async function analyzeSession() {
  if (!selectedSession.value) return
  const result = await store.analyzeSession(selectedSession.value.id)
  if (result) {
    selectedSession.value = { ...selectedSession.value, analysis: result }
  }
}

async function exportSession(format, subformat) {
  if (!selectedSession.value) return
  try {
    const response = await sessionsApi.export(selectedSession.value.id, format, subformat)
    const blob = response.data
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `export-${selectedSession.value.id.slice(0, 8)}.${format === 'testit' ? (subformat || 'json') : format}`
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Export failed:', error)
  }
}

async function deleteSession() {
  if (!selectedSession.value) return
  if (confirm('Delete this session?')) {
    await store.deleteSession(selectedSession.value.id)
    closeSession()
  }
}

async function checkTestItStatus() {
  try {
    const response = await integrationsApi.testItStatus()
    testItStatus.value = response.data
  } catch (error) {
    console.error('Failed to check TestIt status:', error)
  }
}

async function sendToTestIt() {
  if (!selectedSession.value || sendingToTestIt.value) return

  sendingToTestIt.value = true
  try {
    const response = await integrationsApi.sendToTestIt(selectedSession.value.id)
    const data = response.data

    if (data.success) {
      selectedSession.value = {
        ...selectedSession.value,
        testit_url: data.testit_url,
        testit_id: data.testit_id
      }
      await store.fetchSessions()
      window.open(data.testit_url, '_blank')
    }
  } catch (error) {
    const message = error.response?.data?.detail || error.message
    alert(`Failed to send to TestIt: ${message}`)
  } finally {
    sendingToTestIt.value = false
  }
}

onMounted(async () => {
  await store.fetchSessions()
  await checkTestItStatus()

  if (route.params.id) {
    const session = await store.fetchSession(route.params.id)
    if (session) {
      selectedSession.value = session
    }
  }
})
</script>

<style scoped>
.dashboard-page {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px;
  color: var(--text-secondary);
}

.empty-state {
  text-align: center;
  padding: 60px;
  color: var(--text-secondary);
}

.empty-state .hint {
  font-size: 14px;
  margin-top: 8px;
}

.sessions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 16px;
}
</style>
