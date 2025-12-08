import { ref, onUnmounted } from 'vue'

export function useGenerationSocket(taskId) {
  const progress = ref(0)
  const total = ref(0)
  const currentEndpoint = ref('')
  const logs = ref([])
  const status = ref('idle')
  const resultId = ref(null)
  const error = ref(null)
  let ws = null

  function connect() {
    const wsUrl = (import.meta.env.VITE_API_URL || window.location.origin).replace('http', 'ws')
    ws = new WebSocket(`${wsUrl}/ws/generation/${taskId}`)
    status.value = 'connecting'

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

    ws.onerror = () => {
      status.value = 'error'
      error.value = 'Connection error'
    }
  }

  function disconnect() {
    ws?.close()
    ws = null
  }

  onUnmounted(disconnect)

  return { progress, total, currentEndpoint, logs, status, resultId, error, connect, disconnect }
}
