import { api } from './client'

export type Role = 'paciente' | 'clinico' | 'admin' | 'auditor'

export interface AdminUser {
  id: string
  email: string
  role: Role
  full_name: string | null
  active: boolean
  created_at: string
}

export interface SystemStats {
  users_total: number
  users_active: number
  recordings_total: number
  recordings_active: number
  profiles_total: number
  syntheses_total: number
  syntheses_by_status: Record<string, number>
}

export const adminApi = {
  users: () => api.get<{ items: AdminUser[]; total: number }>('/admin/users'),
  setActive: (id: string, active: boolean) =>
    api.put<unknown>(`/admin/users/${id}/active`, { active }),  // method is PATCH — see below
  stats: () => api.get<SystemStats>('/admin/stats'),
}

// PATCH helper — the generic client only has get/post/put/del/upload, so we
// expose PATCH here rather than bloating client.ts.
export async function setUserActive(id: string, active: boolean): Promise<AdminUser> {
  const prefix = import.meta.env.VITE_API_PREFIX ?? '/api'
  const { useAuthStore } = await import('@/stores/auth')
  const auth = useAuthStore()
  const res = await fetch(`${prefix}/admin/users/${id}/active`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...(auth.token ? { Authorization: `Bearer ${auth.token}` } : {}),
    },
    body: JSON.stringify({ active }),
  })
  if (!res.ok) throw new Error(`PATCH ${res.status}`)
  return (await res.json()) as AdminUser
}
