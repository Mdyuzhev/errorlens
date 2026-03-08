import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import StepsTable from '../StepsTable.vue'

// Mock RichEditor — render as a simple div
vi.mock('@/components/common/RichEditor.vue', () => ({
  default: {
    name: 'RichEditor',
    template: '<div class="mock-editor">{{ modelValue?.content?.[0]?.content?.[0]?.text || "" }}</div>',
    props: ['modelValue', 'placeholder', 'editable', 'uploadEnabled', 'maxLength']
  }
}))

// Mock api for RichEditor
vi.mock('@/services/api', () => ({
  articlesApi: { uploadImage: vi.fn() }
}))

const sampleSteps = [
  { action: 'Open page', expected: 'Page loaded', testData: '' },
  { action: 'Click button', expected: 'Dialog shown', testData: '' }
]

function mountTable(props = {}) {
  return mount(StepsTable, {
    props: { steps: sampleSteps, ...props }
  })
}

describe('StepsTable', () => {
  it('test_renders_steps', () => {
    const wrapper = mountTable()
    const rows = wrapper.findAll('.step-row')
    expect(rows.length).toBe(2)
    expect(wrapper.findAll('.step-num').length).toBe(2)
    expect(wrapper.find('.step-num').text()).toBe('1')
  })

  it('test_add_step', async () => {
    const wrapper = mountTable()
    const addBtn = wrapper.find('[data-testid="add-step"]')
    await addBtn.trigger('click')
    await nextTick()

    const rows = wrapper.findAll('.step-row')
    expect(rows.length).toBe(3)

    const emitted = wrapper.emitted('update:steps')
    expect(emitted).toBeTruthy()
    expect(emitted[emitted.length - 1][0].length).toBe(3)
  })

  it('test_remove_step', async () => {
    const wrapper = mountTable()
    const removeBtn = wrapper.findAll('.btn-remove')[0]
    await removeBtn.trigger('click')
    await nextTick()

    const rows = wrapper.findAll('.step-row')
    expect(rows.length).toBe(1)

    const emitted = wrapper.emitted('update:steps')
    expect(emitted).toBeTruthy()
    expect(emitted[emitted.length - 1][0].length).toBe(1)
  })

  it('test_empty_steps', () => {
    const wrapper = mountTable({ steps: [] })
    // Should have at least one default row
    expect(wrapper.findAll('.step-row').length).toBe(1)
    expect(wrapper.find('[data-testid="add-step"]').exists()).toBe(true)
  })

  it('test_plain_text_fallback', () => {
    // Passing plain string in action — should not crash
    const wrapper = mountTable({
      steps: [{ action: 'Plain text action', expected: 'Result', testData: '' }]
    })
    expect(wrapper.findAll('.step-row').length).toBe(1)
    // The mock RichEditor renders — no crash
    expect(wrapper.find('.mock-editor').exists()).toBe(true)
  })
})
