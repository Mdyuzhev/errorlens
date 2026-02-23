import { defineStore } from 'pinia'
import { testCasesApi } from '@/services/api'

export const useTestCasesStore = defineStore('testcases', {
  state: () => ({
    testCases: [],
    currentTestCase: null,
    folders: [],          // String-based folders (old)
    treeFolders: [],      // Nested tree structure (new)
    expandedFolders: new Set(),
    selectedFolderId: null,
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
        if (this.selectedFolderId) params.folder_id = this.selectedFolderId
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
        if (this.selectedFolderId) {
          data.folder_id = this.selectedFolderId
        }
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

    // Tree folder actions
    async fetchFoldersTree() {
      try {
        const response = await testCasesApi.getFoldersTree()
        this.treeFolders = response.data.folders || []
      } catch {
        this.treeFolders = []
      }
    },

    async createFolder(name, parentId = null) {
      try {
        await testCasesApi.createFolder({ name, parent_id: parentId })
        await this.fetchFoldersTree()
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to create folder'
        return false
      }
    },

    async updateFolder(id, name) {
      try {
        await testCasesApi.updateFolder(id, { name })
        await this.fetchFoldersTree()
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to update folder'
        return false
      }
    },

    async deleteFolder(id) {
      try {
        await testCasesApi.deleteFolder(id)
        if (this.selectedFolderId === id) {
          this.selectedFolderId = null
        }
        await this.fetchFoldersTree()
        await this.fetchTestCases()
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to delete folder'
        return false
      }
    },

    async moveFolder(id, newParentId) {
      try {
        await testCasesApi.moveFolder(id, { new_parent_id: newParentId })
        await this.fetchFoldersTree()
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to move folder'
        return false
      }
    },

    async moveTestCaseToFolder(tcId, folderId) {
      try {
        await testCasesApi.moveTestCaseToFolder(tcId, { folder_id: folderId })
        await this.fetchFoldersTree()
        await this.fetchTestCases()
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to move test case'
        return false
      }
    },

    toggleFolder(id) {
      if (this.expandedFolders.has(id)) {
        this.expandedFolders.delete(id)
      } else {
        this.expandedFolders.add(id)
      }
    },

    selectFolder(id) {
      this.selectedFolderId = id
      this.filters.folder = ''
      this.fetchTestCases()
    },

    setFilter(key, value) {
      this.filters[key] = value
      this.fetchTestCases()
    }
  }
})
