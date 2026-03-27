import { defineStore } from 'pinia'
import { tasksApi, sprintsApi, componentsApi, workLogsApi, attachmentsApi, customFieldsApi } from '@/services/api'

export const useIssuesStore = defineStore('issues', {
  state: () => ({
    tasks: [],
    board: { todo: [], in_progress: [], review: [], done: [] },
    currentTask: null,
    loading: false,
    error: null,
    activity: [],
    relations: [],
    // New Issue fields
    backlog: [],
    sprints: [],
    activeSprint: null,
    components: [],
    customFields: [],
    dashboard: null,
    dashboardLoading: false,
    burndown: [],
    velocity: [],
    treeData: [],
    treeLoading: false,
    attachments: {},
    workLogs: {},
    customValues: {},
    projectWorkLogs: [],
    projectWorkLogsLoading: false,
  }),

  actions: {
    // === Base task actions (copied from tasks store) ===
    async fetchTasks(params) {
      this.loading = true
      this.error = null
      try {
        const response = await tasksApi.list(params)
        this.tasks = response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load tasks'
      } finally {
        this.loading = false
      }
    },

    async fetchBoard(params) {
      this.loading = true
      this.error = null
      try {
        const response = await tasksApi.getBoard(params)
        this.board = response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load board'
      } finally {
        this.loading = false
      }
    },

    async fetchTask(id) {
      try {
        const response = await tasksApi.get(id)
        this.currentTask = response.data
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load task'
        return null
      }
    },

    async createTask(data) {
      try {
        const response = await tasksApi.create(data)
        await this.fetchBoard()
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to create task'
        return null
      }
    },

    async updateTask(id, data) {
      try {
        await tasksApi.update(id, data)
        await this.fetchBoard()
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to update task'
        return false
      }
    },

    async deleteTask(id) {
      try {
        await tasksApi.delete(id)
        await this.fetchBoard()
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to delete task'
        return false
      }
    },

    async moveTask(taskId, newStatus) {
      return this.updateTask(taskId, { status: newStatus })
    },

    async fetchActivity(taskId, params) {
      try {
        const response = await tasksApi.getActivity(taskId, params)
        this.activity = response.data
        return response.data
      } catch {
        this.activity = []
        return []
      }
    },

    async addComment(taskId, content) {
      try {
        const response = await tasksApi.createComment(taskId, content)
        await this.fetchActivity(taskId)
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to add comment'
        return null
      }
    },

    async fetchRelations(taskId) {
      try {
        const response = await tasksApi.getRelations(taskId)
        this.relations = response.data
        return response.data
      } catch {
        this.relations = []
        return []
      }
    },

    async createRelation(taskId, data) {
      try {
        const response = await tasksApi.createRelation(taskId, data)
        await this.fetchRelations(taskId)
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to create relation'
        return null
      }
    },

    async deleteRelation(taskId, relationId) {
      try {
        await tasksApi.deleteRelation(taskId, relationId)
        await this.fetchRelations(taskId)
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to delete relation'
        return false
      }
    },

    // === New Issue actions ===

    async fetchBacklog(params = {}) {
      try {
        const response = await tasksApi.getBacklog(params)
        this.backlog = response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load backlog'
      }
    },

    async updateRank(issueId, rank, sprintId = null) {
      try {
        await tasksApi.updateRank(issueId, { rank, sprint_id: sprintId })
        const item = this.backlog.find(t => t.id === issueId)
        if (item) item.rank = rank
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to update rank'
        return false
      }
    },

    async fetchSprints(projectId) {
      try {
        const response = await sprintsApi.list(projectId)
        this.sprints = response.data
        this.activeSprint = this.sprints.find(s => s.status === 'active') || null
      } catch { this.sprints = [] }
    },

    async createSprint(data) {
      try {
        const response = await sprintsApi.create(data)
        await this.fetchSprints(data.project_id)
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to create sprint'
        return null
      }
    },

    async startSprint(sprintId, projectId) {
      try {
        await sprintsApi.start(sprintId)
        await this.fetchSprints(projectId)
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to start sprint'
        return false
      }
    },

    async completeSprint(sprintId, nextSprintId = null, projectId) {
      try {
        await sprintsApi.complete(sprintId, { next_sprint_id: nextSprintId })
        await this.fetchSprints(projectId)
        await this.fetchBacklog({ project_id: projectId })
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to complete sprint'
        return false
      }
    },

    async fetchComponents(projectId) {
      try {
        const response = await componentsApi.list(projectId)
        this.components = response.data
      } catch { this.components = [] }
    },

    async fetchBurndown(sprintId) {
      try {
        const r = await sprintsApi.burndown(sprintId)
        this.burndown = r.data
      } catch (e) { this.burndown = [] }
    },

    async fetchVelocity(projectId, limit = 5) {
      try {
        const r = await sprintsApi.velocity(projectId, limit)
        this.velocity = r.data
      } catch (e) { this.velocity = [] }
    },

    async fetchTree(projectId) {
      this.treeLoading = true
      try {
        const r = await tasksApi.getTree(projectId)
        this.treeData = r.data
      } catch (e) {
        this.treeData = []
      } finally {
        this.treeLoading = false
      }
    },

    async fetchDashboard(projectId) {
      this.dashboardLoading = true
      try {
        const response = await tasksApi.getDashboardStats(projectId)
        this.dashboard = response.data
      } catch { this.dashboard = null }
      finally { this.dashboardLoading = false }
    },

    async fetchAttachments(issueId) {
      try {
        const response = await attachmentsApi.list(issueId)
        this.attachments[issueId] = response.data
      } catch { this.attachments[issueId] = [] }
    },

    async uploadAttachment(issueId, file) {
      const formData = new FormData()
      formData.append('file', file)
      try {
        await attachmentsApi.upload(issueId, formData)
        await this.fetchAttachments(issueId)
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Upload failed'
        return false
      }
    },

    async deleteAttachment(issueId, attId) {
      try {
        await attachmentsApi.remove(issueId, attId)
        await this.fetchAttachments(issueId)
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Delete failed'
        return false
      }
    },

    async fetchWorkLogs(issueId) {
      try {
        const response = await workLogsApi.list(issueId)
        this.workLogs[issueId] = response.data
      } catch { this.workLogs[issueId] = [] }
    },

    async fetchProjectWorkLogs(projectId, params = {}) {
      this.projectWorkLogsLoading = true
      try {
        const r = await workLogsApi.getProjectReport(projectId, params)
        this.projectWorkLogs = r.data
      } catch (e) {
        this.projectWorkLogs = []
      } finally {
        this.projectWorkLogsLoading = false
      }
    },

    async createWorkLogGlobal(data) {
      try {
        await workLogsApi.create(data.issue_id, { hours: data.hours, log_date: data.log_date, comment: data.comment })
        return true
      } catch (e) {
        return false
      }
    },

    async createWorkLog(issueId, data) {
      try {
        await workLogsApi.create(issueId, data)
        await this.fetchWorkLogs(issueId)
        if (this.currentTask?.id === issueId) {
          const updated = await tasksApi.get(issueId)
          this.currentTask = updated.data
        }
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to log work'
        return false
      }
    },
  }
})
