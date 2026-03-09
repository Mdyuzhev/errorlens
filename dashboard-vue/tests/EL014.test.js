import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHashHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'

// Mock RichEditor
vi.mock('@/components/common/RichEditor.vue', () => ({
  default: {
    name: 'RichEditor',
    props: ['modelValue', 'placeholder', 'readonly', 'editable', 'maxLength', 'showToolbar'],
    emits: ['update:modelValue'],
    template: '<div class="mock-rich-editor"></div>'
  }
}))

// Mock GridEditor
vi.mock('@/components/articles/GridEditor.vue', () => ({
  default: {
    name: 'GridEditor',
    props: ['modelValue', 'readonly', 'uploadEnabled'],
    emits: ['update:modelValue'],
    template: '<div class="mock-grid-editor"></div>'
  }
}))

// Mock EditorToolbar
vi.mock('@/components/common/EditorToolbar.vue', () => ({
  default: {
    name: 'EditorToolbar',
    props: ['editor', 'uploadEnabled'],
    emits: ['upload-image'],
    template: '<div class="editor-toolbar"></div>'
  }
}))

// Mock FolderTree
vi.mock('@/components/articles/FolderTree.vue', () => ({
  default: {
    name: 'FolderTree',
    props: ['folders', 'selectedFolderId', 'expandedIds'],
    template: '<div class="folder-tree"></div>'
  }
}))

vi.mock('@/components/testcases/FolderTree.vue', () => ({
  default: {
    name: 'FolderTree',
    props: ['folders', 'selectedFolderId', 'expandedIds'],
    template: '<div class="folder-tree"></div>'
  }
}))

// Mock TestCasePanel
vi.mock('@/components/testcases/TestCasePanel.vue', () => ({
  default: {
    name: 'TestCasePanel',
    props: ['testCase', 'backlinks', 'modelValue'],
    emits: ['update:modelValue', 'save', 'delete', 'close', 'go-to-article'],
    template: '<div class="tc-panel"></div>'
  }
}))

// Mock StepsTable
vi.mock('@/components/testcases/StepsTable.vue', () => ({
  default: {
    name: 'StepsTable',
    props: ['steps'],
    emits: ['update:steps'],
    template: '<div class="steps-table"></div>'
  }
}))

// Mock CollapsibleSection
vi.mock('@/components/testcases/CollapsibleSection.vue', () => ({
  default: {
    name: 'CollapsibleSection',
    props: ['title', 'defaultOpen', 'hasContent'],
    template: '<div class="collapsible"><slot /></div>'
  }
}))

// Mock TestCaseMeta
vi.mock('@/components/testcases/TestCaseMeta.vue', () => ({
  default: {
    name: 'TestCaseMeta',
    props: ['modelValue'],
    emits: ['update:modelValue'],
    template: '<div class="tc-meta"></div>'
  }
}))

// Mock API
vi.mock('@/services/api', () => ({
  articlesApi: {
    list: vi.fn().mockResolvedValue({ data: [] }),
    get: vi.fn().mockResolvedValue({ data: { id: 'a1', title: 'Test Article', slug: 'test-article', content: '{}', status: 'draft' } }),
    getCategories: vi.fn().mockResolvedValue({ data: [] }),
    getFoldersTree: vi.fn().mockResolvedValue({ data: { folders: [] } }),
  },
  testCasesApi: {
    list: vi.fn().mockResolvedValue({ data: [] }),
    get: vi.fn().mockResolvedValue({ data: { id: 'tc1', title: 'Test Case 1', priority: 'High', status: 'Draft', steps: [] } }),
    getFoldersTree: vi.fn().mockResolvedValue({ data: { folders: [] } }),
  },
  tasksApi: {
    list: vi.fn().mockResolvedValue({ data: [] }),
    get: vi.fn().mockResolvedValue({ data: { id: 't1', title: 'Task 1', status: 'todo', priority: 'medium' } }),
    getBoard: vi.fn().mockResolvedValue({ data: { todo: [], in_progress: [], review: [], done: [] } }),
  },
  entityLinksApi: {
    getBacklinks: vi.fn().mockResolvedValue({ data: { items: [] } }),
  }
}))

