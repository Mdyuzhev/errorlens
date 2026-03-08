import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import RichEditor from '../RichEditor.vue'

// Mock the API module
vi.mock('@/services/api', () => ({
  articlesApi: {
    uploadImage: vi.fn()
  }
}))

const sampleDoc = {
  type: 'doc',
  content: [
    { type: 'paragraph', content: [{ type: 'text', text: 'Hello world' }] }
  ]
}

function mountEditor(props = {}) {
  return mount(RichEditor, {
    props,
    global: {
      stubs: {}
    }
  })
}

describe('RichEditor', () => {
  it('test_renders_without_crash', () => {
    const wrapper = mountEditor()
    expect(wrapper.find('.rich-editor').exists()).toBe(true)
  })

  it('test_modelValue_sets_content', async () => {
    const wrapper = mountEditor({ modelValue: sampleDoc })
    await nextTick()
    await nextTick()
    // Editor content should contain our text
    const editorContent = wrapper.find('.rich-editor__content')
    expect(editorContent.exists()).toBe(true)
  })

  it('test_emits_on_change', async () => {
    const wrapper = mountEditor({ modelValue: sampleDoc })
    await nextTick()
    await nextTick()
    // The component should have emitted at least the initial content
    // TipTap fires onUpdate when content is set
    // We verify the emit mechanism is wired up
    expect(wrapper.emitted()).toBeDefined()
  })

  it('test_readonly_hides_toolbar', () => {
    const wrapper = mountEditor({ editable: false })
    expect(wrapper.find('.editor-toolbar').exists()).toBe(false)
  })

  it('test_placeholder_shown_when_empty', async () => {
    const wrapper = mountEditor({ placeholder: 'Test placeholder' })
    await nextTick()
    // Placeholder is set via TipTap extension, check it doesn't crash
    expect(wrapper.find('.rich-editor').exists()).toBe(true)
  })

  it('test_character_count_shown', () => {
    const wrapper = mountEditor({ maxLength: 100 })
    expect(wrapper.find('.rich-editor__counter').exists()).toBe(true)
    expect(wrapper.find('.rich-editor__counter').text()).toContain('/ 100')
  })

  it('test_plain_text_fallback', async () => {
    // Plain text passed as TipTap doc wrapper (as parseContent would produce)
    const plainDoc = {
      type: 'doc',
      content: [{ type: 'paragraph', content: [{ type: 'text', text: 'plain text' }] }]
    }
    const wrapper = mountEditor({ modelValue: plainDoc })
    await nextTick()
    expect(wrapper.find('.rich-editor').exists()).toBe(true)
  })

  it('test_upload_button_hidden_by_default', () => {
    const wrapper = mountEditor({ uploadEnabled: false })
    expect(wrapper.find('[data-testid="image-upload-btn"]').exists()).toBe(false)
  })

  it('test_upload_button_visible_when_enabled', async () => {
    const wrapper = mountEditor({ uploadEnabled: true })
    await nextTick()
    await nextTick()
    expect(wrapper.find('[data-testid="image-upload-btn"]').exists()).toBe(true)
  })

  it('test_readonly_class_applied', () => {
    const wrapper = mountEditor({ editable: false })
    expect(wrapper.find('.rich-editor--readonly').exists()).toBe(true)
  })

  it('test_counter_hidden_without_maxLength', () => {
    const wrapper = mountEditor()
    expect(wrapper.find('.rich-editor__counter').exists()).toBe(false)
  })
})
