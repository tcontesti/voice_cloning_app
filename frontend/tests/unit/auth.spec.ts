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
    await auth.bootstrapFromStorage()
    expect(auth.token).toBe('persisted-tok')
    expect(auth.user?.role).toBe('paciente')
    expect(auth.isAuthenticated).toBe(true)
  })

  it('isAuthenticated is true with only a token (user loads async)', () => {
    localStorage.setItem('vcapp.token', 'persisted-tok')
    const auth = useAuthStore()
    // Kick off bootstrap but don't await: guards run before /me resolves.
    void auth.bootstrapFromStorage()
    expect(auth.token).toBe('persisted-tok')
    expect(auth.isAuthenticated).toBe(true)
  })

  it('login → logout → bootstrap roundtrip persists and clears cleanly', async () => {
    const a1 = useAuthStore()
    await a1.login('paciente@example.com', 'pw')
    expect(localStorage.getItem('vcapp.token')).toBe('tok-abc')

    // Simulate a page reload: fresh pinia, same localStorage.
    setActivePinia(createPinia())
    const a2 = useAuthStore()
    expect(a2.token).toBeNull()
    await a2.bootstrapFromStorage()
    expect(a2.token).toBe('tok-abc')
    expect(a2.isAuthenticated).toBe(true)

    a2.logout()
    expect(localStorage.getItem('vcapp.token')).toBeNull()

    setActivePinia(createPinia())
    const a3 = useAuthStore()
    await a3.bootstrapFromStorage()
    expect(a3.token).toBeNull()
    expect(a3.isAuthenticated).toBe(false)
  })
})
