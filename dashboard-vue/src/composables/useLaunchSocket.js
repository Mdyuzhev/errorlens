import { ref, onUnmounted } from 'vue'

export function useLaunchSocket(launchId) {
  const tests = ref([])
  const status = ref('idle')
  const passed = ref(0)
  const failed = ref(0)
  const skipped = ref(0)
  const total = ref(0)
  let ws = null

  function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) return

    const wsUrl = (import.meta.env.VITE_API_URL || window.location.origin).replace('http', 'ws')
    ws = new WebSocket(`${wsUrl}/ws/launches/${launchId}`)

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      switch (data.type) {
        case 'launch_started':
          status.value = 'running'
          total.value = data.total || 0
          break
        case 'launch_batch':
          status.value = 'running'
          if (data.tests) {
            tests.value = [...tests.value, ...data.tests]
          }
          passed.value = data.passed || 0
          failed.value = data.failed || 0
          skipped.value = data.skipped || 0
          total.value = data.total || tests.value.length
          break
        case 'launch_completed':
          status.value = data.status || 'completed'
          passed.value = data.passed || passed.value
          failed.value = data.failed || failed.value
          skipped.value = data.skipped || skipped.value
          total.value = data.total || total.value
          break
      }
    }

    ws.onclose = () => {}
    ws.onerror = () => {}
  }

  function disconnect() {
    if (ws) {
      ws.close()
      ws = null
    }
  }

  onUnmounted(disconnect)

  return { tests, status, passed, failed, skipped, total, connect, disconnect }
}
