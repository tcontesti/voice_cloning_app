import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'home', component: () => import('@/views/HomeView.vue') },
      { path: 'consent', name: 'consent', component: () => import('@/views/ConsentView.vue') },
      { path: 'record', name: 'record', component: () => import('@/views/RecordView.vue') },
    ],
  },
  {
    path: '/login',
    component: () => import('@/layouts/PublicLayout.vue'),
    children: [
      { path: '', name: 'login', component: () => import('@/views/LoginView.vue') },
    ],
  },
  { path: '/:catchAll(.*)', redirect: { name: 'home' } },
]

export const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.isAuthenticated) return { name: 'home' }
})
