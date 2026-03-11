import { defineStore } from 'pinia'
import { tasksApi, savedFiltersApi } from '@/services/api'

export const useJqlStore = defineStore('jql', {
  state: () => ({
    currentJQL: '',
    isValid: true,
    syntaxError: null,
    savedFilters: [],
    suggestions: [],
    jqlResults: [],
    loading: false,
  }),

  actions: {
    async validateJQL(jql) {
      if (!jql.trim()) {
        this.isValid = true
        this.syntaxError = null
        return
      }
      try {
        const res = await tasksApi.jqlValidate(jql)
        this.isValid = res.data.valid
        this.syntaxError = res.data.valid ? null : { message: res.data.error, position: res.data.position }
      } catch {
        this.isValid = false
      }
    },

    async executeJQL(jql, projectId) {
      if (!jql.trim()) {
        this.jqlResults = []
        return
      }
      this.loading = true
      try {
        const res = await tasksApi.list({ jql, project_id: projectId })
        this.jqlResults = res.data
        this.currentJQL = jql
      } catch (e) {
        const detail = e.response?.data?.detail
        if (detail?.error === 'jql_syntax_error') {
          this.syntaxError = { message: detail.message, position: detail.position }
          this.isValid = false
        }
        this.jqlResults = []
      } finally {
        this.loading = false
      }
    },

    async fetchSuggestions(field, query, projectId) {
      try {
        const res = await tasksApi.jqlSuggest(field, query, projectId)
        this.suggestions = res.data
      } catch {
        this.suggestions = []
      }
    },

    async askAI(text, projectId) {
      try {
        const res = await tasksApi.jqlAi(text, projectId)
        return res.data.jql
      } catch {
        return null
      }
    },

    async fetchSavedFilters(projectId) {
      try {
        const res = await savedFiltersApi.list(projectId)
        this.savedFilters = res.data
      } catch {
        this.savedFilters = []
      }
    },

    async saveFilter(name, jql, projectId, isShared = false) {
      try {
        await savedFiltersApi.create({ name, jql, project_id: projectId, is_shared: isShared })
        await this.fetchSavedFilters(projectId)
        return true
      } catch {
        return false
      }
    },

    async deleteFilter(id, projectId) {
      try {
        await savedFiltersApi.remove(id)
        await this.fetchSavedFilters(projectId)
        return true
      } catch {
        return false
      }
    },

    clearJQL() {
      this.currentJQL = ''
      this.isValid = true
      this.syntaxError = null
      this.jqlResults = []
    },
  },
})
