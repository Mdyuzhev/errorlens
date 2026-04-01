import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/sessions',
    name: 'sessions',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/sessions/:id',
    name: 'session',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/qa',
    name: 'qa',
    component: () => import('@/views/QAView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/import',
    name: 'import',
    component: () => import('@/views/ImportView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/qa/:tab',
    name: 'qa-tab',
    component: () => import('@/views/QAView.vue'),
    meta: { requiresAuth: true },
    props: true
  },
  {
    path: '/testcases',
    redirect: '/qa'
  },
  {
    path: '/testcases/:id',
    redirect: to => `/qa?open=${to.params.id}`
  },
  {
    path: '/tasks',
    name: 'tasks',
    component: () => import('@/views/TasksView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/tasks/:id',
    name: 'task',
    component: () => import('@/views/TasksView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/issues',
    name: 'issues',
    component: () => import('@/views/IssuesView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/issues/:id',
    name: 'issue',
    component: () => import('@/views/IssuesView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/articles',
    name: 'articles',
    component: () => import('@/views/ArticlesView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/articles/:slug',
    name: 'article',
    component: () => import('@/views/ArticlesView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/test-plans',
    redirect: '/qa?tab=plans'
  },
  {
    path: '/test-plans/runs/:runId',
    name: 'test-plan-run',
    component: () => import('@/views/TestPlanRunView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/results',
    name: 'results',
    component: () => import('@/views/ResultsView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/generator/:sessionId?',
    name: 'generator',
    component: () => import('@/views/GeneratorView.vue'),
    meta: { requiresAuth: true },
    props: true
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// Auth guard
router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()

  // Check auth on first load
  if (!auth.isAuthenticated && localStorage.getItem('access_token')) {
    await auth.checkAuth()
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && auth.isAuthenticated) {
    next('/')
  } else {
    next()
  }
})

export default router
