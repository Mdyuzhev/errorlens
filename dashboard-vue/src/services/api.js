import axios from 'axios'

// In production (Railway), FastAPI serves directly without /api prefix
// In development with nginx, /api is proxied to backend
const API_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor - add token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor - handle 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_URL}/auth/refresh`, {
            refresh_token: refreshToken
          })

          const { access_token, refresh_token } = response.data
          localStorage.setItem('access_token', access_token)
          localStorage.setItem('refresh_token', refresh_token)

          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return api(originalRequest)
        } catch (refreshError) {
          // Refresh failed - logout
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/#/login'
        }
      } else {
        window.location.href = '/#/login'
      }
    }

    return Promise.reject(error)
  }
)

export default api

// Auth API
export const authApi = {
  login: (username, password) => api.post('/auth/login', { username, password }),
  refresh: (refreshToken) => api.post('/auth/refresh', { refresh_token: refreshToken }),
  me: () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout')
}

// Sessions API
export const sessionsApi = {
  list: (params) => api.get('/sessions', { params }),
  get: (id) => api.get(`/sessions/${id}`),
  delete: (id) => api.delete(`/sessions/${id}`),
  export: (id, format, subformat) => {
    let url = `/sessions/${id}/export/${format}`
    if (subformat) url += `?format=${subformat}`
    return api.get(url, { responseType: 'blob' })
  },
  analyze: (id) => api.post('/analyze/rerun', { session_id: id })
}

// Test Cases API
export const testCasesApi = {
  list: (params) => api.get('/testcases', { params }),
  get: (id) => api.get(`/testcases/${id}`),
  create: (data) => api.post('/testcases', data),
  update: (id, data) => api.put(`/testcases/${id}`, data),
  delete: (id) => api.delete(`/testcases/${id}`),
  getFolders: () => api.get('/testcases/folders/list')
}

// Tasks API
export const tasksApi = {
  list: (params) => api.get('/tasks', { params }),
  get: (id) => api.get(`/tasks/${id}`),
  create: (data) => api.post('/tasks', data),
  update: (id, data) => api.put(`/tasks/${id}`, data),
  delete: (id) => api.delete(`/tasks/${id}`),
  getBoard: () => api.get('/tasks/board')
}

// Articles API
export const articlesApi = {
  list: (params) => api.get('/articles', { params }),
  get: (slug) => api.get(`/articles/${slug}`),
  create: (data) => api.post('/articles', data),
  update: (id, data) => api.put(`/articles/${id}`, data),
  delete: (id) => api.delete(`/articles/${id}`),
  getCategories: () => api.get('/articles/categories/list'),
  // Folders
  getFoldersTree: (params) => api.get('/articles/folders', { params }),
  createFolder: (data) => api.post('/articles/folders', data),
  updateFolder: (id, data) => api.put(`/articles/folders/${id}`, data),
  deleteFolder: (id) => api.delete(`/articles/folders/${id}`),
  moveFolder: (id, data) => api.post(`/articles/folders/${id}/move`, data),
  moveArticleToFolder: (id, data) => api.post(`/articles/${id}/move-to-folder`, data),
  // Import
  importFile: (formData) => api.post('/articles/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  previewFile: (formData) => api.post('/articles/import/preview', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
}

// Test Runs API
export const testRunsApi = {
  list: (limit = 5) => api.get('/test-runs', { params: { limit } }),
  get: (id) => api.get(`/test-runs/${id}`),
  getStats: () => api.get('/test-runs/stats/summary'),
  run: (type, sessionId) => api.post(`/tests/run/${type}`, { session_id: sessionId }),
  status: (testId) => api.get(`/tests/${testId}/status`)
}

// Integrations API
export const integrationsApi = {
  // TestIt
  testItStatus: () => api.get('/integrations/testit/status'),
  sendToTestIt: (sessionId) => api.post(`/sessions/${sessionId}/send-to-testit`)
}
