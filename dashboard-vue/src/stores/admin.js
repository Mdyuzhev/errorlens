import { defineStore } from 'pinia'
import { projectsApi, adminApi } from '@/services/api'

export const useAdminStore = defineStore('admin', {
  state: () => ({
    users: [],
    projects: [],
    selectedProject: null,
    members: [],
    loading: false,
  }),

  actions: {
    // --- Users ---
    async fetchUsers() {
      this.loading = true
      try {
        const response = await adminApi.listUsers()
        this.users = response.data
      } finally {
        this.loading = false
      }
    },

    async createUser(data) {
      await adminApi.createUser(data)
      await this.fetchUsers()
    },

    async changePassword(userId, newPassword) {
      await adminApi.changePassword(userId, newPassword)
    },

    async toggleActive(userId, isActive) {
      await adminApi.toggleActive(userId, isActive)
      const user = this.users.find(u => u.id === userId)
      if (user) user.is_active = isActive
    },

    // --- Projects ---
    async fetchProjects() {
      this.loading = true
      try {
        const response = await projectsApi.list()
        this.projects = response.data.items || response.data
      } finally {
        this.loading = false
      }
    },

    async createProject(data) {
      await projectsApi.create(data)
      await this.fetchProjects()
    },

    async deleteProject(id) {
      await projectsApi.remove(id)
      if (this.selectedProject?.id === id) {
        this.selectedProject = null
        this.members = []
      }
      await this.fetchProjects()
    },

    // --- Members ---
    async fetchMembers(projectId) {
      const response = await projectsApi.listMembers(projectId)
      this.members = response.data.items || response.data
    },

    async addMember(projectId, data) {
      await projectsApi.addMember(projectId, data)
      await this.fetchMembers(projectId)
    },

    async removeMember(projectId, userId) {
      await projectsApi.removeMember(projectId, userId)
      await this.fetchMembers(projectId)
    },

    async updateMemberRole(projectId, userId, role) {
      await projectsApi.updateMember(projectId, userId, { role })
      await this.fetchMembers(projectId)
    },
  }
})
