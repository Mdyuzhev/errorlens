import { reactive } from 'vue'
import { testCasesApi, tasksApi, articlesApi } from '@/services/api'

// Shared reactive state for the popup — lives at module level
// so RichEditor can watch it and render EntityMentionPopup
export const suggestionState = reactive({
  active: false,
  items: [],
  selectedIndex: 0,
  query: '',
  clientRect: null,
  command: null,
})

let debounceTimer = null

async function fetchItems(query) {
  if (!query || query.length < 1) return []

  try {
    const [tcRes, taskRes, articleRes] = await Promise.all([
      testCasesApi.list({ q: query, limit: 10 }).catch(() => ({ data: [] })),
      tasksApi.list({ q: query, limit: 10 }).catch(() => ({ data: [] })),
      articlesApi.list({ q: query, limit: 10 }).catch(() => ({ data: [] })),
    ])

    const tcItems = (tcRes.data.items || tcRes.data || []).map((tc) => ({
      entityType: 'testcase',
      entityId: tc.id,
      entityTitle: tc.title,
      status: tc.status,
      linkType: 'verifies',
      icon: '\u{1F9EA}',
      typeLabel: 'Test Case',
      updated_at: tc.updated_at,
    }))

    const taskItems = (taskRes.data.items || taskRes.data || []).map((t) => ({
      entityType: 'task',
      entityId: t.id,
      entityTitle: t.title,
      status: t.status,
      linkType: 'related',
      icon: '\u2705',
      typeLabel: 'Task',
      updated_at: t.updated_at,
    }))

    const articleItems = (articleRes.data.items || articleRes.data || []).map((a) => ({
      entityType: 'article',
      entityId: a.id,
      entityTitle: a.title,
      status: a.status,
      linkType: 'related',
      icon: '\u{1F4C4}',
      typeLabel: 'Article',
      updated_at: a.updated_at,
    }))

    return [...tcItems, ...taskItems, ...articleItems]
  } catch {
    return []
  }
}

export default {
  items: ({ query }) => {
    return new Promise((resolve) => {
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(async () => {
        const items = await fetchItems(query)
        resolve(items)
      }, 300)
    })
  },

  render: () => {
    return {
      onStart: (props) => {
        suggestionState.active = true
        suggestionState.items = props.items
        suggestionState.selectedIndex = 0
        suggestionState.query = props.query
        suggestionState.command = props.command
        suggestionState.clientRect = props.clientRect
      },

      onUpdate: (props) => {
        suggestionState.items = props.items
        suggestionState.query = props.query
        suggestionState.command = props.command
        suggestionState.clientRect = props.clientRect
      },

      onKeyDown: ({ event }) => {
        if (event.key === 'ArrowUp') {
          suggestionState.selectedIndex =
            (suggestionState.selectedIndex - 1 + suggestionState.items.length) %
            suggestionState.items.length
          return true
        }
        if (event.key === 'ArrowDown') {
          suggestionState.selectedIndex =
            (suggestionState.selectedIndex + 1) % suggestionState.items.length
          return true
        }
        if (event.key === 'Enter') {
          const item = suggestionState.items[suggestionState.selectedIndex]
          if (item && suggestionState.command) {
            suggestionState.command(item)
          }
          return true
        }
        if (event.key === 'Escape') {
          suggestionState.active = false
          return true
        }
        return false
      },

      onExit: () => {
        suggestionState.active = false
        suggestionState.items = []
        suggestionState.selectedIndex = 0
        suggestionState.command = null
        suggestionState.clientRect = null
      },
    }
  },
}
