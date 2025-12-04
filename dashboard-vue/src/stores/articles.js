import { defineStore } from 'pinia'
import { articlesApi } from '@/services/api'

export const useArticlesStore = defineStore('articles', {
  state: () => ({
    articles: [],
    currentArticle: null,
    categories: [],
    loading: false,
    error: null,
    filters: {
      category: '',
      status: ''
    }
  }),

  actions: {
    async fetchArticles() {
      this.loading = true
      this.error = null

      try {
        const params = {}
        if (this.filters.category) params.category = this.filters.category
        if (this.filters.status) params.status = this.filters.status

        const response = await articlesApi.list(params)
        this.articles = response.data
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

    setFilter(key, value) {
      this.filters[key] = value
      this.fetchArticles()
    }
  }
})
