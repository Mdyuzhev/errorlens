<template>
  <div class="settings-page">
    <h1>Settings</h1>

    <div class="settings-grid">
      <!-- User Info -->
      <div class="settings-card">
        <h2>Account</h2>
        <div class="setting-item">
          <label>Username</label>
          <span class="value">{{ auth.user?.username }}</span>
        </div>
        <div class="setting-item">
          <label>Role</label>
          <span class="value badge-info">{{ auth.user?.role || 'user' }}</span>
        </div>
      </div>

      <!-- API Info -->
      <div class="settings-card">
        <h2>API</h2>
        <div class="setting-item">
          <label>API URL</label>
          <span class="value code">{{ apiUrl }}</span>
        </div>
        <div class="setting-item">
          <label>Status</label>
          <span class="value" :class="apiStatus === 'OK' ? 'badge-success' : 'badge-error'">
            {{ apiStatus }}
          </span>
        </div>
      </div>

      <!-- Bookmarklet -->
      <div class="settings-card">
        <h2>Bookmarklet</h2>
        <p class="hint">Drag the button below to your bookmarks bar:</p>
        <a
          :href="bookmarkletCode"
          class="bookmarklet-btn"
          @click.prevent
          draggable="true"
        >
          ErrorLens
        </a>
        <p class="hint" style="margin-top: 12px;">
          Or copy the code manually:
        </p>
        <button class="btn btn-secondary" @click="copyBookmarklet">
          Copy Bookmarklet Code
        </button>
      </div>

      <!-- About -->
      <div class="settings-card">
        <h2>About</h2>
        <div class="setting-item">
          <label>Version</label>
          <span class="value">2.0.0</span>
        </div>
        <div class="setting-item">
          <label>Repository</label>
          <a href="https://github.com/Mdyuzhev/errorlens" target="_blank" class="value link">
            github.com/Mdyuzhev/errorlens
          </a>
        </div>
        <div class="setting-item">
          <label>Stack</label>
          <span class="value">Vue 3 + FastAPI + SQLite</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import api from '@/services/api'

const auth = useAuthStore()

const apiUrl = import.meta.env.VITE_API_URL || '/api'
const apiStatus = ref('Checking...')

const bookmarkletCode = ref('')

onMounted(async () => {
  // Check API status
  try {
    await api.get('/health')
    apiStatus.value = 'OK'
  } catch {
    apiStatus.value = 'Error'
  }

  // Generate bookmarklet code
  const baseUrl = window.location.origin
  bookmarkletCode.value = `javascript:(function(){var s=document.createElement('script');s.src='${baseUrl}/bookmarklet/recorder.js';document.body.appendChild(s);})();`
})

function copyBookmarklet() {
  navigator.clipboard.writeText(bookmarkletCode.value)
  alert('Bookmarklet code copied!')
}
</script>

<style scoped>
.settings-page h1 {
  margin-bottom: 24px;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.settings-card {
  background: var(--bg-card);
  padding: 24px;
  border-radius: 12px;
}

.settings-card h2 {
  font-size: 18px;
  margin: 0 0 20px 0;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--bg-secondary);
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--bg-secondary);
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-item label {
  color: var(--text-secondary);
  font-size: 14px;
}

.setting-item .value {
  font-size: 14px;
}

.setting-item .value.code {
  font-family: monospace;
  background: var(--bg-secondary);
  padding: 4px 8px;
  border-radius: 4px;
}

.setting-item .value.link {
  color: var(--accent);
}

.hint {
  color: var(--text-secondary);
  font-size: 13px;
  margin-bottom: 12px;
}

.bookmarklet-btn {
  display: inline-block;
  padding: 12px 24px;
  background: linear-gradient(135deg, var(--accent) 0%, #9333ea 100%);
  color: white;
  border-radius: 8px;
  font-weight: 600;
  text-decoration: none;
  cursor: grab;
  transition: all 0.2s;
}

.bookmarklet-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.4);
}

.bookmarklet-btn:active {
  cursor: grabbing;
}
</style>
