/**
 * Polls /system/health every `intervalMs` (default 10s). Auto-pauses
 * when the document is hidden so we don't burn battery in background tabs.
 *
 * Exposes a `degraded` rollup the UI uses to switch the SystemStatusBadge
 * tint and to disable model-specific actions.
 */
import { computed, onBeforeUnmount, ref, shallowRef } from 'vue'
import { systemApi, type SystemHealth, type WorkerName } from '@/api/system'

export type DegradedLevel = 'ok' | 'spark-down' | 'backend-down' | 'loading'

export interface UseSystemHealthOptions {
  intervalMs?: number
  immediate?: boolean
}

export function useSystemHealth(opts: UseSystemHealthOptions = {}) {
  const intervalMs = opts.intervalMs ?? 10_000
  const immediate = opts.immediate ?? true

  const data = shallowRef<SystemHealth | null>(null)
  const error = ref<string | null>(null)
  const lastFetchAt = ref<number | null>(null)

  let timer: ReturnType<typeof setTimeout> | null = null
  let stopped = false

  async function fetchOnce(): Promise<void> {
    try {
      const h = await systemApi.health()
      data.value = h
      error.value = null
      lastFetchAt.value = Date.now()
    } catch (e) {
      error.value = (e as Error).message
      // Keep last-known data, but mark backend-down via the computed below.
      lastFetchAt.value = Date.now()
    }
  }

  function schedule() {
    if (stopped) return
    timer = setTimeout(async () => {
      if (typeof document === 'undefined' || !document.hidden) {
        await fetchOnce()
      }
      schedule()
    }, intervalMs)
  }

  function start() {
    stopped = false
    if (immediate) void fetchOnce()
    schedule()
  }

  function stop() {
    stopped = true
    if (timer) { clearTimeout(timer); timer = null }
  }

  start()
  onBeforeUnmount(stop)

  /** Backend down ⇒ current fetch failed; spark down ⇒ rabbit/minio unreachable. */
  const degraded = computed<DegradedLevel>(() => {
    if (!data.value && !error.value) return 'loading'
    if (error.value) return 'backend-down'
    if (data.value && !data.value.spark_reachable) return 'spark-down'
    return 'ok'
  })

  function workerAvailable(name: WorkerName): boolean {
    return data.value?.workers[name] === 'available'
  }

  return {
    data,
    error,
    lastFetchAt,
    degraded,
    workerAvailable,
    refresh: fetchOnce,
    stop,
  }
}
