import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

// Mock articles store
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

// Mock RichEditor
vi.mock('@/components/common/RichEditor.vue', () => ({
  default: {
    name: 'RichEditor',
    template: '<div class="rich-editor-mock"><slot /></div>',
    props: ['modelValue', 'placeholder', 'uploadEnabled', 'editable'],
  }
}))

// Mock FolderTree
vi.mock('@/components/articles/FolderTree.vue', () => ({
  default: {
    name: 'FolderTree',
    template: '<div class="folder-tree-mock"></div>',
    props: ['folders', 'selectedFolderId', 'expandedIds'],
  }
}))

import ArticlesView from '@/views/ArticlesView.vue'

describe('ArticlesView Autosave', () => {
  let wrapper

  beforeEach(() => {
    vi.useFakeTimers()
    setActivePinia(createPinia())
    vi.clearAllMocks()
    mockStore.updateArticle.mockResolvedValue({})

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

  it('autosave_starts_for_existing — setInterval вызван при editingArticle !== null', async () => {
    const setIntervalSpy = vi.spyOn(global, 'setInterval')

    // Simulate editFromView with existing article
    wrapper.vm.editingArticle = { id: 1, title: 'Test', content: '', category: '', status: 'draft', tags: [] }
    wrapper.vm.form = { title: 'Test', content: '', contentJson: null, category: '', status: 'draft' }
    wrapper.vm.showEditor = true
    wrapper.vm.startAutosave()

    expect(setIntervalSpy).toHaveBeenCalledWith(expect.any(Function), 60000)
    setIntervalSpy.mockRestore()
  })

  it('autosave_not_starts_for_new — setInterval НЕ вызван при editingArticle === null', async () => {
    const setIntervalSpy = vi.spyOn(global, 'setInterval')

    // Simulate createArticle (no editingArticle)
    wrapper.vm.editingArticle = null
    wrapper.vm.showEditor = true
    wrapper.vm.startAutosave()

    expect(setIntervalSpy).not.toHaveBeenCalled()
    setIntervalSpy.mockRestore()
  })

  it('autosave_stops_on_close — clearInterval вызван в closeEditor', async () => {
    const clearIntervalSpy = vi.spyOn(global, 'clearInterval')

    // Start autosave first
    wrapper.vm.editingArticle = { id: 1, title: 'Test', content: '', category: '', status: 'draft', tags: [] }
    wrapper.vm.showEditor = true
    wrapper.vm.startAutosave()

    // Mock confirm to return true (allow close)
    globalThis.confirm = vi.fn(() => true)

    wrapper.vm.closeEditor()

    expect(clearIntervalSpy).toHaveBeenCalled()
    clearIntervalSpy.mockRestore()
  })

  it('dirty_flag_on_change — isDirty становится true после изменения form.title', async () => {
    wrapper.vm.showEditor = true
    wrapper.vm.isDirty = false
    await flushPromises()

    wrapper.vm.form.title = 'Changed title'
    await flushPromises()

    // Vue deep watcher triggers on next tick
    await vi.runAllTimersAsync()
    await flushPromises()

    expect(wrapper.vm.isDirty).toBe(true)
  })

  it('dirty_flag_reset_on_save — isDirty становится false после saveArticle', async () => {
    wrapper.vm.editingArticle = { id: 1 }
    wrapper.vm.showEditor = true
    wrapper.vm.isDirty = true
    wrapper.vm.form = { title: 'Test', content: '', contentJson: null, category: '', status: 'draft' }
    wrapper.vm.tagsInput = ''

    await wrapper.vm.saveArticle()
    await flushPromises()

    expect(wrapper.vm.isDirty).toBe(false)
  })
})
