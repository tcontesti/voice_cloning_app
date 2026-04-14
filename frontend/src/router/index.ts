import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { Role } from '@/api/admin'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    roles?: Role[]
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'home', component: () => import('@/views/HomeView.vue') },
      { path: 'consent', name: 'consent', component: () => import('@/views/ConsentView.vue') },
      { path: 'record', name: 'record', component: () => import('@/views/RecordView.vue') },
      { path: 'synthesize', name: 'synthesize', component: () => import('@/views/SynthesizeView.vue') },
      {
        path: 'admin/users',
        name: 'admin-users',
        component: () => import('@/views/AdminUsersView.vue'),
        meta: { roles: ['admin'] },
      },
      {
        path: 'audit',
        name: 'audit',
        component: () => import('@/views/AuditLogView.vue'),
        meta: { roles: ['admin', 'auditor'] },
      },
    ],
  },
  {
    path: '/login',
    component: () => import('@/layouts/PublicLayout.vue'),
    children: [
      { path: '', name: 'login', component: () => import('@/views/LoginView.vue') },
    ],
  },
  // Design system playground — dev-only. Excluded from the production bundle
  // and bypasses auth so we can iterate the look in isolation.
  ...(import.meta.env.DEV
    ? ([
        {
          path: '/_ui',
          name: 'ui-demo',
          component: () => import('@/views/UiDemoView.vue'),
        },
      ] as RouteRecordRaw[])
    : []),
  { path: '/:catchAll(.*)', redirect: { name: 'home' } },
]

export const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  if (to.name === 'ui-demo') return
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.isAuthenticated) return { name: 'home' }
  if (to.meta.roles && auth.role && !to.meta.roles.includes(auth.role as Role)) {
    return { name: 'home' }
  }
})
