import { defineStore } from 'pinia'
import api from '@/services/api'

export const useRecorderStore = defineStore('recorder', {
  state: () => ({
    isRecording: false,
    isPaused: false,
    isDone: false,
    startTime: null,
    elapsedTime: 0,
    requestCount: 0,
    consoleCount: 0,

    // Recorded data
    recordedRequests: [],
    consoleLogs: [],
    networkErrors: [],
    jsExceptions: [],

    // Session result
    sessionId: null,
    sessionUrl: null,

    // Warnings
    warning: null,

    // Timer interval
    timerInterval: null,

    // Limits
    limits: {
      maxTime: 5 * 60 * 1000,  // 5 min
      maxRequests: 100,
      maxConsole: 200,
      maxBodySize: 10 * 1024  // 10KB
    }
  }),

  getters: {
    timeRemaining: (state) => state.limits.maxTime - state.elapsedTime,
    requestsRemaining: (state) => state.limits.maxRequests - state.requestCount,
    timeProgress: (state) => Math.min((state.elapsedTime / state.limits.maxTime) * 100, 100),
    requestProgress: (state) => Math.min((state.requestCount / state.limits.maxRequests) * 100, 100),
    // Alias for widget
    duration: (state) => state.elapsedTime,
    errorCount: (state) => state.networkErrors.length + state.jsExceptions.length,
    recentErrors: (state) => {
      const errors = []
      // Add network errors (4xx, 5xx)
      for (const req of state.recordedRequests) {
        if (req.response && req.response.status >= 400) {
          errors.push({ status: req.response.status, url: req.url || req.request?.url })
        }
      }
      // Add explicit network errors
      for (const err of state.networkErrors) {
        errors.push({ status: 'ERR', url: err.url || 'unknown' })
      }
      return errors.slice(-5).reverse()
    }
  },

  actions: {
    start() {
      this.reset()
      this.isRecording = true
      this.isPaused = false
      this.startTime = Date.now()

      // Start timer
      this.timerInterval = setInterval(() => {
        if (!this.isPaused) {
          this.elapsedTime = Date.now() - this.startTime
          this.checkLimits()
        }
      }, 100)
    },

    stop() {
      this.isRecording = false
      this.isPaused = false
      clearInterval(this.timerInterval)

      // Send to backend
      this.sendSession()
    },

    togglePause() {
      this.isPaused = !this.isPaused
    },

    // Legacy aliases
    startRecording() {
      this.start()
    },

    stopRecording() {
      this.stop()
    },

    checkLimits() {
      if (this.elapsedTime >= this.limits.maxTime) {
        this.setWarning('Time limit reached (5 min)')
        this.stopRecording()
      }
      if (this.requestCount >= this.limits.maxRequests) {
        this.setWarning('Request limit reached (100)')
        this.stopRecording()
      }
    },

    addRequest(request) {
      if (this.requestCount >= this.limits.maxRequests) return

      // Truncate body if too large
      if (request.request?.body?.length > this.limits.maxBodySize) {
        request.request.body = request.request.body.slice(0, this.limits.maxBodySize) + '...[truncated]'
      }
      if (request.response?.body?.length > this.limits.maxBodySize) {
        request.response.body = request.response.body.slice(0, this.limits.maxBodySize) + '...[truncated]'
      }

      this.recordedRequests.push(request)
      this.requestCount++
    },

    addConsole(log) {
      if (this.consoleLogs.length >= this.limits.maxConsole) return
      this.consoleLogs.push(log)
      this.consoleCount++
    },

    addError(error) {
      this.networkErrors.push(error)
    },

    addException(exception) {
      this.jsExceptions.push(exception)
    },

    async sendSession() {
      try {
        const payload = {
          url: window.location.href,
          user_agent: navigator.userAgent,
          recording_duration_ms: this.elapsedTime,
          record_mode: 'all',
          console_logs: this.consoleLogs,
          network_errors: this.networkErrors,
          js_exceptions: this.jsExceptions,
          recorded_requests: this.recordedRequests
        }

        const response = await api.post('/sessions', payload)
        this.sessionId = response.data.id
        this.sessionUrl = `/#/sessions/${response.data.id}`
        this.isDone = true

      } catch (error) {
        this.setWarning('Save error: ' + error.message)
      }
    },

    setWarning(message) {
      this.warning = message
      setTimeout(() => { this.warning = null }, 5000)
    },

    reset() {
      this.isRecording = false
      this.isPaused = false
      this.isDone = false
      this.startTime = null
      this.elapsedTime = 0
      this.requestCount = 0
      this.consoleCount = 0
      this.recordedRequests = []
      this.consoleLogs = []
      this.networkErrors = []
      this.jsExceptions = []
      this.sessionId = null
      this.sessionUrl = null
      this.warning = null
      clearInterval(this.timerInterval)
    }
  }
})
