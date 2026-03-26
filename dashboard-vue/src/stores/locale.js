import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const messages = {
  en: {
    qa: {
      title: 'QA',
      newCase: '+ New Test Case',
      tabs: {
        tree: 'Tree',
        plans: 'Test Plans',
        runs: 'Runs',
        dashboard: 'Dashboard',
        sessions: 'Sessions',
        results: 'Results',
      },
    },
  },
  ru: {
    qa: {
      title: 'QA',
      newCase: '+ Новый тест-кейс',
      tabs: {
        tree: 'Дерево',
        plans: 'Тест-планы',
        runs: 'Прогоны',
        dashboard: 'Дашборд',
        sessions: 'Сессии',
        results: 'Результаты',
      },
    },
  },
}

function resolve(obj, path) {
  return path.split('.').reduce((acc, key) => acc?.[key], obj)
}

export const useLocaleStore = defineStore('locale', () => {
  const lang = ref('en')

  function t(key) {
    return resolve(messages[lang.value], key) ?? key
  }

  function setLang(l) {
    lang.value = l
  }

  return { lang, t, setLang }
})
