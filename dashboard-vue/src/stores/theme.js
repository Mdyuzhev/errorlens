import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  const theme = ref('dark')

  function init() {
    const saved = localStorage.getItem('el-theme')
    if (saved === 'light' || saved === 'dark' || saved === 'retrowave' || saved === 'corp') {
      theme.value = saved
    }
    applyTheme()
  }

  function setTheme(t) {
    theme.value = t
    localStorage.setItem('el-theme', t)
    applyTheme()
  }

  function toggle() {
    const cycle = { dark: 'light', light: 'retrowave', retrowave: 'corp', corp: 'dark' }
    setTheme(cycle[theme.value])
  }

  function applyTheme() {
    document.body.classList.remove('theme-light', 'theme-retrowave', 'theme-corp')
    if (theme.value === 'light') {
      document.body.classList.add('theme-light')
    } else if (theme.value === 'retrowave') {
      document.body.classList.add('theme-retrowave')
    } else if (theme.value === 'corp') {
      document.body.classList.add('theme-corp')
    }
  }

  return { theme, init, setTheme, toggle }
})
