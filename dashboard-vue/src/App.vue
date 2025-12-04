<template>
  <div class="app">
    <Navbar v-if="isAuthenticated && route.path !== '/login'" />
    <main class="main-content">
      <router-view />
    </main>
    <Toasts />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Navbar from '@/components/common/Navbar.vue'
import Toasts from '@/components/common/Toasts.vue'

const route = useRoute()
const auth = useAuthStore()

const isAuthenticated = computed(() => auth.isAuthenticated)
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
</style>
