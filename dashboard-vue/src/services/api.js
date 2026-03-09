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
  getFolders: () => api.get('/testcases/folders/list'),
  // Tree folders
  getFoldersTree: (params) => api.get('/testcases/folders', { params }),
  createFolder: (data) => api.post('/testcases/folders', data),
  updateFolder: (id, data) => api.put(`/testcases/folders/${id}`, data),
  deleteFolder: (id) => api.delete(`/testcases/folders/${id}`),
  moveFolder: (id, data) => api.post(`/testcases/folders/${id}/move`, data),
  moveTestCaseToFolder: (id, data) => api.post(`/testcases/${id}/move-to-folder`, data),
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
  // Images
  uploadImage: (formData) => api.post('/articles/images/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  deleteImage: (imageId) => api.delete(`/articles/images/${imageId}`),
  getArticleImages: (articleId) => api.get(`/articles/${articleId}/images`),
}

// Entity Links API — with 30s in-memory cache
const entityPreviewCache = new Map()
const CACHE_TTL = 30_000

function getCached(key) {
  const entry = entityPreviewCache.get(key)
  if (entry && Date.now() - entry.timestamp < CACHE_TTL) return entry.data
  entityPreviewCache.delete(key)
  return null
}

function setCache(key, data) {
  entityPreviewCache.set(key, { data, timestamp: Date.now() })
  if (entityPreviewCache.size > 200) {
    const now = Date.now()
    for (const [k, v] of entityPreviewCache) {
      if (now - v.timestamp > CACHE_TTL) entityPreviewCache.delete(k)
    }
  }
}

export const entityLinksApi = {
  getPreview: async (type, id) => {
    const key = `${type}:${id}`
    const cached = getCached(key)
    if (cached) return { data: cached }
    const response = await api.get(`/entities/${type}/${id}/preview`)
    setCache(key, response.data)
    return response
  },
  getBacklinks: (type, id) => api.get(`/entities/${type}/${id}/backlinks`),
}

// Test Plans API
export const testPlansApi = {
  list: (params) => api.get('/api/v1/test-plans', { params }),
  get: (id) => api.get(`/api/v1/test-plans/${id}`),
  create: (data) => api.post('/api/v1/test-plans', data),
  update: (id, data) => api.put(`/api/v1/test-plans/${id}`, data),
  remove: (id) => api.delete(`/api/v1/test-plans/${id}`),
  addCases: (id, ids) => api.post(`/api/v1/test-plans/${id}/cases`, { testcase_ids: ids }),
  removeCase: (id, tcId) => api.delete(`/api/v1/test-plans/${id}/cases/${tcId}`),
  reorderCases: (id, orderedIds) => api.put(`/api/v1/test-plans/${id}/cases/reorder`, { ordered_ids: orderedIds }),
  getRuns: (id) => api.get(`/api/v1/test-plans/${id}/runs`),
  getRun: (runId) => api.get(`/api/v1/test-plans/runs/${runId}`),
  startRun: (id, data) => api.post(`/api/v1/test-plans/${id}/runs`, data),
  recordResult: (runId, tcId, data) => api.put(`/api/v1/test-plans/runs/${runId}/results/${tcId}`, data),
  finishRun: (runId) => api.post(`/api/v1/test-plans/runs/${runId}/finish`),
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

// Projects API
export const projectsApi = {
  list: () => api.get('/projects'),
  create: (data) => api.post('/projects', data),
  update: (id, data) => api.put(`/projects/${id}`, data),
  remove: (id) => api.delete(`/projects/${id}`),
  checkKey: (key) => api.get(`/projects/check-key`, { params: { key } }),
  listMembers: (projectId) => api.get(`/projects/${projectId}/members`),
  addMember: (projectId, data) => api.post(`/projects/${projectId}/members`, data),
  updateMember: (projectId, userId, data) => api.put(`/projects/${projectId}/members/${userId}`, data),
  removeMember: (projectId, userId) => api.delete(`/projects/${projectId}/members/${userId}`),
}

// Admin API
export const adminApi = {
  listUsers: () => api.get('/admin/users'),
  createUser: (data) => api.post('/admin/users', data),
  changePassword: (userId, newPassword) => api.patch(`/admin/users/${userId}/password`, { new_password: newPassword }),
  toggleActive: (userId, isActive) => api.patch(`/admin/users/${userId}/active`, { is_active: isActive }),
}

// Notifications API
export const notificationsApi = {
  list: () => api.get('/api/v1/notifications'),
  unreadCount: () => api.get('/api/v1/notifications/unread-count'),
  markRead: (id) => api.post(`/api/v1/notifications/${id}/read`),
  markAllRead: () => api.post('/api/v1/notifications/read-all'),
}
