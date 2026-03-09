import { defineStore } from 'pinia'
import { tasksApi } from '@/services/api'

export const useTasksStore = defineStore('tasks', {
  state: () => ({
    tasks: [],
    board: {
      todo: [],
      in_progress: [],
      review: [],
      done: []
    },
    currentTask: null,
    loading: false,
    error: null,
    activity: [],
    relations: [],
  }),

  actions: {
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

    // Activity
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

    // Relations
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
  }
})
