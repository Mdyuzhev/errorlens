import { ref, onUnmounted } from 'vue'

const MAX_RECONNECT_ATTEMPTS = 5
const INITIAL_RECONNECT_DELAY = 1000

export function useGenerationSocket(taskId) {
  const progress = ref(0)
  const total = ref(0)
  const currentEndpoint = ref('')
  const logs = ref([])
  const status = ref('idle')
  const resultId = ref(null)
  const error = ref(null)
  const reconnectAttempt = ref(0)
  let ws = null
  let reconnectTimeout = null

  function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) return

    const wsUrl = (import.meta.env.VITE_API_URL || window.location.origin).replace('http', 'ws')
    ws = new WebSocket(`${wsUrl}/ws/generation/${taskId}`)
    status.value = 'connecting'

    ws.onopen = () => {
      reconnectAttempt.value = 0
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      switch (data.type) {
        case 'started':
          status.value = 'running'
          total.value = data.total
          break
        case 'progress':
          progress.value = data.current
          total.value = data.total
          currentEndpoint.value = data.endpoint
          if (data.log) logs.value.push(data.log)
          break
        case 'completed':
          status.value = 'completed'
          resultId.value = data.result_id
          break
        case 'error':
          status.value = 'error'
          error.value = data.message
          break
      }
    }

    ws.onclose = (event) => {
      // Don't reconnect if completed, error, or intentional close
      if (status.value === 'completed' || status.value === 'error' || event.wasClean) {
        return
      }
      attemptReconnect()
    }

    ws.onerror = () => {
      // onclose will be called after onerror
    }
  }

  function attemptReconnect() {
    if (reconnectAttempt.value >= MAX_RECONNECT_ATTEMPTS) {
      status.value = 'error'
      error.value = 'Connection lost after max reconnect attempts'
      return
    }

    reconnectAttempt.value++
    const delay = INITIAL_RECONNECT_DELAY * Math.pow(2, reconnectAttempt.value - 1)
    status.value = 'connecting'

    reconnectTimeout = setTimeout(() => {
      connect()
    }, delay)
  }

  function disconnect() {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout)
      reconnectTimeout = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
  }

  onUnmounted(disconnect)

  return { progress, total, currentEndpoint, logs, status, resultId, error, reconnectAttempt, connect, disconnect }
}
