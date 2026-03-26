<template>
  <nav class="navbar">
    <div class="nav-brand">
      <router-link to="/">ErrorLens</router-link>
    </div>

    <div class="nav-links">
      <router-link to="/" class="nav-link">
        Sessions
      </router-link>
      <router-link to="/qa" class="nav-link">
        QA
      </router-link>
      <router-link to="/issues" class="nav-link">
        Issues
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
      <!-- Notifications bell -->
      <div class="notif-wrapper" ref="notifWrapper">
        <button class="btn-bell" @click="toggleDropdown" :title="`${notifStore.unreadCount} непрочитанных`">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
          </svg>
          <span v-if="notifStore.unreadCount > 0" class="badge">{{ notifStore.unreadCount > 99 ? '99+' : notifStore.unreadCount }}</span>
        </button>

        <div v-if="showDropdown" class="notif-dropdown">
          <div class="notif-header">
            <span>Уведомления</span>
            <button v-if="notifStore.unreadCount > 0" class="btn-mark-all" @click="markAllRead">Прочитать все</button>
          </div>

          <div v-if="notifStore.loading" class="notif-loading">Загрузка...</div>
          <div v-else-if="notifStore.notifications.length === 0" class="notif-empty">Нет уведомлений</div>
          <div v-else class="notif-list">
            <div
              v-for="n in notifStore.notifications.slice(0, 10)"
              :key="n.id"
              class="notif-item"
              :class="{ unread: !n.is_read }"
              @click="onNotifClick(n)"
            >
              <div class="notif-icon">{{ getIcon(n.type) }}</div>
              <div class="notif-content">
                <div class="notif-title">{{ n.title }}</div>
                <div v-if="n.body" class="notif-body">{{ n.body }}</div>
                <div class="notif-time">{{ timeAgo(n.created_at) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <span class="username">{{ auth.user?.username }}</span>
      <button @click="logout" class="btn-logout">Logout</button>
    </div>
  </nav>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'

const router = useRouter()
const auth = useAuthStore()
const notifStore = useNotificationsStore()

const showDropdown = ref(false)
const notifWrapper = ref(null)
let pollInterval = null

function toggleDropdown() {
  showDropdown.value = !showDropdown.value
  if (showDropdown.value) {
    notifStore.fetchNotifications()
  }
}

function onClickOutside(e) {
  if (notifWrapper.value && !notifWrapper.value.contains(e.target)) {
    showDropdown.value = false
  }
}

function onNotifClick(n) {
  notifStore.markRead(n.id)
  showDropdown.value = false

  if (n.entity_type && n.entity_id) {
    const routes = {
      task: '/tasks',
      testcase: '/qa',
      testplan_run: '/qa?tab=plans',
      session: '/',
    }
    const path = routes[n.entity_type] || '/'
    router.push(path)
  }
}

async function markAllRead() {
  await notifStore.markAllRead()
}

function getIcon(type) {
  const icons = {
    'task.assigned': 'T',
    'task.status_changed': 'T',
    'testcase.status_changed': 'C',
    'testplan_run.completed': 'R',
    'session.analyzed': 'S',
  }
  return icons[type] || 'N'
}

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'только что'
  if (mins < 60) return `${mins} мин. назад`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} ч. назад`
  const days = Math.floor(hours / 24)
  return `${days} дн. назад`
}

async function logout() {
  await auth.logout()
  router.push('/login')
}

onMounted(() => {
  notifStore.fetchUnreadCount()
  pollInterval = setInterval(() => notifStore.fetchUnreadCount(), 30000)
  document.addEventListener('click', onClickOutside)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
  document.removeEventListener('click', onClickOutside)
})
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

/* Notifications */
.notif-wrapper {
  position: relative;
}

.btn-bell {
  position: relative;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 6px;
  border-radius: 8px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
}

.btn-bell:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.badge {
  position: absolute;
  top: 0;
  right: -2px;
  background: #ef4444;
  color: white;
  font-size: 10px;
  font-weight: 700;
  min-width: 16px;
  height: 16px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
}

.notif-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  width: 360px;
  max-height: 480px;
  background: var(--bg-card);
  border: 1px solid var(--bg-secondary);
  border-radius: 12px;
  box-shadow: var(--shadow-dropdown);
  z-index: 100;
  overflow: hidden;
}

.notif-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--bg-secondary);
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
}

.btn-mark-all {
  background: transparent;
  border: none;
  color: var(--accent);
  cursor: pointer;
  font-size: 12px;
}

.btn-mark-all:hover {
  text-decoration: underline;
}

.notif-list {
  overflow-y: auto;
  max-height: 400px;
}

.notif-item {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.15s;
  border-bottom: 1px solid var(--bg-secondary);
}

.notif-item:hover {
  background: var(--bg-secondary);
}

.notif-item.unread {
  background: rgba(99, 102, 241, 0.08);
}

.notif-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: var(--accent);
  flex-shrink: 0;
}

.notif-content {
  flex: 1;
  min-width: 0;
}

.notif-title {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.4;
}

.notif-body {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.notif-time {
  font-size: 11px;
  color: var(--text-tertiary, var(--text-secondary));
  margin-top: 4px;
}

.notif-loading,
.notif-empty {
  padding: 24px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
}
</style>
