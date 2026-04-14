import { api } from './client'

export interface Recording {
  id: string
  user_id: string
  duration_s: number
  sample_rate: number
  channels: number
  snr_db: number | null
  lufs: number | null
  speech_ratio: number | null
  sha256: string
  created_at: string
  deleted_at: string | null
}

export const recordingsApi = {
  list: () => api.get<{ items: Recording[]; total: number }>('/recordings'),
  upload: (blob: Blob, filename = 'reference.wav') => {
    const fd = new FormData()
    fd.append('file', blob, filename)
    return api.upload<Recording>('/recordings', fd)
  },
  remove: (id: string) => api.del<void>(`/recordings/${id}`),
}
