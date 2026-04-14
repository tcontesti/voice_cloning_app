import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/api/auth', () => ({
  authApi: {
    login: vi.fn(async () => ({
      access_token: 'tok-abc',
      token_type: 'bearer',
      expires_in: 28800,
    })),
    me: vi.fn(async () => ({
      id: 'u-1',
      email: 'paciente@example.com',
      role: 'paciente',
      full_name: 'P',
    })),
  },
}))

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  it('login stores token + fetches user + flips isAuthenticated', async () => {
    const auth = useAuthStore()
    expect(auth.isAuthenticated).toBe(false)

    await auth.login('paciente@example.com', 'pw')

    expect(auth.token).toBe('tok-abc')
    expect(auth.user?.email).toBe('paciente@example.com')
    expect(auth.isAuthenticated).toBe(true)
    expect(localStorage.getItem('vcapp.token')).toBe('tok-abc')
  })

  it('logout clears token + storage', async () => {
    const auth = useAuthStore()
    await auth.login('p@example.com', 'pw')
    auth.logout()
    expect(auth.token).toBeNull()
    expect(auth.user).toBeNull()
    expect(localStorage.getItem('vcapp.token')).toBeNull()
  })

  it('bootstrapFromStorage rehydrates token + refreshes user', async () => {
    localStorage.setItem('vcapp.token', 'persisted-tok')
    const auth = useAuthStore()
    auth.bootstrapFromStorage()
    expect(auth.token).toBe('persisted-tok')
    // refreshUser is async; await microtasks
    await Promise.resolve()
    await Promise.resolve()
    expect(auth.user?.role).toBe('paciente')
  })
})
