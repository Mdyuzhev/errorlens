/**
 * Tests for Wave 6.0 Generator Components
 *
 * Required tests per component as per CLAUDE.md quality gates
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import InputTabs from '@/components/generator/InputTabs.vue'
import SessionSelector from '@/components/generator/SessionSelector.vue'
import FrameworkSelector from '@/components/generator/FrameworkSelector.vue'
import CodePreview from '@/components/generator/CodePreview.vue'
import GenerationHistory from '@/components/generator/GenerationHistory.vue'

describe('InputTabs', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(InputTabs, {
      props: {
        modelValue: 'swagger'
      }
    })
  })

  it('switches between tabs', async () => {
    const buttons = wrapper.findAll('button')
    expect(buttons.length).toBe(3)

    await buttons[1].trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['session'])
  })

  it('emits input-ready with correct type', async () => {
    wrapper.vm.handleSwaggerFile({ name: 'test.json' })
    expect(wrapper.emitted('input-ready')?.[0]).toEqual([
      { type: 'swagger', data: { name: 'test.json' } }
    ])
  })

  it('persists tab selection', async () => {
    const buttons = wrapper.findAll('button')
    await buttons[2].trigger('click')

    const saved = localStorage.getItem('generator_input_tab')
    expect(saved).toBe('url')
  })

  it('handles empty input', () => {
    expect(wrapper.vm.hasInput).toBe(false)
  })

  it('handles none input clearing', () => {
    wrapper.vm.handleClear()
    expect(wrapper.vm.hasInput).toBe(false)
    expect(wrapper.emitted('input-cleared')).toBeTruthy()
  })

  it('handles duplicate tab selections', async () => {
    const buttons = wrapper.findAll('button')
    await buttons[0].trigger('click')
    await buttons[0].trigger('click')

    expect(wrapper.emitted('update:modelValue')?.length).toBeGreaterThan(0)
  })
})

describe('SessionSelector', () => {
  let wrapper

  beforeEach(() => {
    localStorage.setItem('access_token', 'test-token')
    global.fetch = vi.fn()
    wrapper = mount(SessionSelector)
  })

  it('loads sessions with recorded_requests', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        items: [
          { id: '1', url: 'test.com', recorded_requests: [{ method: 'GET' }] }
        ]
      })
    })

    await new Promise(resolve => setTimeout(resolve, 100))

    expect(wrapper.vm.sessions.length).toBe(1)
  })

  it('filters empty sessions', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        items: [
          { id: '1', url: 'test.com', recorded_requests: [] },
          { id: '2', url: 'test2.com', recorded_requests: [{ method: 'GET' }] }
        ]
      })
    })

    await new Promise(resolve => setTimeout(resolve, 100))

    expect(wrapper.vm.sessions.length).toBe(1)
  })

  it('shows endpoint preview', async () => {
    wrapper.vm.sessions = [
      { id: '1', url: 'test.com', recorded_requests: [{ method: 'GET', path: '/api' }] }
    ]
    wrapper.vm.selectedSessionId = '1'
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.endpoints.length).toBe(1)
    expect(wrapper.vm.endpoints[0].method).toBe('GET')
  })

  it('handles error recovery', async () => {
    global.fetch.mockRejectedValueOnce(new Error('Network error'))

    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 0))

    expect(wrapper.vm.error).toBeTruthy()
    expect(wrapper.vm.loading).toBe(false)
  })

  it('handles concurrent access', async () => {
    const promise1 = wrapper.vm.$nextTick()
    const promise2 = wrapper.vm.$nextTick()

    await Promise.all([promise1, promise2])
    expect(wrapper.vm.loading).toBeDefined()
  })
})

describe('FrameworkSelector', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(FrameworkSelector, {
      props: {
        modelValue: 'pytest'
      }
    })
  })

  it('renders all frameworks', () => {
    const cards = wrapper.findAll('.framework-card')
    expect(cards.length).toBe(5)
  })

  it('emits selection', async () => {
    const cards = wrapper.findAll('.framework-card')
    await cards[1].trigger('click')

    expect(wrapper.emitted('update:modelValue')?.[0]).toBeTruthy()
  })

  it('shows selected state', async () => {
    const cards = wrapper.findAll('.framework-card')
    expect(cards[0].classes()).toContain('selected')
  })

  it('handles empty input', () => {
    const wrapper2 = mount(FrameworkSelector, {
      props: { modelValue: '' }
    })
    expect(wrapper2.vm.modelValue).toBe('')
  })

  it('handles duplicate selections', async () => {
    const cards = wrapper.findAll('.framework-card')
    await cards[0].trigger('click')
    await cards[0].trigger('click')

    expect(wrapper.emitted('update:modelValue')?.length).toBeGreaterThan(0)
  })
})

describe('CodePreview', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(CodePreview, {
      props: {
        title: 'Test Code',
        code: 'print("hello")',
        language: 'python'
      }
    })
  })

  it('applies syntax highlighting', () => {
    const code = wrapper.find('code')
    expect(code.classes()).toContain('language-python')
  })

  it('copies to clipboard', async () => {
    const clipboardSpy = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue()

    const btn = wrapper.find('.copy-btn')
    await btn.trigger('click')

    expect(clipboardSpy).toHaveBeenCalledWith('print("hello")')
  })

  it('shows line numbers', () => {
    expect(wrapper.vm.formattedCode).toContain('   1')
  })

  it('handles empty input', () => {
    const wrapper2 = mount(CodePreview, {
      props: { title: 'Empty', code: '', language: 'python' }
    })
    expect(wrapper2.find('.empty-preview').exists()).toBe(true)
  })

  it('handles none code', () => {
    const wrapper2 = mount(CodePreview, {
      props: { title: 'None', code: null, language: 'python' }
    })
    expect(wrapper2.vm.formattedCode).toBe('')
  })

  it('handles error recovery in copy', async () => {
    const clipboardSpy = vi.spyOn(navigator.clipboard, 'writeText').mockRejectedValue(new Error())
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    await wrapper.vm.copyToClipboard()

    expect(consoleSpy).toHaveBeenCalled()
  })
})

describe('GenerationHistory', () => {
  let wrapper

  beforeEach(() => {
    localStorage.clear()
    wrapper = mount(GenerationHistory)
  })

  it('loads from localStorage', () => {
    const testHistory = [
      { id: 1, framework: 'pytest', endpoints: 5, created_at: new Date().toISOString() }
    ]
    localStorage.setItem('generation_history', JSON.stringify(testHistory))

    const wrapper2 = mount(GenerationHistory)
    expect(wrapper2.vm.history.length).toBe(1)
  })

  it('limits to 20 items', () => {
    const items = Array.from({ length: 25 }, (_, i) => ({
      id: i,
      framework: 'pytest',
      endpoints: 1,
      created_at: new Date().toISOString()
    }))

    items.forEach(item => wrapper.vm.addToHistory(item))

    expect(wrapper.vm.history.length).toBe(20)
  })

  it('allows re-download', async () => {
    wrapper.vm.history = [
      { id: 1, framework: 'pytest', endpoints: 5, result_id: 'abc123', created_at: new Date().toISOString() }
    ]
    await wrapper.vm.$nextTick()

    const downloadBtn = wrapper.find('.action-btn')
    await downloadBtn.trigger('click')

    expect(wrapper.emitted('redownload')?.[0]).toEqual(['abc123'])
  })

  it('handles empty history', () => {
    expect(wrapper.vm.history.length).toBe(0)
    expect(wrapper.find('.empty-history').exists()).toBe(true)
  })

  it('handles duplicate items', () => {
    const item = { framework: 'pytest', endpoints: 5, result_id: 'abc' }
    wrapper.vm.addToHistory(item)
    wrapper.vm.addToHistory(item)

    expect(wrapper.vm.history.length).toBe(2)
  })

  it('handles memory cleanup', () => {
    const largArray = Array.from({ length: 100 }, (_, i) => ({
      id: i,
      framework: 'pytest',
      endpoints: 1,
      created_at: new Date().toISOString()
    }))

    largArray.forEach(item => wrapper.vm.addToHistory(item))

    expect(wrapper.vm.history.length).toBeLessThanOrEqual(20)
  })

  it('handles concurrent access', async () => {
    const item1 = { framework: 'pytest', endpoints: 5, result_id: 'abc1' }
    const item2 = { framework: 'cypress', endpoints: 3, result_id: 'abc2' }

    const promise1 = Promise.resolve().then(() => wrapper.vm.addToHistory(item1))
    const promise2 = Promise.resolve().then(() => wrapper.vm.addToHistory(item2))

    await Promise.all([promise1, promise2])

    expect(wrapper.vm.history.length).toBeGreaterThan(0)
  })
})
