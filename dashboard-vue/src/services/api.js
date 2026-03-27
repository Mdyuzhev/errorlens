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
  getBoard: (params) => api.get('/tasks/board', { params }),
  getBoardByType: (typeSlug, params) => api.get(`/tasks/board/${typeSlug}`, { params }),
  getChildren: (id) => api.get(`/tasks/${id}/children`),
  getAllowedTransitions: (id) => api.get(`/tasks/${id}/allowed-transitions`),
  moveStatus: (id, statusId) => api.patch(`/tasks/${id}/move-status`, { status_id: statusId }),
  // Activity & Comments
  getActivity: (id, params) => api.get(`/tasks/${id}/activity`, { params }),
  createComment: (id, content) => api.post(`/tasks/${id}/comments`, { content }),
  updateComment: (taskId, commentId, content) => api.put(`/tasks/${taskId}/comments/${commentId}`, { content }),
  deleteComment: (taskId, commentId) => api.delete(`/tasks/${taskId}/comments/${commentId}`),
  // Relations
  getRelations: (id) => api.get(`/tasks/${id}/relations`),
  createRelation: (id, data) => api.post(`/tasks/${id}/relations`, data),
  deleteRelation: (taskId, relationId) => api.delete(`/tasks/${taskId}/relations/${relationId}`),
  // JQL
  jqlValidate: (jql) => api.get('/tasks/jql-validate', { params: { jql } }),
  jqlSuggest: (field, query, projectId) => api.get('/tasks/jql-suggest', { params: { field, query, project_id: projectId } }),
  jqlAi: (query, projectId) => api.post('/tasks/jql-ai', { query, project_id: projectId }),
  // Issues extensions
  getBacklog: (params) => api.get('/tasks/backlog', { params }),
  updateRank: (id, data) => api.patch(`/tasks/${id}/rank`, data),
  getDashboardStats: (projectId) => api.get('/tasks/dashboard/stats', { params: { project_id: projectId } }),
  getTree: (projectId) => api.get('/tasks/tree', { params: { project_id: projectId } }),
}

// Saved Filters API
export const savedFiltersApi = {
  list: (projectId) => api.get('/saved-filters', { params: { project_id: projectId } }),
  create: (data) => api.post('/saved-filters', data),
  update: (id, data) => api.put(`/saved-filters/${id}`, data),
  remove: (id) => api.delete(`/saved-filters/${id}`),
}

// Task Settings API
export const taskSettingsApi = {
  getTypes: (projectId) => api.get('/task-settings/types', { params: { project_id: projectId } }),
  createType: (projectId, data) => api.post('/task-settings/types', data, { params: { project_id: projectId } }),
  updateType: (typeId, data) => api.put(`/task-settings/types/${typeId}`, data),
  getStatuses: (typeId, projectId) => api.get(`/task-settings/types/${typeId}/statuses`, { params: { project_id: projectId } }),
  createStatus: (typeId, projectId, data) => api.post(`/task-settings/types/${typeId}/statuses`, data, { params: { project_id: projectId } }),
  updateStatus: (statusId, data) => api.put(`/task-settings/statuses/${statusId}`, data),
  deleteStatus: (statusId) => api.delete(`/task-settings/statuses/${statusId}`),
  getTransitions: (typeId, projectId) => api.get(`/task-settings/types/${typeId}/transitions`, { params: { project_id: projectId } }),
  createTransition: (typeId, projectId, data) => api.post(`/task-settings/types/${typeId}/transitions`, data, { params: { project_id: projectId } }),
  updateTransition: (transitionId, data) => api.put(`/task-settings/transitions/${transitionId}`, data),
  deleteTransition: (typeId, data) => api.delete(`/task-settings/types/${typeId}/transitions`, { data }),
  seedDefaults: (projectId) => api.post('/task-settings/seed', null, { params: { project_id: projectId } }),
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
  // Breadcrumbs
  getBreadcrumbs: (articleId) => api.get(`/articles/${articleId}/breadcrumbs`),
  // Folder articles (child pages)
  getFolderArticles: (folderId, excludeId = null) =>
    api.get(`/articles/folders/${folderId}/articles`, {
      params: excludeId ? { exclude: excludeId } : {}
    }),
  // PDF export — blob response
  exportPdf: (articleId) =>
    api.get(`/articles/${articleId}/export/pdf`, { responseType: 'blob' }),
  // Versions
  getVersions: (articleId) => api.get(`/articles/${articleId}/versions`),
  getVersion: (articleId, versionId) =>
    api.get(`/articles/${articleId}/versions/${versionId}`),
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
  list: (params) => api.get('/v1/test-plans', { params }),
  get: (id) => api.get(`/v1/test-plans/${id}`),
  create: (data) => api.post('/v1/test-plans', data),
  update: (id, data) => api.put(`/v1/test-plans/${id}`, data),
  remove: (id) => api.delete(`/v1/test-plans/${id}`),
  addCases: (id, ids) => api.post(`/v1/test-plans/${id}/cases`, { testcase_ids: ids }),
  removeCase: (id, tcId) => api.delete(`/v1/test-plans/${id}/cases/${tcId}`),
  reorderCases: (id, orderedIds) => api.put(`/v1/test-plans/${id}/cases/reorder`, { ordered_ids: orderedIds }),
  getRuns: (id) => api.get(`/v1/test-plans/${id}/runs`),
  getRun: (runId) => api.get(`/v1/test-plans/runs/${runId}`),
  startRun: (id, data) => api.post(`/v1/test-plans/${id}/runs`, data),
  recordResult: (runId, tcId, data) => api.put(`/v1/test-plans/runs/${runId}/results/${tcId}`, data),
  finishRun: (runId) => api.post(`/v1/test-plans/runs/${runId}/finish`),
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
  list: () => api.get('/v1/notifications'),
  unreadCount: () => api.get('/v1/notifications/unread-count'),
  markRead: (id) => api.post(`/v1/notifications/${id}/read`),
  markAllRead: () => api.post('/v1/notifications/read-all'),
}