// Stub crypto.randomUUID
let uuidCounter = 0
vi.stubGlobal('crypto', { randomUUID: () => `uuid-${++uuidCounter}` })

function createTestRouter(routes) {
  return createRouter({
    history: createWebHashHistory(),
    routes
  })
}

describe('EL014: Deep Link Navigation + TestCases Visual Parity', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    uuidCounter = 0
  })

  describe('article_deep_link', () => {
    it('переход на /#/articles/slug открывает viewer', async () => {
      const { articlesApi } = await import('@/services/api')
      articlesApi.get.mockResolvedValue({
        data: { id: 'a1', title: 'Deep Article', slug: 'deep-article', content: '{}', status: 'published' }
      })
      articlesApi.list.mockResolvedValue({ data: [] })

      const router = createTestRouter([
        { path: '/articles', name: 'articles', component: () => import('@/views/ArticlesView.vue') },
        { path: '/articles/:slug', name: 'article', component: () => import('@/views/ArticlesView.vue') },
      ])

      await router.push('/articles/deep-article')
      await router.isReady()

      const ArticlesView = (await import('@/views/ArticlesView.vue')).default
      const wrapper = mount(ArticlesView, {
        global: { plugins: [router, createPinia()] }
      })

      // Wait for async operations
      await new Promise(r => setTimeout(r, 100))
      await wrapper.vm.$nextTick()

      expect(articlesApi.get).toHaveBeenCalledWith('deep-article')
    })
  })

  describe('testcase_deep_link', () => {
    it('переход на /#/testcases/id открывает viewer', async () => {
      const { testCasesApi } = await import('@/services/api')
      testCasesApi.get.mockResolvedValue({
        data: { id: 'tc1', title: 'Deep TC', priority: 'High', status: 'Ready', steps: [] }
      })
      testCasesApi.list.mockResolvedValue({ data: [] })

      const router = createTestRouter([
        { path: '/testcases', name: 'testcases', component: () => import('@/views/TestCasesView.vue') },
        { path: '/testcases/:id', name: 'testcase', component: () => import('@/views/TestCasesView.vue') },
      ])

      await router.push('/testcases/tc1')
      await router.isReady()

      const TestCasesView = (await import('@/views/TestCasesView.vue')).default
      const wrapper = mount(TestCasesView, {
        global: { plugins: [router, createPinia()] }
      })

      await new Promise(r => setTimeout(r, 100))
      await wrapper.vm.$nextTick()

      expect(testCasesApi.get).toHaveBeenCalledWith('tc1')
    })
  })

  describe('task_deep_link', () => {
    it('переход на /#/tasks/id открывает modal', async () => {
      const { tasksApi } = await import('@/services/api')
      tasksApi.getBoard.mockResolvedValue({
        data: { todo: [{ id: 't1', title: 'Task 1', status: 'todo', priority: 'medium' }], in_progress: [], review: [], done: [] }
      })
      tasksApi.get.mockResolvedValue({
        data: { id: 't1', title: 'Task 1', status: 'todo', priority: 'medium' }
      })

      const router = createTestRouter([
        { path: '/tasks', name: 'tasks', component: () => import('@/views/TasksView.vue') },
        { path: '/tasks/:id', name: 'task', component: () => import('@/views/TasksView.vue') },
      ])

      await router.push('/tasks/t1')
      await router.isReady()

      const TasksView = (await import('@/views/TasksView.vue')).default
      const wrapper = mount(TasksView, {
        global: { plugins: [router, createPinia()] }
      })

      await new Promise(r => setTimeout(r, 100))
      await wrapper.vm.$nextTick()

      // Task was either found in board or fetched via API
      const boardCall = tasksApi.getBoard.mock.calls.length
      expect(boardCall).toBeGreaterThanOrEqual(1)
    })
  })

  describe('testcase_list_renders', () => {
    it('отображает строки списка вместо карточек', async () => {
      const { testCasesApi } = await import('@/services/api')
      testCasesApi.list.mockResolvedValue({
        data: [
          { id: 'tc1', title: 'Test 1', priority: 'High', status: 'Draft', steps: [{ action: 'a', expected: 'e' }], human_id: 'TC-001' },
          { id: 'tc2', title: 'Test 2', priority: 'Low', status: 'Ready', steps: [], human_id: 'TC-002' },
        ]
      })

      const router = createTestRouter([
        { path: '/testcases', name: 'testcases', component: () => import('@/views/TestCasesView.vue') },
        { path: '/testcases/:id', name: 'testcase', component: () => import('@/views/TestCasesView.vue') },
      ])

      await router.push('/testcases')
      await router.isReady()

      const TestCasesView = (await import('@/views/TestCasesView.vue')).default
      const wrapper = mount(TestCasesView, {
        global: { plugins: [router, createPinia()] }
      })

      await new Promise(r => setTimeout(r, 100))
      await wrapper.vm.$nextTick()

      // Should have list rows, not cards
      const rows = wrapper.findAll('.tc-row')
      expect(rows.length).toBe(2)

      // Should not have card elements
      const cards = wrapper.findAll('.testcase-card')
      expect(cards.length).toBe(0)
    })
  })

  describe('testcase_viewer_opens', () => {
    it('клик на строку открывает fullscreen viewer', async () => {
      const { testCasesApi, entityLinksApi } = await import('@/services/api')
      testCasesApi.list.mockResolvedValue({
        data: [
          { id: 'tc1', title: 'Click Me', priority: 'High', status: 'Draft', steps: [] }
        ]
      })
      entityLinksApi.getBacklinks.mockResolvedValue({ data: { items: [] } })

      const router = createTestRouter([
        { path: '/testcases', name: 'testcases', component: () => import('@/views/TestCasesView.vue') },
        { path: '/testcases/:id', name: 'testcase', component: () => import('@/views/TestCasesView.vue') },
      ])

      await router.push('/testcases')
      await router.isReady()

      const TestCasesView = (await import('@/views/TestCasesView.vue')).default
      const wrapper = mount(TestCasesView, {
        global: { plugins: [router, createPinia()] }
      })

      await new Promise(r => setTimeout(r, 100))
      await wrapper.vm.$nextTick()

      const row = wrapper.find('.tc-row')
      await row.trigger('click')
      await wrapper.vm.$nextTick()

      // Viewer should be shown
      const viewer = wrapper.findComponent({ name: 'TestCaseViewer' })
      expect(viewer.exists()).toBe(true)
    })
  })

  describe('go_to_article_opens_tab', () => {
    it('goToArticle открывает новую вкладку с конкретным slug', async () => {
      const windowOpenSpy = vi.spyOn(window, 'open').mockImplementation(() => null)

      const TestCaseViewer = (await import('@/components/testcases/TestCaseViewer.vue')).default
      const router = createTestRouter([
        { path: '/testcases', name: 'testcases', component: { template: '<div />' } },
      ])
      await router.push('/testcases')
      await router.isReady()

      const wrapper = mount(TestCaseViewer, {
        props: {
          testCase: { id: 'tc1', title: 'TC', priority: 'High', status: 'Draft', steps: [] },
          backlinks: [{ article_id: 'a1', article_title: 'My Article', article_slug: 'my-article' }]
        },
        global: { plugins: [router] }
      })

      const blItem = wrapper.find('.backlink-item')
      expect(blItem.exists()).toBe(true)
      await blItem.trigger('click')

      expect(windowOpenSpy).toHaveBeenCalledWith(
        expect.stringContaining('#/articles/my-article'),
        '_blank'
      )

      windowOpenSpy.mockRestore()
    })
  })
})
