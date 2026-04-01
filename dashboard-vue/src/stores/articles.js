import { defineStore } from 'pinia'
import { articlesApi } from '@/services/api'

export const useArticlesStore = defineStore('articles', {
  state: () => ({
    articles: [],
    currentArticle: null,
    categories: [],
    folders: [],
    expandedFolders: new Set(),
    selectedFolderId: null,
    breadcrumbs: {},
    folderArticles: {},
    versions: {},
    currentVersion: null,
    loading: false,
    error: null,
    filters: {
      category: '',
      status: ''
    }
  }),

  actions: {
    async fetchArticles(extraParams = {}) {
      this.loading = true
      this.error = null

      try {
        const params = {
          ...this.filters,
          folder_id: this.selectedFolderId || undefined,
          ...extraParams,
        }
        if (!params.category) delete params.category
        if (!params.status) delete params.status

        const response = await articlesApi.list(params)
        this.articles = response.data.items || response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load articles'
      } finally {
        this.loading = false
      }
    },

    async fetchArticle(slug) {
      this.loading = true
      try {
        const response = await articlesApi.get(slug)
        this.currentArticle = response.data
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load article'
        return null
      } finally {
        this.loading = false
      }
    },

    async createArticle(data) {
      try {
        if (this.selectedFolderId) {
          data.folder_id = this.selectedFolderId
        }
        const response = await articlesApi.create(data)
        await this.fetchArticles()
        return response.data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to create article'
        return null
      }
    },

    async updateArticle(id, data) {
      try {
        await articlesApi.update(id, data)
        await this.fetchArticles()
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to update article'
        return false
      }
    },

    async deleteArticle(id) {
      try {
        await articlesApi.delete(id)
        this.articles = this.articles.filter(a => a.id !== id)
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to delete article'
        return false
      }
    },

    async fetchCategories() {
      try {
        const response = await articlesApi.getCategories()
        this.categories = response.data
      } catch {
        // Ignore category fetch errors
      }
    },

    // Folder actions
    async fetchFoldersTree(params = {}) {
      try {
        const response = await articlesApi.getFoldersTree(params)
        this.folders = response.data.folders || []
      } catch {
        this.folders = []
      }
    },

    async createFolder(name, parentId = null) {
      try {
        await articlesApi.createFolder({ name, parent_id: parentId })
        await this.fetchFoldersTree()
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to create folder'
        return false
      }
    },

    async updateFolder(id, name) {
      try {
        await articlesApi.updateFolder(id, { name })
        await this.fetchFoldersTree()
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to update folder'
        return false
      }
    },

    async deleteFolder(id) {
      try {
        await articlesApi.deleteFolder(id)
        if (this.selectedFolderId === id) {
          this.selectedFolderId = null
        }
        await this.fetchFoldersTree()
        await this.fetchArticles()
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to delete folder'
        return false
      }
    },

    async moveFolder(id, newParentId) {
      try {
        await articlesApi.moveFolder(id, { new_parent_id: newParentId })
        await this.fetchFoldersTree()
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to move folder'
        return false
      }
    },

    async moveArticleToFolder(articleId, folderId) {
      try {
        await articlesApi.moveArticleToFolder(articleId, { folder_id: folderId })
        await this.fetchFoldersTree()
        await this.fetchArticles()
        return true
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to move article'
        return false
      }
    },

    toggleFolder(id) {
      if (this.expandedFolders.has(id)) {
        this.expandedFolders.delete(id)
      } else {
        this.expandedFolders.add(id)
      }
    },

    selectFolder(id) {
      this.selectedFolderId = id
      this.fetchArticles()
    },

    setFilter(key, value) {
      this.filters[key] = value
      this.fetchArticles()
    },

    // Breadcrumbs
    async fetchBreadcrumbs(articleId) {
      try {
        const response = await articlesApi.getBreadcrumbs(articleId)
        this.breadcrumbs[articleId] = response.data
      } catch {
        this.breadcrumbs[articleId] = []
      }
    },

    // Folder articles (sibling/child pages)
    async fetchFolderArticles(folderId, excludeId = null) {
      try {
        const response = await articlesApi.getFolderArticles(folderId, excludeId)
        this.folderArticles[folderId] = response.data
      } catch {
        this.folderArticles[folderId] = []
      }
    },

    // PDF export
    async downloadPdf(articleId, slug) {
      try {
        const response = await articlesApi.exportPdf(articleId)
        const url = URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
        const link = document.createElement('a')
        link.href = url
        link.download = `${slug || articleId}.pdf`
        link.click()
        URL.revokeObjectURL(url)
      } catch (error) {
        this.error = 'Failed to export PDF'
      }
    },

    // Versions
    async fetchVersions(articleId) {
      try {
        const response = await articlesApi.getVersions(articleId)
        this.versions[articleId] = response.data
      } catch {
        this.versions[articleId] = []
      }
    },

    async fetchVersion(articleId, versionId) {
      try {
        const response = await articlesApi.getVersion(articleId, versionId)
        this.currentVersion = response.data
        return response.data
      } catch {
        this.currentVersion = null
        return null
      }
    }
  }
})
