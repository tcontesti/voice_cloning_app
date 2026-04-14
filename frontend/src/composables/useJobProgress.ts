/**
 * WebSocket subscriber for /ws/jobs/{id} progress events.
 *
 * Token is appended as ?token=<jwt> because browsers can't set Authorization
 * headers on WebSocket. Same token the REST client uses.
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
    if (!auth.token) { error.value = 'no token'; return }

    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${proto}//${location.host}${WS_PREFIX}/ws/jobs/${id}?token=${encodeURIComponent(auth.token)}`
    ws = new WebSocket(url)
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
