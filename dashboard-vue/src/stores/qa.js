import { defineStore } from 'pinia'
import { testCasesApi, testPlansApi, qaApi } from '@/services/api'

export const useQAStore = defineStore('qa', {
  state: () => ({
    testCases: [],
    tcTotal: 0,
    tcPage: 1,
    tcPageSize: 10,
    tcSearch: '',
    currentTestCase: null,
    treeFolders: [],
    expandedFolders: new Set(),
    selectedFolderId: null,
    loading: false,
    error: null,
    filters: { status: '', priority: '' },

    selectedIds: new Set(),
    activeTab: 'tree',

    plans: [],
    currentPlan: null,
    planRuns: [],

    allRuns: [],

    dashboard: null,
    dashboardLoading: false,

    coverage: null,
    coverageLoading: false,
  }),

  actions: {
    async fetchTestCases() {
      this.loading = true
      try {
        const params = {
          limit: this.tcPageSize,
          offset: (this.tcPage - 1) * this.tcPageSize,
        }
        if (this.selectedFolderId) params.folder_id = this.selectedFolderId
        if (this.filters.status) params.status = this.filters.status
        if (this.filters.priority) params.priority = this.filters.priority
        if (this.tcSearch) params.q = this.tcSearch
        const res = await testCasesApi.list(params)
        // New format: {items, total, limit, offset}
        if (res.data && Array.isArray(res.data.items)) {
          this.testCases = res.data.items
          this.tcTotal = res.data.total || 0
        } else {
          // Fallback for old array format
          this.testCases = Array.isArray(res.data) ? res.data : []
          this.tcTotal = this.testCases.length
        }
      } catch (e) {
        this.error = e.response?.data?.detail || 'Failed to load'
      } finally {
        this.loading = false
      }
    },

    async fetchTestCase(id) {
      try {
        const res = await testCasesApi.get(id)
        this.currentTestCase = res.data
        return res.data
      } catch { return null }
    },

    async createTestCase(data) {
      if (this.selectedFolderId) data.folder_id = this.selectedFolderId
      try {
        await testCasesApi.create(data)
        await this.fetchTestCases()
        await this.fetchFoldersTree()
        return true
      } catch (e) {
        this.error = e.response?.data?.detail || 'Failed'
        return false
      }
    },

    async updateTestCase(id, data) {
      try {
        await testCasesApi.update(id, data)
        await this.fetchTestCases()
        return true
      } catch (e) {
        this.error = e.response?.data?.detail || 'Failed'
        return false
      }
    },

    async deleteTestCase(id) {
      try {
        await testCasesApi.delete(id)
        this.testCases = this.testCases.filter(tc => tc.id !== id)
        this.selectedIds.delete(id)
        return true
      } catch { return false }
    },

    async bulkDeleteSelected() {
      for (const id of this.selectedIds) {
        await this.deleteTestCase(id)
      }
      this.selectedIds.clear()
    },

    async fetchFoldersTree() {
      try {
        const res = await testCasesApi.getFoldersTree()
        this.treeFolders = res.data.folders || []
      } catch { this.treeFolders = [] }
    },

    async createFolder(name, parentId = null) {
      try {
        await testCasesApi.createFolder({ name, parent_id: parentId })
        await this.fetchFoldersTree()
        return true
      } catch { return false }
    },

    async deleteFolder(id) {
      try {
        await testCasesApi.deleteFolder(id)
        if (this.selectedFolderId === id) this.selectedFolderId = null
        await this.fetchFoldersTree()
        await this.fetchTestCases()
        return true
      } catch { return false }
    },

    selectFolder(id) {
      this.selectedFolderId = id
      this.selectedIds.clear()
      this.tcPage = 1
      this.fetchTestCases()
    },

    setTcPage(page) {
      this.tcPage = page
      this.selectedIds.clear()
      this.fetchTestCases()
    },

    setTcSearch(q) {
      this.tcSearch = q
      this.tcPage = 1
      this.fetchTestCases()
    },

    toggleFolder(id) {
      if (this.expandedFolders.has(id)) this.expandedFolders.delete(id)
      else this.expandedFolders.add(id)
    },

    toggleSelect(id) {
      if (this.selectedIds.has(id)) this.selectedIds.delete(id)
      else this.selectedIds.add(id)
    },

    selectAll() {
      this.testCases.forEach(tc => this.selectedIds.add(tc.id))
    },

    clearSelection() {
      this.selectedIds.clear()
    },

    async fetchPlans(projectId) {
      try {
        const res = await testPlansApi.list({ project_id: projectId })
        this.plans = res.data
      } catch { this.plans = [] }
    },

    async fetchPlan(id) {
      try {
        const res = await testPlansApi.get(id)
        this.currentPlan = res.data
        return res.data
      } catch { return null }
    },

    async createPlan(data) {
      try {
        await testPlansApi.create(data)
        return true
      } catch { return false }
    },

    async addCasesToPlan(planId, caseIds) {
      try {
        await testPlansApi.addCases(planId, caseIds)
        await this.fetchPlan(planId)
        return true
      } catch { return false }
    },

    async fetchPlanRuns(planId) {
      try {
        const res = await testPlansApi.getRuns(planId)
        // Load results for each run (needed for RunsMatrix)
        const runsWithResults = await Promise.all(
          res.data.slice(0, 10).map(async (run) => {
            try {
              const detail = await testPlansApi.getRun(run.id)
              return detail.data
            } catch {
              return run
            }
          })
        )
        this.planRuns = runsWithResults
      } catch { this.planRuns = [] }
    },

    async fetchAllRuns(projectId) {
      try {
        const res = await qaApi.getProjectRuns(projectId)
        this.allRuns = res.data
      } catch { this.allRuns = [] }
    },

    async fetchDashboard(projectId) {
      this.dashboardLoading = true
      try {
        const res = await qaApi.getDashboard(projectId)
        this.dashboard = res.data
      } catch { this.dashboard = null }
      finally { this.dashboardLoading = false }
    },

    async fetchCoverage(projectId, params = {}) {
      this.coverageLoading = true
      try {
        const res = await qaApi.getCoverage(projectId, params)
        this.coverage = res.data
      } catch {
        this.coverage = null
      } finally {
        this.coverageLoading = false
      }
    },

    async exportCsv(projectId) {
      const ids = this.selectedIds.size > 0 ? [...this.selectedIds] : undefined
      const url = `/api/v1/testcases/export/csv?project_id=${projectId}` +
        (this.selectedFolderId ? `&folder_id=${this.selectedFolderId}` : '') +
        (ids ? ids.map(id => `&ids=${id}`).join('') : '')
      window.open(url, '_blank')
    },
  }
})
