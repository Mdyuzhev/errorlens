/**
 * Tests for EL016: Light Theme + SVG Icon System.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { useThemeStore } from '@/stores/theme'
import AppIcon from '@/components/common/AppIcon.vue'

beforeEach(() => {
  setActivePinia(createPinia())
  document.body.classList.remove('theme-light')
  localStorage.clear()
})

afterEach(() => {
  document.body.classList.remove('theme-light')
  localStorage.clear()
})

describe('Theme Store', () => {
  describe('theme_init_dark', () => {
    it('body does not have theme-light class by default', () => {
      const store = useThemeStore()
      store.init()
      expect(document.body.classList.contains('theme-light')).toBe(false)
      expect(store.theme).toBe('dark')
    })
  })

  describe('theme_toggle_light', () => {
    it('after toggle() body gets theme-light class', () => {
      const store = useThemeStore()
      store.init()
      store.toggle()
      expect(document.body.classList.contains('theme-light')).toBe(true)
      expect(store.theme).toBe('light')
    })

    it('toggle back to dark removes theme-light class', () => {
      const store = useThemeStore()
      store.init()
      store.toggle()
      store.toggle()
      expect(document.body.classList.contains('theme-light')).toBe(false)
      expect(store.theme).toBe('dark')
    })
  })

  describe('theme_persists', () => {
    it('theme saved to localStorage persists after re-init', () => {
      const store = useThemeStore()
      store.init()
      store.setTheme('light')
      expect(localStorage.getItem('el-theme')).toBe('light')

      // Create a new store instance (simulates reload)
      setActivePinia(createPinia())
      const store2 = useThemeStore()
      store2.init()
      expect(store2.theme).toBe('light')
      expect(document.body.classList.contains('theme-light')).toBe(true)
    })

    it('ignores invalid localStorage values', () => {
      localStorage.setItem('el-theme', 'invalid-value')
      const store = useThemeStore()
      store.init()
      expect(store.theme).toBe('dark')
    })
  })
})

describe('AppIcon Component', () => {
  describe('icon_renders', () => {
    it('AppIcon with name="file" renders svg element', () => {
      const wrapper = mount(AppIcon, { props: { name: 'file' } })
      expect(wrapper.find('svg').exists()).toBe(true)
      expect(wrapper.find('path').exists()).toBe(true)
    })
  })

  describe('icon_size', () => {
    it('prop size=32 sets svg width/height to 32', () => {
      const wrapper = mount(AppIcon, { props: { name: 'file', size: 32 } })
      const svg = wrapper.find('svg')
      expect(svg.attributes('width')).toBe('32')
      expect(svg.attributes('height')).toBe('32')
    })

    it('default size is 20', () => {
      const wrapper = mount(AppIcon, { props: { name: 'file' } })
      const svg = wrapper.find('svg')
      expect(svg.attributes('width')).toBe('20')
      expect(svg.attributes('height')).toBe('20')
    })
  })

  describe('icon_no_glow_light', () => {
    it('glow=true adds app-icon--glow class', () => {
      const wrapper = mount(AppIcon, { props: { name: 'file', glow: true } })
      expect(wrapper.find('svg').classes()).toContain('app-icon--glow')
    })

    it('glow=false does not add app-icon--glow class', () => {
      const wrapper = mount(AppIcon, { props: { name: 'file', glow: false } })
      expect(wrapper.find('svg').classes()).not.toContain('app-icon--glow')
    })
  })

  describe('unknown_icon', () => {
    it('AppIcon with unknown name renders fallback without errors', () => {
      const wrapper = mount(AppIcon, { props: { name: 'nonexistent-icon' } })
      expect(wrapper.find('svg').exists()).toBe(true)
      // Fallback renders a circle (question mark icon)
      expect(wrapper.find('circle').exists()).toBe(true)
    })
  })

  describe('all icons render', () => {
    const iconNames = [
      'file', 'folder', 'folder-open', 'flask', 'check-square',
      'clipboard-list', 'play-circle', 'pencil', 'trash', 'plus',
      'x', 'chevron-right', 'chevron-down', 'search', 'settings',
      'user', 'link', 'eye', 'article', 'tag', 'calendar',
      'alert', 'check', 'ban', 'skip'
    ]

    iconNames.forEach(name => {
      it(`renders "${name}" icon without errors`, () => {
        const wrapper = mount(AppIcon, { props: { name } })
        expect(wrapper.find('svg').exists()).toBe(true)
      })
    })
  })
})
