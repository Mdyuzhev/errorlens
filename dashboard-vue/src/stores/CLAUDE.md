# stores/ — правила работы с Pinia stores

## Соглашение об именовании и структуре

Каждый store определяется через `defineStore` с уникальным строковым ID.
Экспортируется как `use*Store` (useQAStore, useArticlesStore, useTasksStore и т.д.).

```javascript
// Шаблон store
export const useMyStore = defineStore('my-domain', {
  state: () => ({
    items: [],
    currentItem: null,
    loading: false,
    error: null,
  }),
  actions: {
    async fetchItems(params) {
      this.loading = true
      try {
        const res = await myApi.list(params)
        this.items = res.data
      } catch (e) {
        this.error = e.response?.data?.detail || 'Failed'
      } finally {
        this.loading = false
      }
    },
  }
})
```

## Текущие stores и их зоны ответственности

| Store | Файл | Зона |
|-------|------|------|
| `useQAStore` | `qa.js` | Тест-кейсы, папки, планы, прогоны, дашборд |
| `useArticlesStore` | `articles.js` | Статьи, папки, версии, breadcrumbs |
| `useIssuesStore` | `issues.js` | Issues (задачи), спринты, компоненты, дашборд |
| `useAuthStore` | `auth.js` | JWT токены, текущий пользователь |
| `useNotificationsStore` | `notifications.js` | Bell-уведомления, polling |
| `useThemeStore` | `theme.js` | dark/light тема, localStorage |
| `useLocaleStore` | `locale.js` | i18n, locale, t(key) |
| `useTasksStore` | `tasks.js` | Устаревший — используется в TasksView (legacy) |
| `useTestCasesStore` | `testcases.js` | Устаревший — используется в TestCasesView (legacy) |
| `useAdminStore` | `admin.js` | Админ-панель, пользователи |
| `useGenerationStore` | `generation.js` | Генерация тестов из Swagger/сессий |
| `useGitLabStore` | `gitlab.js` | GitLab интеграция |
| `useJqlStore` | `jql.js` | JQL-поиск задач |
| `useRecorderStore` | `recorder.js` | Запись сессий (расширение) |
| `useSessionsStore` | `sessions.js` | Сессии тестирования |
| `useTestPlansStore` | `testPlans.js` | Тест-планы (legacy, новый код → qa.js) |

`tasks.js` и `testcases.js` — legacy stores. Новый функционал добавлять в `qa.js` и `issues.js`.

## Actions — соглашения

- Actions возвращают `true`/`false` для success/failure или данные
- Ошибка пишется в `this.error`, не бросается наружу (кроме критических)
- После мутации данных — рефетч через `fetchItems()` для синхронизации

## Компоненты не вызывают api.js напрямую

Компонент → store action → api.js. Прямые вызовы `api.js` из компонентов — запрещены.

## Запрещено

- Хранить sensitive данные (токены) в state store — только в localStorage/sessionStorage
- Прямые вызовы router из store (только при необходимости через inject)
- Добавлять новый функционал в legacy stores (`tasks.js`, `testcases.js`)
- Дублировать state между stores — один источник правды
