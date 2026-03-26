<template>
  <div class="app">
    <Navbar v-if="isAuthenticated && route.path !== '/login'" />
    <main :class="['main-content', { 'main-content--fullscreen': isFullscreen }]">
      <router-view />
    </main>
    <Toasts />
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { useLocaleStore } from '@/stores/locale'
import Navbar from '@/components/common/Navbar.vue'
import Toasts from '@/components/common/Toasts.vue'

const route = useRoute()
const auth = useAuthStore()
const themeStore = useThemeStore()
const localeStore = useLocaleStore()

const isAuthenticated = computed(() => auth.isAuthenticated)
const isFullscreen = computed(() =>
  ['/articles', '/qa', '/issues'].some(p => route.path.startsWith(p))
)

onMounted(() => {
  themeStore.init()
  localeStore.init()
})
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

.main-content--fullscreen {
  padding: 0;
  max-width: 100%;
}
</style>
