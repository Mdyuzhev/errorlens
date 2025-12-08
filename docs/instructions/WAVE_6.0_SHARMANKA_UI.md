# Wave 6.0: Sharmanka UI Migration

## Scope

Full-featured test generator UI с дизайном ErrorLens.

## Current State

```
GeneratorView.vue: basic Swagger upload
Components: SwaggerUpload, GenerationProgress, LLMSettings
```

## Target State

```
GeneratorView.vue: Tabs (Swagger | Session | URL) + Code Preview + History
Components: +InputTabs, +CodePreview, +FrameworkSelector, +GenerationHistory
```

---

## P1: Input Tabs Component

### Create `components/generator/InputTabs.vue`

```vue
<template>
  <div class="input-tabs">
    <div class="tabs-header">
      <button :class="{ active: tab === 'swagger' }" @click="tab = 'swagger'">
        📄 Swagger/OpenAPI
      </button>
      <button :class="{ active: tab === 'session' }" @click="tab = 'session'">
        📹 Из сессии
      </button>
      <button :class="{ active: tab === 'url' }" @click="tab = 'url'">
        🔗 URL endpoint
      </button>
    </div>
    
    <div class="tab-content">
      <SwaggerUpload v-if="tab === 'swagger'" @file-selected="..." />
      <SessionSelector v-if="tab === 'session'" @session-selected="..." />
      <UrlInput v-if="tab === 'url'" @endpoints-added="..." />
    </div>
  </div>
</template>
```

### Interface

```javascript
// Props
defineProps({
  modelValue: String // 'swagger' | 'session' | 'url'
})

// Emits
defineEmits([
  'update:modelValue',
  'input-ready',  // { type, data }
  'input-cleared'
])
```

### Requirements

- Tab state persists in localStorage
- Visual indicator when input ready
- Clear button per tab

---

## P2: Session Selector Component

### Create `components/generator/SessionSelector.vue`

```vue
<template>
  <div class="session-selector">
    <select v-model="selectedSession">
      <option value="">Выберите сессию...</option>
      <option v-for="s in sessions" :value="s.id">
        {{ s.url }} ({{ s.recorded_requests.length }} requests)
      </option>
    </select>
    <div v-if="selectedSession" class="session-preview">
      <!-- Preview of endpoints -->
    </div>
  </div>
</template>
```

### Interface

```javascript
// Emits
defineEmits(['session-selected']) // session object

// Internal
const sessions = ref([]) // Load from API on mount
```

### Requirements

- Load sessions with recorded_requests > 0
- Show endpoint count per session
- Preview endpoints before generation

---

## P3: URL Input Component

### Create `components/generator/UrlInput.vue`

```vue
<template>
  <div class="url-input">
    <div class="endpoint-row" v-for="(ep, i) in endpoints">
      <select v-model="ep.method">
        <option>GET</option><option>POST</option>
        <option>PUT</option><option>DELETE</option>
      </select>
      <input v-model="ep.url" placeholder="https://api.example.com/users" />
      <button @click="removeEndpoint(i)">✕</button>
    </div>
    <button @click="addEndpoint">+ Добавить endpoint</button>
  </div>
</template>
```

### Interface

```javascript
// Emits
defineEmits(['endpoints-added']) // EndpointSpec[]
```

### Requirements

- Add/remove endpoints dynamically
- Validate URL format
- Parse path parameters from URL

---

## P4: Framework Selector Component

### Create `components/generator/FrameworkSelector.vue`

```vue
<template>
  <div class="framework-grid">
    <div v-for="f in frameworks" 
         :class="['framework-card', { selected: modelValue === f.id }]"
         @click="$emit('update:modelValue', f.id)">
      <span class="icon">{{ f.icon }}</span>
      <span class="name">{{ f.name }}</span>
      <span class="lang">{{ f.language }}</span>
    </div>
  </div>
</template>
```

### Frameworks

| ID | Name | Icon | Language |
|----|------|------|----------|
| pytest | pytest | 🐍 | Python |
| restassured | REST Assured | ☕ | Java |
| postman | Postman | 📮 | JSON |
| cypress | Cypress | 🌲 | JavaScript |
| k6 | k6 | ⚡ | JavaScript |

### Requirements

- Grid layout 3 columns
- Hover effect
- Selected state with border

---

## P5: Code Preview Component

### Create `components/generator/CodePreview.vue`

```vue
<template>
  <div class="code-preview">
    <div class="preview-header">
      <span>{{ title }}</span>
      <button @click="copyCode">📋 Copy</button>
    </div>
    <pre><code :class="language">{{ code }}</code></pre>
  </div>
</template>
```

### Interface

```javascript
defineProps({
  title: String,
  code: String,
  language: String // 'python' | 'java' | 'javascript' | 'json'
})
```

### Requirements

- Syntax highlighting (use highlight.js or Prism)
- Copy to clipboard
- Line numbers
- Max height with scroll

---

## P6: Generation History Component

### Create `components/generator/GenerationHistory.vue`

