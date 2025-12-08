# Wave 4.0 P7: Settings UI

## Scope

Create:
- `dashboard-vue/src/components/generator/LLMSettings.vue`

Update:
- `dashboard-vue/src/views/SettingsView.vue`
- `dashboard-vue/src/views/GeneratorView.vue`

## Interfaces

### LLMSettings.vue

```javascript
// Props
props: {}

// Emits
emits: ['provider-changed', 'model-changed']

// Internal state
const providers = ref([
  { id: 'anthropic', name: 'Anthropic Claude', icon: '🟣', models: [...], configured: false },
  { id: 'openai', name: 'OpenAI GPT', icon: '🟢', models: [...], configured: false },
  { id: 'groq', name: 'Groq', icon: '🔵', models: [...], configured: false },
  { id: 'gemini', name: 'Google Gemini', icon: '🟡', models: [...], configured: false },
  { id: 'ollama', name: 'Ollama (Local)', icon: '🏠', models: [...], configured: true, isLocal: true },
])

const activeProvider = ref('ollama')
const selectedModel = ref('')
```

## Requirements

### Storage
- API keys: `localStorage.llm_api_keys` (JSON object)
- Default provider: `localStorage.llm_default_provider`
- Default model: `localStorage.llm_default_model`

### Security
- Mask API keys in input (type="password")
- Toggle visibility button
- Clear input after save

### Provider Models

| Provider | Models |
|----------|--------|
| anthropic | claude-sonnet-4-20250514, claude-haiku-4-5-20251001 |
| openai | gpt-4o, gpt-4o-mini |
| groq | llama-3.3-70b-versatile, mixtral-8x7b-32768 |
| gemini | gemini-1.5-flash, gemini-1.5-pro |
| ollama | qwen2.5-coder:7b, codellama:7b, mistral:7b |

### UI States
- Unconfigured: show "Requires API key"
- Configured: show "✓ Configured"
- Local (Ollama): always configured, no key needed

### Integration with GeneratorView
- Load saved provider/model on mount
- Apply to generation requests

## Prohibited

- Store API keys in Pinia (localStorage only)
- Show API keys in console
- Hard-coded model lists (define as const)

## Tests Required

```javascript
// tests/settings.spec.js

describe('LLMSettings', () => {
  it('loads saved provider from localStorage')
  it('saves API key to localStorage')
  it('masks API key by default')
  it('toggles key visibility')
  it('clears input after save')
  it('marks provider as configured after save')
  it('emits provider-changed on selection')
})
```

## SettingsView Update

Add after existing cards:
```vue
<div class="settings-card" style="grid-column: 1 / -1">
  <LLMSettings @provider-changed="..." @model-changed="..." />
</div>
```

## GeneratorView Update

Load settings on mount:
```javascript
onMounted(() => {
  provider.value = localStorage.getItem('llm_default_provider') || 'anthropic'
  model.value = localStorage.getItem('llm_default_model') || ''
})
```

## Commit

```
[Wave 4.0] P7: Add LLM Settings UI with provider configuration
```
