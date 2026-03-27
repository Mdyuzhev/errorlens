import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  const theme = ref('dark')

  function init() {
    const saved = localStorage.getItem('el-theme')
    if (saved === 'light' || saved === 'dark' || saved === 'retrowave') {
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
    const cycle = { dark: 'light', light: 'retrowave', retrowave: 'dark' }
    setTheme(cycle[theme.value])
  }

  function applyTheme() {
    document.body.classList.remove('theme-light', 'theme-retrowave')
    if (theme.value === 'light') {
      document.body.classList.add('theme-light')
    } else if (theme.value === 'retrowave') {
      document.body.classList.add('theme-retrowave')
    }
  }

  return { theme, init, setTheme, toggle }
})
