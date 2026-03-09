<template>
  <nav class="navbar">
    <div class="nav-brand">
      <router-link to="/">ErrorLens</router-link>
    </div>

    <div class="nav-links">
      <router-link to="/" class="nav-link">
        Sessions
      </router-link>
      <router-link to="/testcases" class="nav-link">
        Test Cases
      </router-link>
      <router-link to="/test-plans" class="nav-link">
        Test Plans
      </router-link>
      <router-link to="/tasks" class="nav-link">
        Tasks
      </router-link>
      <router-link to="/articles" class="nav-link">
        Articles
      </router-link>
      <router-link to="/results" class="nav-link">
        Results
      </router-link>
      <router-link to="/generator" class="nav-link nav-link-accent">
        Generator
      </router-link>
      <router-link to="/settings" class="nav-link">
        Settings
      </router-link>
    </div>

    <div class="nav-user">
      <span class="username">{{ auth.user?.username }}</span>
      <button @click="logout" class="btn-logout">Logout</button>
    </div>
  </nav>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

async function logout() {
  await auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--bg-secondary);
}

.nav-brand a {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  text-decoration: none;
}

.nav-links {
  display: flex;
  gap: 8px;
}

.nav-link {
  padding: 8px 16px;
  border-radius: 8px;
  color: var(--text-secondary);
  text-decoration: none;
  transition: all 0.2s;
  font-size: 14px;
}

.nav-link:hover,
.nav-link.router-link-active {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.nav-user {
  display: flex;
  align-items: center;
  gap: 12px;
}

.username {
  color: var(--text-secondary);
  font-size: 14px;
}

.btn-logout {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid var(--accent);
  color: var(--accent);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}

.btn-logout:hover {
  background: var(--accent);
  color: white;
}

.nav-link-accent {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white !important;
}

.nav-link-accent:hover {
  background: linear-gradient(135deg, #7b8ff0, #8b5db8);
}
</style>
