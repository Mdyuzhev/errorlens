import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import EntityMentionChip from '../EntityMentionChip.vue'

// Mock NodeViewWrapper from tiptap
vi.mock('@tiptap/vue-3', () => ({
  NodeViewWrapper: {
    name: 'NodeViewWrapper',
    template: '<span><slot /></span>',
    props: ['as']
  }
}))

// Mock api module
const mockGetPreview = vi.fn()
vi.mock('@/services/api', () => ({
  entityLinksApi: {
    getPreview: (...args) => mockGetPreview(...args)
  }
}))

function mountChip(attrs = {}) {
  const defaultAttrs = {
    entityType: 'testcase',
    entityId: 'tc-123',
    entityTitle: 'Login Test',
    linkType: 'related'
  }
  return mount(EntityMentionChip, {
    props: {
      node: { attrs: { ...defaultAttrs, ...attrs } },
      updateAttributes: vi.fn()
    },
    global: {
      stubs: {}
    }
  })
}

describe('EntityMentionChip', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('test_renders_loading', () => {
    // API never resolves — stays in loading
    mockGetPreview.mockReturnValue(new Promise(() => {}))
    const wrapper = mountChip()
    expect(wrapper.find('.chip-loading').exists()).toBe(true)
    expect(wrapper.find('.chip-spinner').exists()).toBe(true)
  })

  it('test_renders_chip_with_data', async () => {
    mockGetPreview.mockResolvedValue({
      data: { id: 'tc-123', type: 'testcase', title: 'Login Test Case', status: 'Ready' }
    })

    const wrapper = mountChip()
    await flushPromises()
    await nextTick()

    expect(wrapper.find('.chip-content').exists()).toBe(true)
    expect(wrapper.find('.chip-title').text()).toBe('Login Test Case')
    expect(wrapper.find('.chip-status').text()).toBe('Ready')
    expect(wrapper.find('.chip-loading').exists()).toBe(false)
  })

  it('test_renders_deleted_state', async () => {
    mockGetPreview.mockRejectedValue({ response: { status: 404 } })

    const wrapper = mountChip()
    await flushPromises()
    await nextTick()

    expect(wrapper.find('.chip-deleted').exists()).toBe(true)
    expect(wrapper.find('s').exists()).toBe(true)
  })

  it('test_click_opens_popup', async () => {
    mockGetPreview.mockResolvedValue({
      data: { id: 'tc-123', type: 'testcase', title: 'Login Test', status: 'Draft' }
    })

    const wrapper = mountChip()
    await flushPromises()
    await nextTick()

    // Popup should not be visible initially
    expect(wrapper.find('.chip-preview-popup').exists()).toBe(false)

    // Click the chip
    await wrapper.find('.entity-mention-chip').trigger('click')
    await nextTick()

    // Popup should now be visible
    expect(wrapper.find('.chip-preview-popup').exists()).toBe(true)
    expect(wrapper.find('.preview-header strong').text()).toBe('Login Test')
  })
})
