<template>
  <div class="settings-page">
    <h1>Settings</h1>

    <!-- Tab navigation -->
    <div class="tabs">
      <button
        class="tab"
        :class="{ active: activeTab === 'general' }"
        @click="activeTab = 'general'"
      >
        General
      </button>
      <button
        class="tab"
        :class="{ active: activeTab === 'projects' }"
        @click="activeTab = 'projects'"
      >
        Projects
      </button>
      <button
        class="tab"
        :class="{ active: activeTab === 'tasks' }"
        @click="activeTab = 'tasks'"
      >
        Tasks
      </button>
      <button
        class="tab"
        :class="{ active: activeTab === 'automations' }"
        @click="activeTab = 'automations'"
      >
        Automations
      </button>
      <button
        class="tab"
        :class="{ active: activeTab === 'integrations' }"
        @click="activeTab = 'integrations'"
      >
        Integrations
      </button>
      <button
        v-if="auth.user?.is_admin"
        class="tab"
        :class="{ active: activeTab === 'users' }"
        @click="activeTab = 'users'"
      >
        Users
      </button>
    </div>

    <!-- General tab -->
    <div v-if="activeTab === 'general'" class="tab-content">
      <div class="settings-grid">
        <!-- Profile Section -->
        <div class="settings-card" data-testid="profile-section">
          <h2>Profile</h2>
          <div class="setting-item">
            <label>Username</label>
            <span class="value">{{ auth.user?.username }}</span>
          </div>
          <div class="setting-item">
            <label>Role</label>
            <span class="value badge-info">{{ auth.user?.role || 'user' }}</span>
          </div>
        </div>

        <!-- Theme Settings -->
        <div class="settings-card" data-testid="theme-section">
          <h2>Theme</h2>
          <div class="theme-selector">
            <div
              class="theme-option"
              :class="{ active: themeStore.theme === 'dark' }"
              @click="themeStore.setTheme('dark')"
              data-testid="theme-option-dark"
            >
              <div class="theme-preview theme-preview--dark">
                <div class="tp-bar"></div>
                <div class="tp-card"></div>
                <div class="tp-btn"></div>
              </div>
              <div class="theme-option-label">Dark</div>
            </div>

            <div
              class="theme-option"
              :class="{ active: themeStore.theme === 'light' }"
              @click="themeStore.setTheme('light')"
              data-testid="theme-option-light"
            >
              <div class="theme-preview theme-preview--light">
                <div class="tp-bar"></div>
                <div class="tp-card"></div>
                <div class="tp-btn"></div>
              </div>
              <div class="theme-option-label">Light</div>
            </div>

            <div
              class="theme-option"
              :class="{ active: themeStore.theme === 'retrowave' }"
              @click="themeStore.setTheme('retrowave')"
              data-testid="theme-option-retrowave"
            >
              <div class="theme-preview theme-preview--retrowave">
                <div class="tp-bar"></div>
                <div class="tp-card"></div>
                <div class="tp-btn"></div>
              </div>
              <div class="theme-option-label">RetroWave</div>
              <div class="theme-option-badge">8-bit</div>
            </div>

            <div
              class="theme-option"
              :class="{ active: themeStore.theme === 'corp' }"
              @click="themeStore.setTheme('corp')"
              data-testid="theme-option-corp"
            >
              <div class="theme-preview theme-preview--corp">
                <div class="tp-bar"></div>
                <div class="tp-card"></div>
                <div class="tp-btn"></div>
              </div>
              <div class="theme-option-label">Corp</div>
              <div class="theme-option-badge theme-option-badge--corp">Corp</div>
            </div>
          </div>
        </div>

        <!-- API Key Section -->
        <div class="settings-card" data-testid="api-key-section">
          <h2>API Key</h2>
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

        <!-- Bookmarklet with Onboarding -->
        <div class="settings-card bookmarklet-card" :class="{ 'onboarding-active': showOnboarding }">
          <div class="card-header">
            <h2>Bookmarklet</h2>
            <button
              v-if="!showOnboarding"
              class="help-btn"
              @click="startOnboarding"
              title="Show tutorial"
            >
              ?
            </button>
          </div>

          <!-- Onboarding overlay -->
          <div v-if="showOnboarding" class="onboarding-overlay">
            <div class="onboarding-step" :class="{ active: onboardingStep === 1 }">
              <div class="step-number">1</div>
              <div class="step-content">
                <h3>Перетащите в закладки</h3>
                <p>Перетащите фиолетовую кнопку "ErrorLens" на панель закладок браузера</p>
              </div>
            </div>
            <div class="onboarding-step" :class="{ active: onboardingStep === 2 }">
              <div class="step-number">2</div>
              <div class="step-content">
                <h3>Откройте любой сайт</h3>
                <p>Перейдите на сайт, который хотите протестировать на ошибки</p>
              </div>
            </div>
            <div class="onboarding-step" :class="{ active: onboardingStep === 3 }">
              <div class="step-number">3</div>
              <div class="step-content">
                <h3>Нажмите букмарклет</h3>
                <p>Кликните на закладку ErrorLens чтобы начать запись ошибок и запросов</p>
              </div>
            </div>
            <div class="onboarding-controls">
              <button v-if="onboardingStep > 1" class="btn btn--ghost" @click="onboardingStep--">
                Назад
              </button>
              <button v-if="onboardingStep < 3" class="btn btn-primary" @click="onboardingStep++">
                Далее
              </button>
              <button v-else class="btn btn-primary" @click="finishOnboarding">
                Понятно!
              </button>
            </div>
          </div>

          <!-- Normal content -->
          <div v-else>
            <p class="hint">Перетащите кнопку ниже на панель закладок:</p>
            <a
              :href="bookmarkletCode"
              class="bookmarklet-btn"
              @click.prevent
              draggable="true"
            >
              ErrorLens
            </a>
            <p class="hint" style="margin-top: 16px;">
              Или скопируйте короткий код загрузчика:
            </p>
            <div class="code-display">
              <code>{{ shortBookmarkletCode }}</code>
              <button class="copy-btn" @click="copyBookmarklet" :class="{ copied: justCopied }">
                {{ justCopied ? '✓' : 'Копировать' }}
              </button>
            </div>
          </div>
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
            <span class="value">Vue 3 + FastAPI + PostgreSQL</span>
          </div>
        </div>

        <!-- LLM Settings -->
        <div class="settings-card settings-card--full">
          <LLMSettings />
        </div>
      </div>
    </div>

    <!-- Projects tab -->
    <div v-if="activeTab === 'projects'" class="tab-content">
      <ProjectsTab />
    </div>

    <!-- Tasks tab -->
    <div v-if="activeTab === 'tasks'" class="tab-content">
      <TaskSettingsTab />
    </div>

    <!-- Automations tab -->
    <div v-if="activeTab === 'automations'" class="tab-content">
      <AutomationsTab />
    </div>

    <!-- Integrations tab -->
    <div v-if="activeTab === 'integrations'" class="tab-content">
      <GitLabConnections />
    </div>

    <!-- Users tab (admin only) -->
    <div v-if="activeTab === 'users'" class="tab-content">
      <UsersTab v-if="auth.user?.is_admin" />
      <div v-else class="access-denied">
        <p>Доступ запрещён</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import api from '@/services/api'
