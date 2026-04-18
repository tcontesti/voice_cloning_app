/**
 * WebSocket subscriber for /ws/jobs/{id} progress events.
 *
 * Auth travels in the `Sec-WebSocket-Protocol` handshake as
 * `["bearer", <jwt>]`. Using the subprotocol keeps the token out of
 * nginx access logs, referer headers, and window.history — the query
 * param variant (still accepted by the server) ended up in all three.
 */
import { ref, onBeforeUnmount, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'

export interface JobEvent {
  stage: string
  pct: number
  message?: string
  payload?: Record<string, unknown>
  ts?: number
}

const WS_PREFIX = (import.meta.env.VITE_API_PREFIX ?? '/api').replace(/\/$/, '')

export function useJobProgress(jobId: () => string | null) {
  const auth = useAuthStore()
  const events = ref<JobEvent[]>([])
  const last = ref<JobEvent | null>(null)
  const connected = ref(false)
  const error = ref<string | null>(null)
  let ws: WebSocket | null = null

  function close() {
    try { ws?.close() } catch {}
    ws = null
    connected.value = false
  }

  function open(id: string) {
    close()
    error.value = null
    // Reset per-job state so the next consumer doesn't see stale stage/events
    // from a prior job (that's how SynthesizeView kept loading the previous
    // audio and 404'ing on model switches).
    events.value = []
    last.value = null
    if (!auth.token) { error.value = 'no token'; return }

    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${proto}//${location.host}${WS_PREFIX}/ws/jobs/${id}`
    // WebSocket subprotocols carry the token in the handshake (Sec-WebSocket-Protocol
    // request header). The server reads protocols[0] == "bearer" + protocols[1] == jwt
    // and echoes `bearer` back on accept. See backend/app/api/ws_jobs.py.
    ws = new WebSocket(url, ['bearer', auth.token])
    ws.onopen = () => { connected.value = true }
    ws.onerror = () => { error.value = 'websocket error' }
    ws.onclose = () => { connected.value = false }
    ws.onmessage = (ev) => {
      try {
        const e = JSON.parse(ev.data) as JobEvent
        if (e.stage === 'heartbeat') return
        events.value.push(e)
        last.value = e
      } catch { /* ignore malformed */ }
    }
  }

  watch(jobId, (id) => { id ? open(id) : close() }, { immediate: true })
  onBeforeUnmount(close)

  return { events, last, connected, error, close }
}
