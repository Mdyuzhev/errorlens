import { defineStore } from 'pinia'
import { testPlansApi } from '@/services/api'

export const useTestPlansStore = defineStore('testPlans', {
  state: () => ({
    plans: [],
    currentPlan: null,
    currentRun: null,
    runs: [],
    loading: false,
    runLoading: false,
    error: null,
  }),

  actions: {
    async fetchPlans(projectId) {
      this.loading = true
      this.error = null
      try {
        const params = projectId ? { project_id: projectId } : {}
        const response = await testPlansApi.list(params)
        this.plans = response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load plans'
      } finally {
        this.loading = false
      }
    },

    async fetchPlan(id) {
      this.loading = true
      try {
        const response = await testPlansApi.get(id)
        this.currentPlan = response.data
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load plan'
        return null
      } finally {
        this.loading = false
      }
    },

    async createPlan(data) {
      try {
        const response = await testPlansApi.create(data)
        await this.fetchPlans()
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to create plan'
        return null
      }
    },

    async updatePlan(id, data) {
      try {
        await testPlansApi.update(id, data)
        await this.fetchPlans()
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to update plan'
        return false
      }
    },

    async deletePlan(id) {
      try {
        await testPlansApi.remove(id)
        this.plans = this.plans.filter(p => p.id !== id)
        if (this.currentPlan?.id === id) this.currentPlan = null
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to delete plan'
        return false
      }
    },

    async addCases(planId, testcaseIds) {
      try {
        await testPlansApi.addCases(planId, testcaseIds)
        await this.fetchPlan(planId)
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to add cases'
        return false
      }
    },

    async removeCase(planId, testcaseId) {
      try {
        await testPlansApi.removeCase(planId, testcaseId)
        if (this.currentPlan) {
          this.currentPlan.cases = this.currentPlan.cases.filter(c => c.testcase_id !== testcaseId)
          this.currentPlan.cases_count = this.currentPlan.cases.length
        }
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to remove case'
        return false
      }
    },

    async fetchRuns(planId) {
      try {
        const response = await testPlansApi.getRuns(planId)
        this.runs = response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load runs'
      }
    },

    async fetchRun(runId) {
      this.loading = true
      try {
        const response = await testPlansApi.getRun(runId)
        this.currentRun = response.data
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load run'
        return null
      } finally {
        this.loading = false
      }
    },

    async startRun(planId, name) {
      try {
        const response = await testPlansApi.startRun(planId, { name })
        await this.fetchRuns(planId)
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to start run'
        return null
      }
    },

    async recordResult(runId, testcaseId, data) {
      this.runLoading = true
      try {
        const response = await testPlansApi.recordResult(runId, testcaseId, data)
        // Update counters from server response
        if (this.currentRun && response.data.counters) {
          this.currentRun.passed = response.data.counters.passed
          this.currentRun.failed = response.data.counters.failed
          this.currentRun.blocked = response.data.counters.blocked
          this.currentRun.skipped = response.data.counters.skipped
        }
        // Update result in local list
        if (this.currentRun?.results) {
          const idx = this.currentRun.results.findIndex(r => r.testcase_id === testcaseId)
          if (idx >= 0) {
            this.currentRun.results[idx].status = response.data.status
            this.currentRun.results[idx].comment = response.data.comment
            this.currentRun.results[idx].error_details = response.data.error_details
            this.currentRun.results[idx].executed_at = response.data.executed_at
          } else {
            this.currentRun.results.push(response.data)
          }
        }
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to record result'
        return null
      } finally {
        this.runLoading = false
      }
    },

    async finishRun(runId) {
      try {
        const response = await testPlansApi.finishRun(runId)
        if (this.currentRun) {
          this.currentRun.status = 'completed'
          this.currentRun.finished_at = response.data.finished_at
          this.currentRun.passed = response.data.passed
          this.currentRun.failed = response.data.failed
          this.currentRun.blocked = response.data.blocked
          this.currentRun.skipped = response.data.skipped
        }
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to finish run'
        return null
      }
    },
  }
})
