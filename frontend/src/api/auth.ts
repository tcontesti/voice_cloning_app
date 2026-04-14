import { api } from './client'

export interface TokenOut {
  access_token: string
  token_type: 'bearer'
  expires_in: number
}

export interface CurrentUser {
  id: string
  email: string
  role: 'paciente' | 'clinico' | 'admin' | 'auditor'
  full_name: string | null
}

export const authApi = {
  login: (email: string, password: string) =>
    api.post<TokenOut>('/auth/login', { email, password }),
  me: () => api.get<CurrentUser>('/auth/me'),
}
