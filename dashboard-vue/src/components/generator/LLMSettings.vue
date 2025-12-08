<template>
  <div class="llm-settings">
    <h3>🤖 LLM Providers</h3>
    <div class="provider-list">
      <div v-for="p in providers" :key="p.id" class="provider-item"
           :class="{ active: p.id === activeProvider, configured: p.configured }"
           @click="activeProvider = p.id">
        <span style="font-size:24px">{{ p.icon }}</span>
        <div>
          <span style="font-weight:600">{{ p.name }}</span><br>
          <span style="font-size:12px;color:var(--text-secondary)">{{ p.configured ? '✓ Настроен' : 'Требует API ключ' }}</span>
        </div>
      </div>
    </div>

    <div v-if="selectedProvider && !selectedProvider.isLocal" style="margin-bottom:16px">
      <label>{{ selectedProvider.name }} API Key</label>
      <div style="display:flex;gap:8px">
        <input :type="showKey ? 'text' : 'password'"
               v-model="apiKey"
               :placeholder="selectedProvider.keyPlaceholder"
               style="flex:1;padding:10px;background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:8px;font-family:monospace" />
        <button @click="showKey = !showKey"
                style="padding:10px 12px;background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:8px">
          {{ showKey ? '🙈' : '👁️' }}
        </button>
      </div>
      <button @click="saveApiKey"
              :disabled="!apiKey"
              style="margin-top:12px;padding:10px 20px;background:linear-gradient(135deg,#667eea,#764ba2);color:white;border:none;border-radius:8px;font-weight:600;cursor:pointer">
        Сохранить
      </button>
    </div>

    <div>
      <label>Модель</label>
      <select v-model="selectedModel"
              style="width:100%;padding:10px;background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:8px">
        <option v-for="m in selectedProvider?.models" :key="m.id" :value="m.id">{{ m.name }}</option>
      </select>
    </div>

    <div v-if="message"
         :style="{ marginTop: '12px', padding: '10px', borderRadius: '8px', background: 'rgba(76,175,80,0.1)', color: '#4CAF50' }">
      {{ message }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const providers = ref([
  {
    id: 'anthropic',
    name: 'Anthropic Claude',
    icon: '🟣',
    keyPlaceholder: 'sk-ant-...',
    configured: false,
    isLocal: false,
    models: [
      { id: 'claude-sonnet-4-20250514', name: 'Claude Sonnet 4' },
      { id: 'claude-haiku-4-5-20251001', name: 'Claude Haiku 4.5' }
    ]
  },
  {
    id: 'openai',
    name: 'OpenAI GPT',
    icon: '🟢',
    keyPlaceholder: 'sk-...',
    configured: false,
    isLocal: false,
    models: [
      { id: 'gpt-4o', name: 'GPT-4o' },
      { id: 'gpt-4o-mini', name: 'GPT-4o Mini' }
    ]
  },
  {
    id: 'groq',
    name: 'Groq',
    icon: '🔵',
    keyPlaceholder: 'gsk_...',
    configured: false,
    isLocal: false,
    models: [
      { id: 'llama-3.3-70b-versatile', name: 'Llama 3.3 70B' }
    ]
  },
  {
    id: 'gemini',
    name: 'Google Gemini',
    icon: '🟡',
    keyPlaceholder: 'AIza...',
    configured: false,
    isLocal: false,
    models: [
      { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash' }
    ]
  },
  {
    id: 'ollama',
    name: 'Ollama (Local)',
    icon: '🏠',
    configured: true,
    isLocal: true,
    models: [
      { id: 'qwen2.5-coder:7b', name: 'Qwen 2.5 Coder 7B' }
    ]
  },
])

const activeProvider = ref('ollama')
const apiKey = ref('')
const showKey = ref(false)
const selectedModel = ref('')
const message = ref('')

const selectedProvider = computed(() => providers.value.find(p => p.id === activeProvider.value))

onMounted(() => {
  const keys = JSON.parse(localStorage.getItem('llm_api_keys') || '{}')
  providers.value.forEach(p => {
    if (!p.isLocal && keys[p.id]) p.configured = true
  })
  const saved = localStorage.getItem('llm_default_provider')
  if (saved) activeProvider.value = saved
})

function saveApiKey() {
  const keys = JSON.parse(localStorage.getItem('llm_api_keys') || '{}')
  keys[activeProvider.value] = apiKey.value
  localStorage.setItem('llm_api_keys', JSON.stringify(keys))
  localStorage.setItem('llm_default_provider', activeProvider.value)

  const p = providers.value.find(p => p.id === activeProvider.value)
  if (p) p.configured = true

  message.value = 'API ключ сохранён'
  apiKey.value = ''
  setTimeout(() => message.value = '', 3000)
}
</script>

<style scoped>
.llm-settings h3 {
  margin: 0 0 16px;
  font-size: 16px;
}

.llm-settings label {
  display: block;
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.provider-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}

.provider-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s;
}

.provider-item:hover {
  background: var(--bg-tertiary);
}

.provider-item.active {
  border-color: #667eea;
  background: rgba(102, 126, 234, 0.1);
}

.provider-item.configured span:last-child span:last-child {
  color: #4CAF50;
}
</style>
