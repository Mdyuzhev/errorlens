import { defineStore } from 'pinia'
import { gitlabApi } from '@/services/api'

export const useGitLabStore = defineStore('gitlab', {
  state: () => ({
    connections: [],
    checking: new Set(),
    projects: new Map(),
    branches: new Map(),
    pipelines: new Map(),
    loading: false,
  }),

  actions: {
    async fetchConnections(projectId) {
      this.loading = true
      try {
        const { data } = await gitlabApi.listConnections(projectId)
        this.connections = data
      } finally {
        this.loading = false
      }
    },

    async createConnection(projectId, payload) {
      await gitlabApi.createConnection(projectId, payload)
      await this.fetchConnections(projectId)
    },

    async updateConnection(id, payload, projectId) {
      await gitlabApi.updateConnection(id, payload)
      await this.fetchConnections(projectId)
    },

    async deleteConnection(id, projectId) {
      await gitlabApi.deleteConnection(id)
      await this.fetchConnections(projectId)
    },

    async checkConnection(id) {
      this.checking.add(id)
      try {
        const { data } = await gitlabApi.checkConnection(id)
        // Update connection status inline
        const conn = this.connections.find(c => c.id === id)
        if (conn) {
          conn.last_check_ok = data.ok
          conn.last_checked_at = new Date().toISOString()
        }
        return data
      } finally {
        this.checking.delete(id)
      }
    },

    async fetchProjects(connId) {
      const { data } = await gitlabApi.listProjects(connId)
      this.projects.set(connId, data)
      return data
    },

    async fetchBranches(connId, projId) {
      const key = `${connId}:${projId}`
      const { data } = await gitlabApi.listBranches(connId, projId)
      this.branches.set(key, data)
      return data
    },

    async fetchPipelines(connId, projId, ref) {
      const key = `${connId}:${projId}`
      const { data } = await gitlabApi.listPipelines(connId, projId, ref)
      this.pipelines.set(key, data)
      return data
    },
  },
})
