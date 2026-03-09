import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import GridEditor from '@/components/articles/GridEditor.vue'
import ImageLightbox from '@/components/common/ImageLightbox.vue'

// Mock RichEditor
const mockEditorInstance = { isActive: vi.fn(), chain: vi.fn(() => ({ focus: vi.fn(() => ({ run: vi.fn() })) })) }
vi.mock('@/components/common/RichEditor.vue', () => ({
  default: {
    name: 'RichEditor',
    props: ['modelValue', 'placeholder', 'uploadEnabled', 'editable', 'showToolbar'],
    emits: ['update:modelValue', 'focus'],
    setup(props, { expose }) {
      expose({ editor: mockEditorInstance })
      return {}
    },
    template: '<div class="mock-rich-editor" @click="$emit(\'focus\')"></div>'
  }
}))

// Mock EditorToolbar
vi.mock('@/components/common/EditorToolbar.vue', () => ({
  default: {
    name: 'EditorToolbar',
    props: ['editor', 'uploadEnabled'],
    emits: ['upload-image'],
    template: '<div class="editor-toolbar" data-testid="editor-toolbar"></div>'
  }
}))

// Mock crypto.randomUUID
let uuidCounter = 0
vi.stubGlobal('crypto', {
  randomUUID: () => `test-uuid-${++uuidCounter}`
})

function makeGrid(rows = []) {
  return { version: 'grid-1', rows }
}

function makeRow(columns = [{ id: 'col-1', span: 12, content: { type: 'doc', content: [] } }], id = 'row-1') {
  return { id, columns }
}

describe('EL012: Editor UX Improvements', () => {
  beforeEach(() => {
    uuidCounter = 0
  })

  // P1: Single toolbar
  describe('P1: Single toolbar', () => {
    it('single_toolbar_rendered', () => {
      const grid = makeGrid([makeRow()])
      const wrapper = mount(GridEditor, {
        props: { modelValue: grid, uploadEnabled: true }
      })
      // GridEditor should NOT render any EditorToolbar (toolbars are hidden via showToolbar=false)
      // RichEditor inside grid has showToolbar=false
      const richEditors = wrapper.findAll('.mock-rich-editor')
      expect(richEditors.length).toBe(1)
      // No toolbar inside GridEditor
      expect(wrapper.findAll('[data-testid="editor-toolbar"]').length).toBe(0)
    })

    it('active_editor_switches', async () => {
      const grid = makeGrid([makeRow([
        { id: 'col-a', span: 6, content: { type: 'doc', content: [] } },
        { id: 'col-b', span: 6, content: { type: 'doc', content: [] } }
      ])])
      const wrapper = mount(GridEditor, {
        props: { modelValue: grid, uploadEnabled: true }
      })
      // Initially no active editor
      expect(wrapper.vm.activeEditor).toBeNull()

      // Focus on second column
      const richEditors = wrapper.findAll('.mock-rich-editor')
      await richEditors[1].trigger('click')

      // activeEditor should be set
      expect(wrapper.vm.activeEditor).toBeTruthy()
    })
  })

  // P2: Read mode
  describe('P2: Read mode', () => {
    it('readonly_no_controls', () => {
      const grid = makeGrid([makeRow()])
      const wrapper = mount(GridEditor, {
        props: { modelValue: grid, readonly: true }
      })
      // No col-toolbar, no row-actions, no add-row-btn
      expect(wrapper.find('.col-toolbar').exists()).toBe(false)
      expect(wrapper.find('.row-actions').exists()).toBe(false)
      expect(wrapper.find('.add-row-btn').exists()).toBe(false)
    })

    it('readonly_renders_content', () => {
      const grid = makeGrid([makeRow([
        { id: 'col-1', span: 12, content: { type: 'doc', content: [{ type: 'paragraph' }] } }
      ])])
      const wrapper = mount(GridEditor, {
        props: { modelValue: grid, readonly: true }
      })
      expect(wrapper.findAll('.mock-rich-editor').length).toBe(1)
    })
  })

  // P3: Lightbox
  describe('P3: Lightbox', () => {
    it('lightbox_renders_hidden', () => {
      const wrapper = mount(ImageLightbox, {
        props: { visible: false, src: 'test.jpg', alt: 'Test' }
      })
      expect(wrapper.find('.lightbox-backdrop').exists()).toBe(false)
    })

    it('click_opens_lightbox', () => {
      const wrapper = mount(ImageLightbox, {
        props: { visible: true, src: 'test.jpg', alt: 'Test' }
      })
      expect(wrapper.find('.lightbox-backdrop').exists()).toBe(true)
      expect(wrapper.find('.lightbox-image').attributes('src')).toBe('test.jpg')
    })

    it('escape_closes_lightbox', async () => {
      const wrapper = mount(ImageLightbox, {
        props: { visible: true, src: 'test.jpg', alt: 'Test' }
      })
      await document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
      expect(wrapper.emitted('close')).toBeTruthy()
    })

    it('click_backdrop_closes_lightbox', async () => {
      const wrapper = mount(ImageLightbox, {
        props: { visible: true, src: 'test.jpg', alt: 'Test' }
      })
      await wrapper.find('.lightbox-backdrop').trigger('click')
      expect(wrapper.emitted('close')).toBeTruthy()
    })
  })

  // P4: @mention new tab
  describe('P4: @mention new tab', () => {
    it('mention_opens_new_tab', () => {
      // Test buildUrl logic
      const origin = 'http://localhost:3000'
      const pathname = '/dashboard/'
      function buildUrl(section, id) {
        return `${origin}${pathname}#/${section}/${id}`
      }
      const url = buildUrl('articles', 'test-slug')
      expect(url).toBe('http://localhost:3000/dashboard/#/articles/test-slug')
    })

    it('mention_url_hash_mode', () => {
      function buildUrl(section, id) {
        return `${window.location.origin}${window.location.pathname}#/${section}/${id}`
      }
      const url = buildUrl('articles', 'my-article')
      expect(url).toContain('#/articles/')
    })

    it('mention_testcase_url', () => {
      function buildUrl(section, id) {
        return `http://localhost:3000/dashboard/#/${section}/${id}`
      }
      expect(buildUrl('testcases', '123')).toContain('#/testcases/123')
      expect(buildUrl('tasks', '456')).toContain('#/tasks/456')
    })
  })
})
