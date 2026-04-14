/**
 * Thin fetch wrapper. Auth token comes from the auth store (read fresh
 * each call so we never send a stale one).
 *
 * In dev the proxy forwards `/api/*` to the backend (vite.config.ts).
 * Override with VITE_API_PREFIX in .env.local.
 */
import { useAuthStore } from '@/stores/auth'

const API_PREFIX = import.meta.env.VITE_API_PREFIX ?? '/api'

export class ApiError extends Error {
  status: number
  detail: unknown
  constructor(status: number, message: string, detail: unknown) {
    super(message)
    this.status = status
    this.detail = detail
  }
}

async function request<T>(method: string, path: string, body?: unknown, isForm = false): Promise<T> {
  const auth = useAuthStore()
  const headers: Record<string, string> = {}
  if (!isForm && body !== undefined) headers['Content-Type'] = 'application/json'
  if (auth.token) headers['Authorization'] = `Bearer ${auth.token}`

  const res = await fetch(`${API_PREFIX}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
  })

  if (res.status === 204) return undefined as T

  let payload: unknown = null
  const ctype = res.headers.get('content-type') ?? ''
  if (ctype.includes('application/json')) payload = await res.json().catch(() => null)
  else payload = await res.text().catch(() => '')

  if (!res.ok) {
    const detail =
      typeof payload === 'object' && payload !== null && 'detail' in payload
        ? (payload as { detail: unknown }).detail
        : payload
    if (res.status === 401) auth.logout()
    throw new ApiError(res.status, `${method} ${path} → ${res.status}`, detail)
  }
  return payload as T
}

export const api = {
  get:  <T,>(p: string) => request<T>('GET', p),
  post: <T,>(p: string, body?: unknown) => request<T>('POST', p, body),
  put:  <T,>(p: string, body?: unknown) => request<T>('PUT', p, body),
  del:  <T,>(p: string) => request<T>('DELETE', p),
  upload: <T,>(p: string, form: FormData) => request<T>('POST', p, form, true),
}
