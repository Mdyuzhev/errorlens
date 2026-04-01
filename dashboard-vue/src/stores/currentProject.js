import { defineStore } from 'pinia'
import { projectsApi } from '@/services/api'

const STORAGE_KEY = 'errorlens:current_project_id'

export const useCurrentProjectStore = defineStore('currentProject', {
  state: () => ({
    projects: [],
    currentProject: null,
    loading: false,
  }),

  getters: {
    currentProjectId: (state) => state.currentProject?.id ?? null,
    currentProjectKey: (state) => state.currentProject?.key ?? '',
    hasProjects: (state) => state.projects.length > 0,
  },

  actions: {
    async fetchProjects() {
      this.loading = true
      try {
        const res = await projectsApi.list()
        const raw = Array.isArray(res.data) ? res.data : (res.data?.items || [])
        // Дедупликация по id
        const seen = new Set()
        this.projects = raw.filter(p => {
          if (seen.has(p.id)) return false
          seen.add(p.id)
          return true
        })
      } catch (e) {
        console.error('[currentProject] fetchProjects error', e)
        this.projects = []
      } finally {
        this.loading = false
      }
    },

    setProject(project) {
      this.currentProject = project
      if (project?.id) {
        localStorage.setItem(STORAGE_KEY, project.id)
      }
    },

    async init() {
      await this.fetchProjects()
      if (!this.projects.length) return

      const savedId = localStorage.getItem(STORAGE_KEY)
      if (savedId) {
        const found = this.projects.find(p => p.id === savedId)
        if (found) {
          this.currentProject = found
          return
        }
      }
      // Fallback — первый проект
      this.currentProject = this.projects[0]
      localStorage.setItem(STORAGE_KEY, this.projects[0].id)
    },
  },
})