import LLMSettings from '@/components/generator/ProviderSelector.vue'
import ProjectsTab from '@/components/settings/ProjectsTab.vue'
import TaskSettingsTab from '@/components/settings/TaskSettingsTab.vue'
import UsersTab from '@/components/settings/UsersTab.vue'
import GitLabConnections from '@/components/settings/GitLabConnections.vue'
import AutomationsTab from '@/components/settings/AutomationsTab.vue'

const auth = useAuthStore()
const themeStore = useThemeStore()

const activeTab = ref('general')

const apiUrl = import.meta.env.VITE_API_URL || '/api'
const apiStatus = ref('Checking...')
const bookmarkletCode = ref('')
const shortBookmarkletCode = ref('')
const justCopied = ref(false)

// Onboarding state
const showOnboarding = ref(false)
const onboardingStep = ref(1)

onMounted(async () => {
  // Check API status
  try {
    await api.get('/health')
    apiStatus.value = 'OK'
  } catch {
    apiStatus.value = 'Error'
  }

  // Generate bookmarklet code - use API URL for backend, not frontend origin
  const baseUrl = import.meta.env.VITE_API_URL || window.location.origin
  bookmarkletCode.value = `javascript:(function(){var s=document.createElement('script');s.src='${baseUrl}/bookmarklet/recorder.js';document.body.appendChild(s);})();`

  // Short version for display
  shortBookmarkletCode.value = `javascript:(function(){var s=document.createElement('script');s.src='${baseUrl}/bookmarklet/recorder.js';document.body.appendChild(s);})();`

  // Show onboarding for first-time users
  if (!localStorage.getItem('errorlens_settings_onboarding_done')) {
    showOnboarding.value = true
  }
})

