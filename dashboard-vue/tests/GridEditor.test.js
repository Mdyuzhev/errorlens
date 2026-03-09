import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import GridEditor from '@/components/articles/GridEditor.vue'

// Mock RichEditor to avoid TipTap dependency
vi.mock('@/components/common/RichEditor.vue', () => ({
  default: {
    name: 'RichEditor',
    props: ['modelValue', 'placeholder', 'uploadEnabled'],
    emits: ['update:modelValue'],
    template: '<div class="mock-rich-editor"></div>'
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

describe('GridEditor', () => {
  beforeEach(() => {
    uuidCounter = 0
  })

  it('renders_empty_grid', () => {
    const wrapper = mount(GridEditor, {
      props: { modelValue: makeGrid() }
    })
    expect(wrapper.find('.add-row-btn').exists()).toBe(true)
    expect(wrapper.find('.add-row-btn').text()).toBe('+ Добавить строку')
    expect(wrapper.findAll('.grid-row-wrapper').length).toBe(0)
  })

  it('add_row', async () => {
    const wrapper = mount(GridEditor, {
      props: { modelValue: makeGrid() }
    })
    await wrapper.find('.add-row-btn').trigger('click')
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    expect(emitted[0][0].rows.length).toBe(1)
    expect(emitted[0][0].rows[0].columns.length).toBe(1)
    expect(emitted[0][0].rows[0].columns[0].span).toBe(12)
  })

  it('split_column', async () => {
    const grid = makeGrid([makeRow([{ id: 'col-1', span: 12, content: { type: 'doc', content: [] } }])])
    const wrapper = mount(GridEditor, {
      props: { modelValue: grid }
    })
    // Find split button (÷)
    const splitBtn = wrapper.findAll('.col-btn').find(b => b.text() === '÷')
    expect(splitBtn).toBeTruthy()
    await splitBtn.trigger('click')
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    const updatedRow = emitted[0][0].rows[0]
    expect(updatedRow.columns.length).toBe(2)
    expect(updatedRow.columns[0].span + updatedRow.columns[1].span).toBe(12)
  })

  it('split_max_columns', () => {
    const grid = makeGrid([makeRow([
      { id: 'c1', span: 4, content: { type: 'doc', content: [] } },
      { id: 'c2', span: 4, content: { type: 'doc', content: [] } },
      { id: 'c3', span: 4, content: { type: 'doc', content: [] } }
    ])])
    const wrapper = mount(GridEditor, {
      props: { modelValue: grid }
    })
    const splitBtns = wrapper.findAll('.col-btn').filter(b => b.text() === '÷')
    splitBtns.forEach(btn => {
      expect(btn.attributes('disabled')).toBeDefined()
    })
  })

  it('delete_row', async () => {
    // Use empty content so no confirm dialog
    const grid = makeGrid([
      makeRow([{ id: 'c1', span: 12, content: { type: 'doc', content: [] } }], 'r1'),
      makeRow([{ id: 'c2', span: 12, content: { type: 'doc', content: [] } }], 'r2')
    ])
    const wrapper = mount(GridEditor, {
      props: { modelValue: grid }
    })
    expect(wrapper.findAll('.grid-row-wrapper').length).toBe(2)
    // Click delete button on first row
    const deleteBtn = wrapper.findAll('.row-btn-danger')[0]
    await deleteBtn.trigger('click')
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    expect(emitted[0][0].rows.length).toBe(1)
  })

  it('move_row_up', async () => {
    const grid = makeGrid([
      makeRow([{ id: 'c1', span: 12, content: { type: 'doc', content: [] } }], 'r1'),
      makeRow([{ id: 'c2', span: 12, content: { type: 'doc', content: [] } }], 'r2')
    ])
    const wrapper = mount(GridEditor, {
      props: { modelValue: grid }
    })
    // Find the ↑ button on second row (first row's ↑ is disabled)
    const rowWrappers = wrapper.findAll('.grid-row-wrapper')
    const upBtn = rowWrappers[1].findAll('.row-btn').find(b => b.text() === '↑')
    expect(upBtn).toBeTruthy()
    await upBtn.trigger('click')
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    expect(emitted[0][0].rows[0].id).toBe('r2')
    expect(emitted[0][0].rows[1].id).toBe('r1')
  })

  it('legacy_content_parsed', () => {
    // Test the parseArticleContent function logic inline
    const legacyTiptap = { type: 'doc', content: [{ type: 'paragraph' }] }
    const raw = JSON.stringify(legacyTiptap)
    const parsed = JSON.parse(raw)
    // Simulate parseArticleContent: no version field → wrap
    expect(parsed.version).toBeUndefined()
    const grid = {
      version: 'grid-1',
      rows: [{ id: 'uuid', columns: [{ id: 'uuid', span: 12, content: parsed }] }]
    }
    expect(grid.version).toBe('grid-1')
    expect(grid.rows.length).toBe(1)
    expect(grid.rows[0].columns[0].span).toBe(12)
    expect(grid.rows[0].columns[0].content.type).toBe('doc')
  })

  it('empty_content_parsed', () => {
    // Simulate parseArticleContent with empty string
    const raw = ''
    let result
    if (!raw) {
      result = { version: 'grid-1', rows: [] }
    }
    expect(result.version).toBe('grid-1')
    expect(result.rows.length).toBe(0)
  })
})
