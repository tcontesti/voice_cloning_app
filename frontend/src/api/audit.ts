import { api } from './client'

export interface AuditEntry {
  id: number
  actor_id: string | null
  action: string
  resource_type: string
  resource_id: string | null
  payload: Record<string, unknown>
  prev_hash: string
  hash: string
  created_at: string
}

export interface AuditPage {
  items: AuditEntry[]
  total: number
  limit: number
  offset: number
}

export interface ChainStatus {
  ok: boolean
  broken_at: number | null
  total_entries: number
}

export interface AuditStats {
  total: number
  by_action: Record<string, number>
  by_resource: Record<string, number>
  first_ts: string | null
  last_ts: string | null
}

export interface AuditFilters {
  limit?: number
  offset?: number
  action?: string
  action_prefix?: string
  actor_id?: string
  resource_type?: string
  since?: string
  until?: string
}

function qs(params: AuditFilters): string {
  const sp = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== '' && v !== null) sp.append(k, String(v))
  })
  const s = sp.toString()
  return s ? `?${s}` : ''
}

export const auditApi = {
  logs:   (f: AuditFilters = {}) => api.get<AuditPage>(`/audit/logs${qs(f)}`),
  verify: () => api.get<ChainStatus>('/audit/verify'),
  stats:  () => api.get<AuditStats>('/audit/stats'),
}
