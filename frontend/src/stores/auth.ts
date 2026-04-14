import { defineStore } from 'pinia'
import { authApi, type CurrentUser } from '@/api/auth'

const TOKEN_KEY = 'vcapp.token'

interface State {
  token: string | null
  user: CurrentUser | null
  loading: boolean
}

export const useAuthStore = defineStore('auth', {
  state: (): State => ({
    token: null,
    user: null,
    loading: false,
  }),
  getters: {
    isAuthenticated: (s) => Boolean(s.token && s.user),
    role: (s) => s.user?.role ?? null,
  },
  actions: {
    bootstrapFromStorage() {
      const t = localStorage.getItem(TOKEN_KEY)
      if (!t) return
      this.token = t
      void this.refreshUser()
    },
    async login(email: string, password: string) {
      this.loading = true
      try {
        const tok = await authApi.login(email, password)
        this.token = tok.access_token
        localStorage.setItem(TOKEN_KEY, tok.access_token)
        await this.refreshUser()
      } finally {
        this.loading = false
      }
    },
    async refreshUser() {
      try {
        this.user = await authApi.me()
      } catch {
        this.logout()
      }
    },
    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
    },
  },
})
