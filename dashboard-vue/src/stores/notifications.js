import { defineStore } from 'pinia'
import api from '@/services/api'

export const useNotificationsStore = defineStore('notifications', {
  state: () => ({
    notifications: [],
    unreadCount: 0,
    loading: false,
  }),

  actions: {
    async fetchUnreadCount() {
      try {
        const response = await api.get('/v1/notifications/unread-count')
        this.unreadCount = response.data.count
      } catch (error) {
        // Silently fail — polling should not disrupt UX
      }
    },

    async fetchNotifications() {
      this.loading = true
      try {
        const response = await api.get('/v1/notifications')
        this.notifications = response.data
      } catch (error) {
        // Silently fail
      } finally {
        this.loading = false
      }
    },

    async markRead(id) {
      try {
        await api.post(`/v1/notifications/${id}/read`)
        const n = this.notifications.find(n => n.id === id)
        if (n) {
          n.is_read = true
          this.unreadCount = Math.max(0, this.unreadCount - 1)
        }
      } catch (error) {
        // Silently fail
      }
    },

    async markAllRead() {
      try {
        await api.post('/v1/notifications/read-all')
        this.notifications.forEach(n => { n.is_read = true })
        this.unreadCount = 0
      } catch (error) {
        // Silently fail
      }
    },
  }
})
