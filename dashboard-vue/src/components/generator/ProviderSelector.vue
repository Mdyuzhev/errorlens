<template>
  <div class="llm-settings">
    <h3><AppIcon name="cpu" :size="16" :glow="false" /> LLM Providers</h3>
    <div class="provider-list">
      <div v-for="p in providers" :key="p.id" class="provider-item"
           :class="{ active: p.id === activeProvider, configured: p.configured }"
           @click="activeProvider = p.id">
        <span style="display:flex;align-items:center"><AppIcon v-if="p.iconName" :name="p.iconName" :size="16" :glow="false" /></span>
        <div>
          <span style="font-weight:600">{{ p.name }}</span><br>
          <span style="font-size:12px;color:var(--text-secondary)"><template v-if="p.configured"><AppIcon name="check" :size="14" :glow="false" /> Настроен</template><template v-else>Требует API ключ</template></span>
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
          <AppIcon :name="showKey ? 'x' : 'eye'" :size="16" :glow="false" />
        </button>
      </div>
      <button @click="saveApiKey"
              :disabled="!apiKey"
              style="margin-top:12px;padding:10px 20px;background:var(--accent);color:white;border:none;border-radius:8px;font-weight:600;cursor:pointer">
        Сохранить
      </button>
    </div>

    <div>
      <label>Модель</label>
      <select v-model="selectedModel"
              style="width:100%;padding:10px;background:var(--bg-secondary);border:1px solid var(--border-color);border-radius:8px;color:var(--text-primary)">
        <option v-for="m in availableModels" :key="m.id" :value="m.id">{{ m.name }}</option>
      </select>
    </div>

    <div v-if="message"
         :style="{ marginTop: '12px', padding: '10px', borderRadius: '8px', background: 'rgba(16,185,129,0.1)', color: 'var(--success)' }">
      {{ message }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: 'ollama'
  },
  model: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'update:model'])

const providerModels = {
  anthropic: [
    { id: 'claude-sonnet-4-20250514', name: 'Claude Sonnet 4' },
    { id: 'claude-haiku-4-5-20251001', name: 'Claude Haiku 4.5' }
  ],
  openai: [
    { id: 'gpt-4o', name: 'GPT-4o' },
    { id: 'gpt-4o-mini', name: 'GPT-4o Mini' }
  ],
  groq: [
    { id: 'llama-3.3-70b-versatile', name: 'Llama 3.3 70B' },
    { id: 'mixtral-8x7b-32768', name: 'Mixtral 8x7B' }
  ],
  gemini: [
    { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash' }
  ],
  ollama: [
    { id: 'mistral', name: 'Mistral 7B' },
    { id: 'tinyllama', name: 'TinyLlama 1B' }
  ]
}

const providers = ref([
  {
    id: 'anthropic',
    name: 'Anthropic Claude',
    iconName: 'layers',
    keyPlaceholder: 'sk-ant-...',
    configured: false,
    isLocal: false
  },
  {
    id: 'openai',
    name: 'OpenAI GPT',
    iconName: 'globe',
    keyPlaceholder: 'sk-...',
    configured: false,
    isLocal: false
  },
  {
    id: 'groq',
    name: 'Groq',
    iconName: 'zap',
    keyPlaceholder: 'gsk_...',
    configured: false,
    isLocal: false
  },
  {
    id: 'gemini',
    name: 'Google Gemini',
    iconName: 'sun',
    keyPlaceholder: 'AIza...',
    configured: false,
    isLocal: false
  },
  {
    id: 'ollama',
    name: 'Ollama (Local)',
    iconName: 'cpu',
    configured: true,
    isLocal: true
  }
])

const activeProvider = ref(props.modelValue)
const apiKey = ref('')
const showKey = ref(false)
const selectedModel = ref(props.model)
const message = ref('')

const selectedProvider = computed(() =>
  providers.value.find(p => p.id === activeProvider.value)
)

const availableModels = computed(() =>
  providerModels[activeProvider.value] || []
)

watch(activeProvider, (newProvider) => {
  emit('update:modelValue', newProvider)

  if (availableModels.value.length > 0 && !selectedModel.value) {
    selectedModel.value = availableModels.value[0].id
    emit('update:model', selectedModel.value)
  }
})

watch(selectedModel, (newModel) => {
  emit('update:model', newModel)
})

onMounted(() => {
  const keys = JSON.parse(localStorage.getItem('llm_api_keys') || '{}')
  providers.value.forEach(p => {
    if (!p.isLocal && keys[p.id]) p.configured = true
  })

  const saved = localStorage.getItem('llm_default_provider')
  if (saved) {
    activeProvider.value = saved
  }

  if (availableModels.value.length > 0 && !selectedModel.value) {
    selectedModel.value = availableModels.value[0].id
    emit('update:model', selectedModel.value)
  }
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
  border-color: var(--accent);
  background: var(--accent-muted);
}

.provider-item.configured span:last-child span:last-child {
  color: var(--success);
}

</style>
