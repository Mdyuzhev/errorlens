import { defineStore } from 'pinia'
import { testCasesApi } from '@/services/api'

export const useTestCasesStore = defineStore('testcases', {
  state: () => ({
    testCases: [],
    currentTestCase: null,
    folders: [],
    loading: false,
    error: null,
    filters: {
      folder: '',
      status: '',
      priority: ''
    }
  }),

  actions: {
    async fetchTestCases() {
      this.loading = true
      this.error = null

      try {
        const params = {}
        if (this.filters.folder) params.folder = this.filters.folder
        if (this.filters.status) params.status = this.filters.status
        if (this.filters.priority) params.priority = this.filters.priority

        const response = await testCasesApi.list(params)
        this.testCases = response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load test cases'
      } finally {
        this.loading = false
      }
    },

    async fetchTestCase(id) {
      this.loading = true
      try {
        const response = await testCasesApi.get(id)
        this.currentTestCase = response.data
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load test case'
        return null
      } finally {
        this.loading = false
      }
    },

    async createTestCase(data) {
      try {
        const response = await testCasesApi.create(data)
        await this.fetchTestCases()
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to create test case'
        return null
      }
    },

    async updateTestCase(id, data) {
      try {
        await testCasesApi.update(id, data)
        await this.fetchTestCases()
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to update test case'
        return false
      }
    },

    async deleteTestCase(id) {
      try {
        await testCasesApi.delete(id)
        this.testCases = this.testCases.filter(tc => tc.id !== id)
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to delete test case'
        return false
      }
    },

    async fetchFolders() {
      try {
        const response = await testCasesApi.getFolders()
        this.folders = response.data
      } catch {
        // Ignore folder fetch errors
      }
    },

    setFilter(key, value) {
      this.filters[key] = value
      this.fetchTestCases()
    }
  }
})