function startOnboarding() {
  onboardingStep.value = 1
  showOnboarding.value = true
}

function finishOnboarding() {
  showOnboarding.value = false
  localStorage.setItem('errorlens_settings_onboarding_done', 'true')
}

function copyBookmarklet() {
  navigator.clipboard.writeText(shortBookmarkletCode.value)
  justCopied.value = true
  setTimeout(() => {
    justCopied.value = false
  }, 2000)
}
</script>

<style scoped>
.settings-page h1 {
  margin-bottom: 16px;
}

/* Tabs */
.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 24px;
  border-bottom: 2px solid var(--bg-secondary);
  padding-bottom: 0;
}

.tab {
  padding: 10px 20px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.tab:hover {
  color: var(--text-primary);
}

.tab.active {
  color: var(--text-primary);
  border-bottom-color: var(--accent);
}

.tab-content {
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.access-denied {
  padding: 40px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 16px;
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

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--bg-secondary);
}

.card-header h2 {
  margin: 0;
  padding: 0;
  border: none;
}

.help-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
}

.help-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 2px 10px rgba(102, 126, 234, 0.4);
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 8px;
  font-weight: 600;
  text-decoration: none;
  cursor: grab;
  transition: all 0.2s;
}

.bookmarklet-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.bookmarklet-btn:active {
  cursor: grabbing;
}

/* Code display */
.code-display {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 8px 12px;
  margin-top: 8px;
}

.code-display code {
  flex: 1;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 11px;
  color: var(--text-secondary);
  word-break: break-all;
  line-height: 1.4;
}

.copy-btn {
  padding: 6px 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 60px;
}

.copy-btn:hover {
  transform: scale(1.05);
}

.copy-btn.copied {
  background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
}

/* Onboarding styles */
.bookmarklet-card.onboarding-active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.bookmarklet-card.onboarding-active h2 {
  color: white;
  border-bottom-color: rgba(255, 255, 255, 0.2);
}

.bookmarklet-card.onboarding-active .card-header {
  border-bottom-color: rgba(255, 255, 255, 0.2);
}

.bookmarklet-card.onboarding-active .hint {
  color: rgba(255, 255, 255, 0.9);
}

.onboarding-overlay {
  animation: fadeIn 0.3s ease;
}

.onboarding-step {
  display: flex;
  gap: 15px;
  padding: 15px;
  margin-bottom: 10px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  opacity: 0.6;
  transition: all 0.3s;
}

.onboarding-step.active {
  opacity: 1;
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.02);
}

.step-number {
  width: 32px;
  height: 32px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 16px;
  flex-shrink: 0;
}

.onboarding-step.active .step-number {
  background: white;
  color: #764ba2;
}

