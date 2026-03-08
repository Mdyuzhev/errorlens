import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import CollapsibleSection from '../CollapsibleSection.vue'

function mountSection(props = {}) {
  return mount(CollapsibleSection, {
    props: { title: 'Test Section', ...props },
    slots: { default: '<p>Section content</p>' }
  })
}

describe('CollapsibleSection', () => {
  it('test_closed_by_default', () => {
    const wrapper = mountSection({ defaultOpen: false })
    const body = wrapper.find('.collapsible-body')
    expect(body.element.style.maxHeight).toBe('0px')
  })

  it('test_opens_on_click', async () => {
    const wrapper = mountSection({ defaultOpen: false })
    await wrapper.find('.collapsible-header').trigger('click')
    await nextTick()
    const body = wrapper.find('.collapsible-body')
    expect(body.element.style.maxHeight).not.toBe('0px')
    expect(wrapper.find('.collapsible-arrow').text()).toBe('▼')
  })

  it('test_auto_open_with_content', () => {
    const wrapper = mountSection({ hasContent: true, defaultOpen: false })
    const body = wrapper.find('.collapsible-body')
    expect(body.element.style.maxHeight).not.toBe('0px')
  })
})
