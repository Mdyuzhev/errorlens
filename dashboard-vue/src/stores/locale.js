import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import ru from '@/locales/ru.js'
import en from '@/locales/en.js'
import zh from '@/locales/zh.js'

const LOCALES = { ru, en, zh }
const SUPPORTED = ['ru', 'en', 'zh']

export const useLocaleStore = defineStore('locale', () => {
  const locale = ref('ru')

  function init() {
    const saved = localStorage.getItem('el-locale')
    if (saved && SUPPORTED.includes(saved)) {
      locale.value = saved
    }
  }

  function setLocale(lang) {
    if (!SUPPORTED.includes(lang)) return
    locale.value = lang
    localStorage.setItem('el-locale', lang)
  }

  // Deep key access: t('nav.qa') → translations.nav.qa
  function t(key) {
    const messages = LOCALES[locale.value] || LOCALES.ru
    const parts = key.split('.')
    let result = messages
    for (const part of parts) {
      result = result?.[part]
      if (result === undefined) break
    }
    if (typeof result === 'string') return result
    // Fallback to Russian
    let fallback = LOCALES.ru
    for (const part of parts) {
      fallback = fallback?.[part]
    }
    return typeof fallback === 'string' ? fallback : key
  }

  const currentLocaleLabel = computed(() => {
    return { ru: 'RU', en: 'EN', zh: '中' }[locale.value] || 'RU'
  })

  return { locale, init, setLocale, t, currentLocaleLabel }
})
