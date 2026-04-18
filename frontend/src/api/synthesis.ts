import { api } from './client'

export type SynthesisStatus = 'queued' | 'running' | 'succeeded' | 'failed'
export type SynthesisModel = 'chatterbox' | 'omnivoice' | 'qwen3tts' | 'elevenlabs'

export interface SynthesisRow {
  id: string
  user_id: string
  profile_id: string
  model: SynthesisModel
  text: string
  status: SynthesisStatus
  duration_s: number | null
  rtf: number | null
  watermark_scheme: string | null
  watermark_verified: boolean | null
  aasist_score: number | null
  error: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export interface ModelInfo {
  name: string
  license: string
  available: boolean
  notes: string | null
}

export interface Profile {
  id: string
  user_id: string
  name: string
  reference_ids: string[]
  status: 'pending' | 'ready' | 'failed'
  created_at: string
}

export const synthesisApi = {
  models: () => api.get<ModelInfo[]>('/synthesis/models'),
  list:   () => api.get<{ items: SynthesisRow[]; total: number }>('/synthesis'),
  get:    (id: string) => api.get<SynthesisRow>(`/synthesis/${id}`),
  create: (body: { profile_id: string; model: SynthesisModel; text: string; options?: Record<string, unknown> }) =>
    api.post<SynthesisRow>('/synthesis', body),
  audioUrl: (id: string) => `/api/synthesis/${id}/audio`,
}

export const profilesApi = {
  list: () => api.get<{ items: Profile[]; total: number }>('/profiles'),
  create: (name: string, reference_ids: string[]) =>
    api.post<Profile>('/profiles', { name, reference_ids }),
  update: (id: string, patch: { name?: string; reference_ids?: string[] }) =>
    patchJson<Profile>(`/profiles/${id}`, patch),
  remove: (id: string) => api.del<void>(`/profiles/${id}`),
}

// Generic client only speaks GET/POST/PUT/DELETE/upload. PATCH is hand-rolled
// here — mirrors the same bearer-auth + JSON error-shape the rest uses.
async function patchJson<T>(path: string, body: unknown): Promise<T> {
  const prefix = import.meta.env.VITE_API_PREFIX ?? '/api'
  const { useAuthStore } = await import('@/stores/auth')
  const auth = useAuthStore()
  const res = await fetch(`${prefix}${path}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...(auth.token ? { Authorization: `Bearer ${auth.token}` } : {}),
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: `PATCH ${res.status}` }))
    throw new Error(typeof detail.detail === 'string' ? detail.detail : `PATCH ${res.status}`)
  }
  return (await res.json()) as T
}