```vue
<template>
  <div class="history-panel">
    <h3>История генераций</h3>
    <div v-for="item in history" class="history-item">
      <div class="meta">
        <span>{{ item.framework }}</span>
        <span>{{ item.endpoints }} endpoints</span>
        <span>{{ formatDate(item.created_at) }}</span>
      </div>
      <div class="actions">
        <button @click="redownload(item.result_id)">📥</button>
        <button @click="regenerate(item)">🔄</button>
      </div>
    </div>
  </div>
</template>
```

### Interface

```javascript
// Internal state from localStorage
const history = ref(JSON.parse(localStorage.getItem('generation_history') || '[]'))

// Max 20 items, FIFO
function addToHistory(item) { ... }
```

### Requirements

- Store in localStorage
- Max 20 items
- Re-download and re-generate buttons
- Clear history option

---

## P7: Updated GeneratorView

### Structure

```vue
<template>
  <div class="generator-page">
    <div class="generator-main">
      <!-- Left: Input -->
      <div class="input-section">
        <InputTabs v-model="inputType" @input-ready="onInputReady" />
        <FrameworkSelector v-model="framework" />
        <ProviderSelector v-model="provider" v-model:model="model" />
        <button @click="generate" :disabled="!canGenerate">
          🚀 Генерировать
        </button>
      </div>
      
      <!-- Center: Progress/Results -->
      <div class="output-section">
        <GenerationProgress v-if="step === 'progress'" ... />
        <CodePreview v-if="step === 'results'" ... />
      </div>
    </div>
    
    <!-- Right: History -->
    <GenerationHistory class="history-sidebar" />
  </div>
</template>
```

### Layout

```
┌─────────────────────────────────────────────────────┐
│  🔧 Генератор тестов                                │
├─────────────┬─────────────────────┬─────────────────┤
│ Input Tabs  │ Progress/Preview    │ History         │
│ Framework   │                     │                 │
│ Provider    │                     │                 │
│ [Generate]  │                     │                 │
└─────────────┴─────────────────────┴─────────────────┘
```

---

## P8: Provider Selector Update

### Update `components/generator/LLMSettings.vue` → `ProviderSelector.vue`

Add model selection per provider:

```javascript
const providerModels = {
  anthropic: ['claude-sonnet-4-20250514', 'claude-haiku-4-5-20251001'],
  openai: ['gpt-4o', 'gpt-4o-mini'],
  groq: ['llama-3.3-70b-versatile', 'mixtral-8x7b-32768'],
  ollama: ['qwen2.5-coder:7b', 'codellama:7b']
}
```

---

## Tests Required

```javascript
// tests/generator.spec.js

describe('InputTabs', () => {
  it('switches between tabs')
  it('emits input-ready with correct type')
  it('persists tab selection')
})

describe('SessionSelector', () => {
  it('loads sessions with recorded_requests')
  it('filters empty sessions')
  it('shows endpoint preview')
})

describe('FrameworkSelector', () => {
  it('renders all frameworks')
  it('emits selection')
  it('shows selected state')
})

describe('CodePreview', () => {
  it('applies syntax highlighting')
  it('copies to clipboard')
  it('shows line numbers')
})

describe('GenerationHistory', () => {
  it('loads from localStorage')
  it('limits to 20 items')
  it('allows re-download')
})
```

---

## Design Tokens

```css
:root {
  --gradient-primary: linear-gradient(135deg, #667eea, #764ba2);
  --bg-card: #1a1a2e;
  --bg-secondary: #16213e;
  --border-color: #2a2a4a;
  --text-primary: #ffffff;
  --text-secondary: #a0a0b0;
  --accent: #667eea;
  --success: #4CAF50;
  --error: #f44336;
}
```

---

## File Summary

| File | Action |
|------|--------|
| `components/generator/InputTabs.vue` | Create |
| `components/generator/SessionSelector.vue` | Create |
| `components/generator/UrlInput.vue` | Create |
| `components/generator/FrameworkSelector.vue` | Create |
| `components/generator/CodePreview.vue` | Create |
| `components/generator/GenerationHistory.vue` | Create |
| `components/generator/ProviderSelector.vue` | Rename from LLMSettings |
| `views/GeneratorView.vue` | Rewrite |

---

## Commits

```
[Wave 6.0] P1: Add InputTabs component
[Wave 6.0] P2: Add SessionSelector component
[Wave 6.0] P3: Add UrlInput component
[Wave 6.0] P4: Add FrameworkSelector component
[Wave 6.0] P5: Add CodePreview with syntax highlighting
[Wave 6.0] P6: Add GenerationHistory component
[Wave 6.0] P7: Rewrite GeneratorView with full layout
[Wave 6.0] P8: Update ProviderSelector with model selection
```

---

## Quality Gates

- [ ] All tabs functional
- [ ] Session selector loads sessions
- [ ] URL input validates
- [ ] All 5 frameworks selectable
- [ ] Code preview highlights syntax
- [ ] History persists in localStorage
- [ ] Layout responsive
- [ ] ErrorLens design applied
