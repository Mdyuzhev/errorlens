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
    error: null
  }),

  actions: {
    async fetchTasks() {
      this.loading = true
      this.error = null

      try {
        const response = await tasksApi.list()
        this.tasks = response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load tasks'
      } finally {
        this.loading = false
      }
    },

    async fetchBoard() {
      this.loading = true
      this.error = null

      try {
        const response = await tasksApi.getBoard()
        this.board = response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load board'
      } finally {
        this.loading = false
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
    }
  }
})