// Automations API
export const automationsApi = {
  getRules: (projectId) => api.get('/v1/automations/rules', { params: { project_id: projectId } }),
  createRule: (data) => api.post('/v1/automations/rules', data),
  updateRule: (id, data) => api.put(`/v1/automations/rules/${id}`, data),
  deleteRule: (id) => api.delete(`/v1/automations/rules/${id}`),
  getRuleRuns: (ruleId) => api.get(`/v1/automations/rules/${ruleId}/runs`),
  getTaskRuns: (taskId) => api.get('/v1/automations/runs', { params: { task_id: taskId, limit: 5 } }),
  getRun: (id) => api.get(`/v1/automations/runs/${id}`),
}

// Sprints API
export const sprintsApi = {
  list: (projectId, status = null) =>
    api.get('/api/v1/sprints', { params: { project_id: projectId, status } }),
  create: (data) => api.post('/api/v1/sprints', data),
  update: (id, data) => api.put(`/api/v1/sprints/${id}`, data),
  remove: (id) => api.delete(`/api/v1/sprints/${id}`),
  start: (id) => api.post(`/api/v1/sprints/${id}/start`),
  complete: (id, data) => api.post(`/api/v1/sprints/${id}/complete`, data),
  burndown: (id) => api.get(`/api/v1/sprints/${id}/burndown`),
  velocity: (projectId, limit = 5) =>
    api.get('/api/v1/sprints/velocity', { params: { project_id: projectId, limit } }),
}

// Components API
export const componentsApi = {
  list: (projectId) => api.get('/api/v1/components', { params: { project_id: projectId } }),
  create: (data) => api.post('/api/v1/components', data),
  update: (id, data) => api.put(`/api/v1/components/${id}`, data),
  remove: (id) => api.delete(`/api/v1/components/${id}`),
}

// Work Logs API
export const workLogsApi = {
  list: (issueId) => api.get(`/api/v1/issues/${issueId}/work-logs`),
  create: (issueId, data) => api.post(`/api/v1/issues/${issueId}/work-log`, data),
  remove: (issueId, logId) => api.delete(`/api/v1/issues/${issueId}/work-logs/${logId}`),
  getProjectReport: (projectId, params = {}) => api.get('/api/v1/work-logs/project', { params: { project_id: projectId, ...params } }),
}

// Attachments API
export const attachmentsApi = {
  list: (issueId) => api.get(`/api/v1/issues/${issueId}/attachments`),
  upload: (issueId, formData) =>
    api.post(`/api/v1/issues/${issueId}/attachments`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  remove: (issueId, attId) => api.delete(`/api/v1/issues/${issueId}/attachments/${attId}`),
}

// Custom Fields API
export const customFieldsApi = {
  listFields: (projectId, taskTypeId = null) =>
    api.get('/api/v1/custom-fields', { params: { project_id: projectId, task_type_id: taskTypeId } }),
  createField: (data) => api.post('/api/v1/custom-fields', data),
  updateField: (id, data) => api.put(`/api/v1/custom-fields/${id}`, data),
  deleteField: (id) => api.delete(`/api/v1/custom-fields/${id}`),
  getValues: (issueId) => api.get(`/api/v1/custom-fields/values/${issueId}`),
  setValues: (issueId, values) => api.put(`/api/v1/custom-fields/values/${issueId}`, { values }),
}

// GitLab API
export const gitlabApi = {
  listConnections: (projectId) => api.get('/v1/gitlab/connections', { params: { project_id: projectId } }),
  createConnection: (projectId, data) => api.post('/v1/gitlab/connections', data, { params: { project_id: projectId } }),
  updateConnection: (id, data) => api.put(`/v1/gitlab/connections/${id}`, data),
  deleteConnection: (id) => api.delete(`/v1/gitlab/connections/${id}`),
  checkConnection: (id) => api.post(`/v1/gitlab/connections/${id}/check`),
  listProjects: (connId) => api.get(`/v1/gitlab/connections/${connId}/projects`),
  listPipelines: (connId, projId, ref) => api.get(`/v1/gitlab/connections/${connId}/projects/${projId}/pipelines`, { params: { ref } }),
  listBranches: (connId, projId) => api.get(`/v1/gitlab/connections/${connId}/projects/${projId}/branches`),
}

export const issuesApi = tasksApi

// QA API
export const qaApi = {
  getDashboard: (projectId) =>
    api.get('/api/v1/qa/dashboard', { params: { project_id: projectId } }),
  getProjectRuns: (projectId) =>
    api.get(`/v1/test-plans/project/${projectId}/runs`),
  getCoverage: (projectId, params = {}) =>
    api.get('/api/v1/qa/coverage', {
      params: { project_id: projectId, ...params }
    }),
  exportCsv: (projectId, folderId, ids) => {
    const params = new URLSearchParams({ project_id: projectId })
    if (folderId) params.append('folder_id', folderId)
    if (ids) ids.forEach(id => params.append('ids', id))
    return api.get(`/testcases/export/csv?${params}`, { responseType: 'blob' })
  },
}
