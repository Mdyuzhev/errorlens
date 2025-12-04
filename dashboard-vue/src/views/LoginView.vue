<template>
  <div class="login-page">
    <div class="login-card">
      <div class="logo">
        <div class="logo-icon">🔍</div>
        <h1>Error<span>Lens</span></h1>
        <p>AI-powered error analysis</p>
      </div>

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
          <span v-else>Login</span>
        </button>
      </form>
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
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: linear-gradient(135deg, var(--bg-primary) 0%, #1a0a2e 50%, #2d1b4e 100%);
}

.login-card {
  width: 100%;
  max-width: 400px;
  background: var(--bg-card);
  padding: 40px;
  border-radius: 24px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.logo {
  text-align: center;
  margin-bottom: 32px;
}

.logo-icon {
  font-size: 48px;
  margin-bottom: 8px;
}

.logo h1 {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.logo h1 span {
  color: var(--accent);
}

.logo p {
  color: var(--text-secondary);
  font-size: 14px;
  margin-top: 4px;
}

.error-alert {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: var(--text-secondary);
}

.form-group input {
  width: 100%;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border: 2px solid transparent;
  border-radius: 12px;
  color: var(--text-primary);
  font-size: 16px;
  transition: all 0.2s;
}

.form-group input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 4px rgba(124, 58, 237, 0.2);
}

.form-group input::placeholder {
  color: rgba(255, 255, 255, 0.3);
}

.btn-login {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, var(--accent) 0%, #9333ea 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-login:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(124, 58, 237, 0.4);
}

.btn-login:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}
</style>
