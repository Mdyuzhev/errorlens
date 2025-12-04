import { defineStore } from 'pinia'
import { authApi } from '@/services/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    isAuthenticated: false,
    loading: false,
    error: null
  }),

  actions: {
    async login(username, password) {
      this.loading = true
      this.error = null

      try {
        const response = await authApi.login(username, password)
        const { access_token, refresh_token } = response.data

        localStorage.setItem('access_token', access_token)
        localStorage.setItem('refresh_token', refresh_token)

        await this.fetchUser()
        this.isAuthenticated = true

        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Login failed'
        return false
      } finally {
        this.loading = false
      }
    },

    async fetchUser() {
      try {
        const response = await authApi.me()
        this.user = response.data
        this.isAuthenticated = true
      } catch {
        this.isAuthenticated = false
        this.user = null
      }
    },

    async logout() {
      try {
        await authApi.logout()
      } catch {
        // Ignore logout errors
      } finally {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        this.user = null
        this.isAuthenticated = false
      }
    },

    async checkAuth() {
      const token = localStorage.getItem('access_token')
      if (token) {
        await this.fetchUser()
      }
    }
  }
})
