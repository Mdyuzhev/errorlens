<template>
  <div class="settings-editor">
    <!-- Toggle settings -->
    <div class="setting-row" v-for="s in toggleSettings" :key="s.key">
      <div class="setting-info">
        <div class="setting-label">{{ s.label }}</div>
        <div class="setting-desc">{{ s.desc }}</div>
      </div>
      <div class="setting-control">
        <button
          class="toggle-btn"
          :class="{ 'toggle-on': localSettings[s.key] }"
          @click="toggle(s.key)"
          :title="localSettings[s.key] ? 'ON' : 'OFF'"
        >
          <span class="toggle-knob"></span>
        </button>
        <span class="toggle-label" :class="localSettings[s.key] ? 'label-on' : 'label-off'">
          {{ localSettings[s.key] ? 'ON' : 'OFF' }}
        </span>
      </div>
    </div>

    <!-- Separator -->
    <div class="settings-divider"></div>

    <!-- Number input settings -->
    <div class="setting-row" v-for="s in numberSettings" :key="s.key">
      <div class="setting-info">
        <div class="setting-label">{{ s.label }}</div>
        <div class="setting-desc">{{ s.desc }}</div>
      </div>
      <div class="setting-control">
        <input
          type="number"
          class="setting-input"
          :min="s.min"
          :max="s.max"
          :placeholder="String(s.default)"
          :value="localSettings[s.key] ?? s.default"
          @change="setNumber(s.key, $event.target.value, s.default)"
        />
      </div>
    </div>

    <!-- Reset to defaults -->
    <div class="settings-footer">
      <button class="btn-reset" @click="resetDefaults">Reset to defaults</button>
    </div>
  </div>
</template>

<script setup>
import { reactive, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) }
})
const emit = defineEmits(['update:modelValue'])

const DEFAULTS = {
  follow_redirects: true,
  verify_ssl: false,
  encode_url: true,
  timeout: 30,
  max_redirects: 10,
}

const toggleSettings = [
  {
    key: 'follow_redirects',
    label: 'Follow redirects',
    desc: 'Automatically follow HTTP 3xx responses as redirects',
  },
  {
    key: 'verify_ssl',
    label: 'Verify SSL certificate',
    desc: 'Validate SSL/TLS certificates. Disable for self-signed certificates',
  },
  {
    key: 'encode_url',
    label: 'Encode URL automatically',
    desc: 'Encode special characters in URL path, query params, and auth fields',
  },
]

const numberSettings = [
  {
    key: 'timeout',
    label: 'Request timeout (seconds)',
    desc: 'Maximum time to wait for a response. Set to 0 for no timeout',
    default: 30, min: 0, max: 300,
  },
  {
    key: 'max_redirects',
    label: 'Maximum number of redirects',
    desc: 'Stop following redirects after this many hops',
    default: 10, min: 0, max: 30,
  },
]

const localSettings = reactive({ ...DEFAULTS, ...props.modelValue })

watch(() => props.modelValue, (val) => {
  Object.assign(localSettings, { ...DEFAULTS, ...val })
}, { deep: true })

function toggle(key) {
  localSettings[key] = !localSettings[key]
  emit('update:modelValue', { ...localSettings })
}

function setNumber(key, val, defaultVal) {
  const n = parseInt(val)
  localSettings[key] = isNaN(n) ? defaultVal : Math.max(0, n)
  emit('update:modelValue', { ...localSettings })
}

function resetDefaults() {
  Object.assign(localSettings, DEFAULTS)
  emit('update:modelValue', { ...DEFAULTS })
}
</script>

<style scoped>
.settings-editor {
  padding: 4px 0;
}

.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 14px 0;
  border-bottom: 1px solid var(--border-color);
}
.setting-row:last-of-type { border-bottom: none; }

.setting-info { flex: 1; min-width: 0; }

.setting-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 3px;
}

.setting-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.setting-control {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* Toggle switch */
.toggle-btn {
  width: 40px;
  height: 22px;
  border-radius: 11px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  cursor: pointer;
  position: relative;
  transition: background 0.2s, border-color 0.2s;
  padding: 0;
}
.toggle-btn.toggle-on {
  background: var(--accent);
  border-color: var(--accent);
}
.toggle-knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: white;
  transition: left 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}
.toggle-btn.toggle-on .toggle-knob { left: 20px; }

.toggle-label {
  font-size: 11px;
  font-weight: 600;
  min-width: 24px;
}
.label-on { color: var(--accent); }
.label-off { color: var(--text-secondary); }

/* Number input */
.setting-input {
  width: 80px;
  padding: 6px 8px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  text-align: center;
  outline: none;
}
.setting-input:focus { border-color: var(--accent); }

.settings-divider {
  height: 1px;
  background: var(--border-color);
  margin: 4px 0;
}

.settings-footer {
  padding-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.btn-reset {
  padding: 5px 12px;
  background: none;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-reset:hover {
  border-color: var(--accent);
  color: var(--accent);
}
</style>
