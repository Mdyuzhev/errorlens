import { defineStore } from 'pinia'
import { sessionsApi } from '@/services/api'

export const useSessionsStore = defineStore('sessions', {
  state: () => ({
    sessions: [],
    currentSession: null,
    loading: false,
    error: null,
    filter: 'all' // all, bug, chain
  }),

  getters: {
    filteredSessions: (state) => {
      if (state.filter === 'all') return state.sessions
      if (state.filter === 'bug') {
        return state.sessions.filter(s => s.has_errors || s.analysis?.severity)
      }
      if (state.filter === 'chain') {
        return state.sessions.filter(s => s.recorded_requests?.length > 0)
      }
      return state.sessions
    }
  },

  actions: {
    async fetchSessions() {
      this.loading = true
      this.error = null

      try {
        const response = await sessionsApi.list()
        this.sessions = response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load sessions'
      } finally {
        this.loading = false
      }
    },

    async fetchSession(id) {
      this.loading = true
      this.error = null

      try {
        const response = await sessionsApi.get(id)
        this.currentSession = response.data
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load session'
        return null
      } finally {
        this.loading = false
      }
    },

    async deleteSession(id) {
      try {
        await sessionsApi.delete(id)
        this.sessions = this.sessions.filter(s => s.id !== id)
        if (this.currentSession?.id === id) {
          this.currentSession = null
        }
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to delete session'
        return false
      }
    },

    async analyzeSession(id) {
      try {
        const response = await sessionsApi.analyze(id)
        // Update session in list
        const idx = this.sessions.findIndex(s => s.id === id)
        if (idx !== -1) {
          this.sessions[idx] = { ...this.sessions[idx], analysis: response.data }
        }
        if (this.currentSession?.id === id) {
          this.currentSession = { ...this.currentSession, analysis: response.data }
        }
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Analysis failed'
        return null
      }
    },

    setFilter(filter) {
      this.filter = filter
    }
  }
})
