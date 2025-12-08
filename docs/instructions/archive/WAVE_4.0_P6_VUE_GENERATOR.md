# Wave 4.0 P6: Vue Generator UI

## Scope

Create files in `dashboard-vue/src/`:
- `composables/useGenerationSocket.js`
- `stores/generation.js`
- `components/generator/SwaggerUpload.vue`
- `components/generator/GenerationProgress.vue`
- `components/generator/CodePreview.vue`
- `views/GeneratorView.vue`

Update:
- `router/index.js`

## Interfaces

### composables/useGenerationSocket.js

```javascript
export function useGenerationSocket(taskId) {
  // Returns
  return {
    progress,      // ref<number>
    total,         // ref<number>
    currentEndpoint, // ref<string>
    logs,          // ref<string[]>
    status,        // ref<'idle'|'connecting'|'running'|'completed'|'error'>
    resultId,      // ref<string|null>
    error,         // ref<string|null>
    connect,       // () => void
    disconnect,    // () => void
  }
}
```

### stores/generation.js

```javascript
export const useGenerationStore = defineStore('generation', () => {
  // State
  const loading = ref(false)
  const taskId = ref(null)
  const result = ref(null)
  const error = ref(null)

  // Actions
  async function startFromSwagger(file, options) { ... }
  async function fetchResult(resultId) { ... }
  function getDownloadUrl(resultId) { ... }
  function reset() { ... }

  return { loading, taskId, result, error, startFromSwagger, fetchResult, getDownloadUrl, reset }
})
```

### Components Props/Emits

```javascript
// SwaggerUpload.vue
emits: ['file-selected', 'file-removed']

// GenerationProgress.vue
props: {
  progress: Number,
  total: Number,
  currentEndpoint: String,
  logs: Array,
  status: String
}

// CodePreview.vue
props: {
  title: String,
  code: String
}
```

## Requirements

### WebSocket Reconnection
- Exponential backoff: 1s, 2s, 4s, 8s, max 30s
- Max 5 reconnection attempts
- Show reconnection status to user

### File Upload
- Drag-and-drop support
- Accept: .json, .yaml, .yml
- Show file name and size after selection
- Allow removal

### Progress Display
- Percentage bar with animation
- Current endpoint name
- Scrollable log area (max-height: 200px)
- Status text in Russian

### Error Handling
- Show error message prominently
- Allow retry
- Clear error on new attempt

### Styling
- Use existing ErrorLens gradient: `linear-gradient(135deg, #667eea, #764ba2)`
- Card class: `settings-card`
- Dark theme compatible

## Prohibited

- Inline styles over 3 properties (use scoped CSS)
- Direct API calls in components (use store)
- Hard-coded URLs
- console.log in production code

## Tests Required

```javascript
// tests/generator.spec.js (Vitest)

describe('SwaggerUpload', () => {
  it('emits file-selected on drop')
  it('shows file info after selection')
  it('emits file-removed on clear')
  it('rejects invalid file types')
})

describe('GenerationProgress', () => {
  it('calculates percentage correctly')
  it('shows correct status text')
  it('auto-scrolls logs')
})

describe('useGenerationSocket', () => {
  it('connects to correct URL')
  it('handles all event types')
  it('reconnects on disconnect')
  it('stops after max attempts')
})
```

## Router Update

```javascript
// router/index.js
{
  path: '/generator',
  name: 'generator',
  component: () => import('../views/GeneratorView.vue'),
  meta: { requiresAuth: true }
}
```

## Commit

```
[Wave 4.0] P6: Add Vue Generator UI with WebSocket progress
```
