import { defineStore } from 'pinia'
import { importApi } from '@/services/api'

export const useImportStore = defineStore('import', {
  state: () => ({
    step: 1,
    file: null,
    preview: null,
    previewLoading: false,
    targetProjectId: null,
    newProjectName: '',
    newProjectPrefix: 'VN',
    useNewProject: true,
    jobId: null,
    job: null,
    pollTimer: null,
  }),

  actions: {
    reset() {
      this.step = 1
      this.file = null
      this.preview = null
      this.previewLoading = false
      this.targetProjectId = null
      this.newProjectName = ''
      this.newProjectPrefix = 'VN'
      this.useNewProject = true
      this.jobId = null
      this.job = null
      this.stopPolling()
    },

    async loadPreview(file) {
      this.file = file
      this.previewLoading = true
      this.preview = null
      try {
        const formData = new FormData()
        formData.append('file', file)
        const resp = await importApi.preview(formData)
        this.preview = resp.data
        this.step = 2
      } catch (e) {
        console.error('Preview failed', e)
        throw e
      } finally {
        this.previewLoading = false
      }
    },

    async startImport(projectId) {
      this.targetProjectId = projectId
      const formData = new FormData()
      formData.append('file', this.file)
      const resp = await importApi.importTestIt(formData, projectId)
      this.jobId = resp.data.job_id
      this.step = 3
      this.startPolling()
    },

    startPolling() {
      this.stopPolling()
      this.pollTimer = setInterval(async () => {
        if (!this.jobId) return
        try {
          const resp = await importApi.getJob(this.jobId)
          this.job = resp.data
          if (resp.data.status === 'done' || resp.data.status === 'error') {
            this.stopPolling()
            this.step = 4
          }
        } catch { /* silent */ }
      }, 2000)
    },

    stopPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    },
  }
})
