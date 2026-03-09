import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  const theme = ref('dark')

  function init() {
    const saved = localStorage.getItem('el-theme')
    if (saved === 'light' || saved === 'dark') {
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
    setTheme(theme.value === 'dark' ? 'light' : 'dark')
  }

  function applyTheme() {
    if (theme.value === 'light') {
      document.body.classList.add('theme-light')
    } else {
      document.body.classList.remove('theme-light')
    }
  }

  return { theme, init, setTheme, toggle }
})
