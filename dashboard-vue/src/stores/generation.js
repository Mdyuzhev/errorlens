import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export const useGenerationStore = defineStore('generation', () => {
  const loading = ref(false)
  const taskId = ref(null)
  const result = ref(null)
  const error = ref(null)

  async function startFromSwagger(file, options = {}) {
    loading.value = true
    error.value = null

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('framework', options.framework || 'pytest')
      formData.append('provider', options.provider || 'anthropic')
      if (options.model) formData.append('model', options.model)

      const response = await api.post('/api/v1/generation/from-swagger', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      taskId.value = response.data.task_id
      loading.value = false
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      loading.value = false
      throw err
    }
  }

  async function startFromSession(sessionId, options = {}) {
    loading.value = true
    error.value = null

    try {
      const formData = new FormData()
      formData.append('framework', options.framework || 'pytest')
      formData.append('provider', options.provider || 'anthropic')
      if (options.model) formData.append('model', options.model)

      const response = await api.post(`/api/v1/generation/from-session/${sessionId}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      taskId.value = response.data.task_id
      loading.value = false
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      loading.value = false
      throw err
    }
  }

  async function fetchResult(id) {
    try {
      const response = await api.get(`/api/v1/generation/result/${id}`)
      result.value = response.data
      return response.data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  function getDownloadUrl(id) {
    return `${import.meta.env.VITE_API_URL || ''}/api/v1/generation/download/${id}`
  }

  async function startFromEndpoints(endpoints, options = {}) {
    // TODO: Backend endpoint not implemented yet
    error.value = 'Генерация из URL endpoints пока не поддерживается. Используйте Swagger файл или сессию.'
    throw new Error(error.value)
  }

  function reset() {
    loading.value = false
    taskId.value = null
    result.value = null
    error.value = null
  }

  return { loading, taskId, result, error, startFromSwagger, startFromSession, startFromEndpoints, fetchResult, getDownloadUrl, reset }
})