.step-content h3 {
  margin: 0 0 5px 0;
  font-size: 15px;
  font-weight: 600;
}

.step-content p {
  margin: 0;
  font-size: 13px;
  opacity: 0.9;
  line-height: 1.4;
}

.onboarding-controls {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 15px;
}

.btn-ghost, .btn--ghost {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-ghost:hover, .btn--ghost:hover {
  background: rgba(255, 255, 255, 0.3);
}

.btn-primary {
  background: white;
  color: #764ba2;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

/* Theme selector */
.theme-selector {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.theme-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px;
  border: 2px solid transparent;
  border-radius: 8px;
  transition: all 0.2s;
  position: relative;
}

.theme-option:hover {
  border-color: var(--accent-subtle);
  background: var(--accent-bg);
}

.theme-option.active {
  border-color: var(--accent);
}

.theme-preview {
  width: 120px;
  height: 72px;
  border-radius: 6px;
  overflow: hidden;
  position: relative;
  border: 1px solid rgba(255,255,255,0.08);
}

/* Dark preview */
.theme-preview--dark { background: #0f0a1a; }
.theme-preview--dark .tp-bar { background: #231a33; height: 14px; width: 100%; }
.theme-preview--dark .tp-card { background: #231a33; margin: 6px 8px 0; height: 28px; border-radius: 3px; }
.theme-preview--dark .tp-btn { background: #7c3aed; width: 36px; height: 8px; border-radius: 2px; position: absolute; bottom: 6px; right: 8px; }

/* Light preview */
.theme-preview--light { background: #f0f4f8; }
.theme-preview--light .tp-bar { background: #0052cc; height: 14px; width: 100%; }
.theme-preview--light .tp-card { background: #fff; margin: 6px 8px 0; height: 28px; border-radius: 3px; border: 1px solid #dfe1e6; }
.theme-preview--light .tp-btn { background: #0052cc; width: 36px; height: 8px; border-radius: 2px; position: absolute; bottom: 6px; right: 8px; }

/* RetroWave preview */
.theme-preview--retrowave { background: #0a0014; }
.theme-preview--retrowave .tp-bar { background: #12002a; height: 14px; width: 100%; border-bottom: 1px solid rgba(5,217,232,0.4); }
.theme-preview--retrowave .tp-card { background: #1a0035; margin: 6px 8px 0; height: 28px; border: 1px solid rgba(5,217,232,0.25); }
.theme-preview--retrowave .tp-btn { background: #ff2d78; width: 36px; height: 8px; position: absolute; bottom: 6px; right: 8px; box-shadow: 0 0 6px rgba(255,45,120,0.6); }

/* Corp preview */
.theme-preview--corp { background: #f0f4ff; }
.theme-preview--corp .tp-bar {
  background: #ffffff; height: 14px; width: 100%;
  border-bottom: 1px solid #e2e8f0;
}
.theme-preview--corp .tp-card {
  background: #ffffff; margin: 6px 8px 0; height: 28px;
  border-radius: 3px; border: 1px solid #e2e8f0;
}
.theme-preview--corp .tp-btn {
  background: #2563eb; width: 36px; height: 8px; border-radius: 2px;
  position: absolute; bottom: 6px; right: 8px;
}
.theme-option-badge--corp {
  position: absolute; top: 4px; right: 4px;
  background: #2563eb; color: white;
  font-size: 9px; font-weight: 700; padding: 1px 5px;
  border-radius: 3px; letter-spacing: 0.05em;
}

.theme-option-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.theme-option.active .theme-option-label {
  color: var(--text-primary);
  font-weight: 600;
}

.theme-option-badge {
  position: absolute;
  top: 4px;
  right: 4px;
  background: #ff2d78;
  color: white;
  font-size: 9px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 3px;
  letter-spacing: 0.05em;
}

.settings-card--full {
  grid-column: 1 / -1;
}
</style>
