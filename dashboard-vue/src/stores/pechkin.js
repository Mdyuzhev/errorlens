import { defineStore } from 'pinia'
import { pechkinApi } from '@/services/api'

export const usePechkinStore = defineStore('pechkin', {
  state: () => ({
    collections: [],
    activeRequestId: null,
    activeRequest: null,
    activeCollectionId: null,
    response: null,
    history: [],
    variables: {},
    activeEnv: 'collection',
    loading: false,
    executing: false,
  }),
  getters: {
    resolvedVariables() {
      const result = {}
      const colId = this.activeCollectionId
      if (!colId || !this.variables[colId]) return result
      const scopes = ['global', 'collection']
      if (this.activeEnv && !scopes.includes(this.activeEnv)) scopes.push(this.activeEnv)
      for (const scope of scopes) {
        const vars = this.variables[colId]?.[scope] || {}
        for (const [k, v] of Object.entries(vars)) result[k] = v
      }
      return result
    }
  },
  actions: {
    async fetchCollections(projectId) {
      this.loading = true
      try {
        const resp = await pechkinApi.listCollections(projectId)
        this.collections = resp.data
      } finally { this.loading = false }
    },
    async createCollection(projectId, name) {
      const resp = await pechkinApi.createCollection({ project_id: projectId, name })
      this.collections.push(resp.data)
      return resp.data
    },
    async deleteCollection(id) {
      await pechkinApi.deleteCollection(id)
      this.collections = this.collections.filter(c => c.id !== id)
      if (this.activeCollectionId === id) {
        this.activeRequest = null
        this.activeRequestId = null
        this.activeCollectionId = null
      }
    },
    async createFolder(collectionId, name, parentId = null) {
      const resp = await pechkinApi.createFolder(collectionId, { name, parent_id: parentId })
      await this.fetchCollections(this.collections[0]?.project_id)
      return resp.data
    },
    async deleteFolder(id) {
      await pechkinApi.deleteFolder(id)
      const pid = this.collections[0]?.project_id
      if (pid) await this.fetchCollections(pid)
    },
    async createRequest(collectionId, data) {
      const resp = await pechkinApi.createRequest(collectionId, data)
      const pid = this.collections[0]?.project_id
      if (pid) await this.fetchCollections(pid)
      return resp.data
    },
    async openRequest(id) {
      const resp = await pechkinApi.getRequest(id)
      this.activeRequest = resp.data
      this.activeRequestId = id
      this.activeCollectionId = resp.data.collection_id
      try {
        const hist = await pechkinApi.listHistory(id)
        this.history = hist.data
      } catch (e) {
        if (e?.response?.status) this.history = []
      }
    },
    async updateRequest(id, data) {
      await pechkinApi.updateRequest(id, data)
      if (this.activeRequestId === id) Object.assign(this.activeRequest, data)
    },
    async deleteRequest(id) {
      await pechkinApi.deleteRequest(id)
      if (this.activeRequestId === id) {
        this.activeRequest = null
        this.activeRequestId = null
      }
      const pid = this.collections[0]?.project_id
      if (pid) await this.fetchCollections(pid)
    },
    async execute() {
      if (!this.activeRequest) return
      this.executing = true
      this.response = null
      try {
        const req = this.activeRequest
        const resp = await pechkinApi.execute({
          method: req.method,
          url: req.url,
          headers: req.headers || {},
          body: req.body,
          body_type: req.body_type || 'none',
          auth: req.auth || {},
          variables: this.resolvedVariables,
          request_id: req.id,
        })
        this.response = resp.data
        if (req.id) {
          const hist = await pechkinApi.listHistory(req.id)
          this.history = hist.data
        }
      } finally { this.executing = false }
    },
    async fetchVariables(collectionId) {
      const resp = await pechkinApi.listVariables(collectionId)
      const byScope = {}
      for (const v of resp.data) {
        if (!byScope[v.scope]) byScope[v.scope] = {}
        if (v.is_enabled) byScope[v.scope][v.name] = v.value
      }
      this.variables[collectionId] = byScope
    },
    async duplicateRequest(id) {
      const resp = await pechkinApi.getRequest(id)
      const req = resp.data
      const copy = { ...req, name: req.name + ' (copy)', id: undefined }
      await pechkinApi.createRequest(req.collection_id, copy)
      const pid = this.collections[0]?.project_id
      if (pid) await this.fetchCollections(pid)
    },
  }
})
