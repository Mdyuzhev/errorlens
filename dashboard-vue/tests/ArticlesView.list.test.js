import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const mockStore = {
  loading: false,
  articles: [],
  categories: [],
  folders: [],
  filters: {},
  selectedFolderId: null,
  expandedFolders: new Set(),
  fetchArticles: vi.fn(),
  fetchCategories: vi.fn(),
  fetchFoldersTree: vi.fn(),
  fetchArticle: vi.fn(),
  createArticle: vi.fn(),
  updateArticle: vi.fn(),
  deleteArticle: vi.fn(),
  selectFolder: vi.fn(),
  toggleFolder: vi.fn(),
  createFolder: vi.fn(),
  updateFolder: vi.fn(),
  deleteFolder: vi.fn(),
  moveFolder: vi.fn(),
  moveArticleToFolder: vi.fn(),
}

vi.mock('@/stores/articles', () => ({
  useArticlesStore: () => mockStore
}))

vi.mock('@/services/api', () => ({
  articlesApi: {
    importFile: vi.fn(),
    previewFile: vi.fn(),
  }
}))

vi.mock('@/components/common/RichEditor.vue', () => ({
  default: {
    name: 'RichEditor',
    template: '<div class="rich-editor-mock"></div>',
    props: ['modelValue', 'placeholder', 'uploadEnabled', 'editable'],
  }
}))

vi.mock('@/components/articles/FolderTree.vue', () => ({
  default: {
    name: 'FolderTree',
    template: '<div class="folder-tree-mock"></div>',
    props: ['folders', 'selectedFolderId', 'expandedIds'],
  }
}))

import ArticlesView from '@/views/ArticlesView.vue'

describe('ArticlesView List', () => {
  let wrapper

  beforeEach(() => {
    vi.useFakeTimers()
    setActivePinia(createPinia())
    vi.clearAllMocks()

    mockStore.articles = [
      { id: 1, title: 'First Article', status: 'draft', category: 'API', created_at: '2026-03-01' },
      { id: 2, title: 'Second Article', status: 'published', category: 'QA', created_at: '2026-02-28' },
    ]
    mockStore.loading = false
    mockStore.fetchArticle.mockResolvedValue({
      id: 1, title: 'First Article', content: '{"type":"doc","content":[]}',
      status: 'draft', category: 'API', tags: [], created_at: '2026-03-01'
    })

    wrapper = mount(ArticlesView, {
      global: {
        stubs: {
          FolderTree: true,
          RichEditor: { template: '<div />', props: ['modelValue', 'placeholder', 'uploadEnabled', 'editable'] },
        }
      }
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    wrapper.unmount()
  })

  it('renders_as_list — элемент .articles-list присутствует в DOM', () => {
    expect(wrapper.find('.articles-list').exists()).toBe(true)
  })

  it('no_articles_grid — элемент .articles-grid отсутствует в DOM', () => {
    expect(wrapper.find('.articles-grid').exists()).toBe(false)
  })

  it('row_click_opens_editor — клик по строке → showEditor === true', async () => {
    const row = wrapper.find('.article-row')
    await row.trigger('click')
    await flushPromises()

    expect(wrapper.vm.showEditor).toBe(true)
    expect(wrapper.vm.editingArticle).not.toBeNull()
  })

  it('filter_by_folder — fetchArticles вызван при выборе папки', async () => {
    mockStore.fetchArticles.mockClear()
    mockStore.selectedFolderId = 5
    await wrapper.vm.loadArticles()
    expect(mockStore.fetchArticles).toHaveBeenCalled()
  })

  it('empty_state — показывается при articles.length === 0', async () => {
    // Remount with empty articles
    mockStore.articles = []
    const emptyWrapper = mount(ArticlesView, {
      global: {
        stubs: {
          FolderTree: true,
          RichEditor: { template: '<div />', props: ['modelValue', 'placeholder', 'uploadEnabled', 'editable'] },
        }
      }
    })

    expect(emptyWrapper.find('.empty-state').exists()).toBe(true)
    expect(emptyWrapper.find('.articles-list').exists()).toBe(false)
    emptyWrapper.unmount()
  })
})
