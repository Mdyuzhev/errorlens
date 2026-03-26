<template>
  <div class="login-page">
    <!-- Left: App preview -->
    <div class="login-preview">
      <div class="preview-brand">
        <svg class="brand-icon" xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <span class="brand-name">ErrorLens</span>
      </div>
      <p class="preview-subtitle">AI-платформа для QA-инженеров</p>

      <div class="preview-cards">
        <div class="preview-card">
          <div class="preview-card-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 2h6l3 7H6L9 2z"/><path d="M12 9v13"/><path d="M8 22h8"/><path d="M5 12l-2 4h18l-2-4"/></svg>
          </div>
          <div>
            <div class="preview-card-title">QA</div>
            <div class="preview-card-desc">Тест-кейсы, планы и прогоны</div>
          </div>
        </div>
        <div class="preview-card">
          <div class="preview-card-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 8h7"/><path d="M9 12h7"/><path d="M9 16h4"/></svg>
          </div>
          <div>
            <div class="preview-card-title">Issues</div>
            <div class="preview-card-desc">Задачи и баг-трекер</div>
          </div>
        </div>
        <div class="preview-card">
          <div class="preview-card-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/><path d="M8 7h6"/><path d="M8 11h8"/></svg>
          </div>
          <div>
            <div class="preview-card-title">Articles</div>
            <div class="preview-card-desc">База знаний команды</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Right: Login form -->
    <div class="login-form-side">
      <div class="login-card">
        <h2 class="login-heading">Войти в систему</h2>

        <div v-if="error" class="error-alert">
          {{ error }}
        </div>

        <form @submit.prevent="handleLogin">
          <div class="form-group">
            <label for="username">Username</label>
            <input
              type="text"
              id="username"
              v-model="username"
              required
              autofocus
              placeholder="admin"
            />
          </div>

          <div class="form-group">
            <label for="password">Password</label>
            <input
              type="password"
              id="password"
              v-model="password"
              required
              placeholder="••••••••"
            />
          </div>

          <button type="submit" class="btn-login" :disabled="loading">
            <span v-if="loading" class="spinner"></span>
            <span v-else>Войти</span>
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  loading.value = true
  error.value = ''

  const success = await auth.login(username.value, password.value)

  if (success) {
    router.push('/')
  } else {
    error.value = auth.error
  }

  loading.value = false
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
}

/* ── Left column: app preview ── */
.login-preview {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 60px 56px;
  background: linear-gradient(160deg, var(--bg-primary) 0%, #1a0a2e 60%, #2d1b4e 100%);
}

.preview-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.brand-icon {
  flex-shrink: 0;
}

.brand-name {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
}

.preview-subtitle {
  font-size: 16px;
  color: var(--text-secondary);
  margin: 0 0 48px;
}

.preview-cards {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 400px;
}

.preview-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  backdrop-filter: blur(4px);
}

.preview-card-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: rgba(124, 92, 191, 0.15);
  border-radius: 10px;
  color: var(--accent);
}

.preview-card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 2px;
}

.preview-card-desc {
  font-size: 13px;
  color: var(--text-secondary);
}

/* ── Right column: login form ── */
.login-form-side {
  width: 440px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 48px;
  background: var(--bg-card);
  border-left: 1px solid var(--border-color);
}

.login-card {
  width: 100%;
}

.login-heading {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 28px;
}

.error-alert {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  font-size: 14px;
  color: var(--text-secondary);
}

.form-group input {
  width: 100%;
  padding: 12px 16px;
  border-radius: 10px;
  font-size: 15px;
}

.btn-login {
  width: 100%;
  padding: 13px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 8px;
}

.btn-login:hover:not(:disabled) {
  background: var(--accent-hover);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.btn-login:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Mobile: stack columns */
@media (max-width: 768px) {
  .login-page {
    flex-direction: column;
  }

  .login-preview {
    padding: 40px 24px 32px;
  }

  .preview-cards {
    max-width: 100%;
  }

  .login-form-side {
    width: 100%;
    border-left: none;
    border-top: 1px solid var(--border-color);
    padding: 32px 24px;
  }
}
</style>
