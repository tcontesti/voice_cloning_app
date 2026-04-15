/**
 * useSystemHealth — verifies polling, degraded rollup and worker helper.
 * We mock the api module directly with vi.fn() instead of pulling MSW.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent, h, nextTick } from 'vue'
import { mount } from '@vue/test-utils'

const healthMock = vi.fn()

vi.mock('@/api/system', () => ({
  systemApi: { health: () => healthMock() },
}))

import { useSystemHealth } from '@/composables/useSystemHealth'
import type { SystemHealth } from '@/api/system'

function fakeHealth(overrides: Partial<SystemHealth> = {}): SystemHealth {
  return {
    backend: 'ok',
    postgres: 'ok',
    redis: 'ok',
    rabbitmq: 'ok',
    minio: 'ok',
    workers: {
      chatterbox: 'available',
      omnivoice: 'available',
      qwen3tts: 'available',
      elevenlabs: 'available',
    },
    spark_reachable: true,
    ...overrides,
  }
}

interface Probe {
  data: { value: SystemHealth | null }
  degraded: { value: 'ok' | 'spark-down' | 'backend-down' }
  workerAvailable: (n: 'chatterbox' | 'omnivoice' | 'qwen3tts' | 'elevenlabs') => boolean
  refresh: () => Promise<void>
}

/** Mount a host so the composable runs inside a real component lifecycle. */
function host(): Probe {
  let probe!: Probe
  const Comp = defineComponent({
    setup() {
      const r = useSystemHealth({ intervalMs: 50 })
      probe = r as unknown as Probe
      return () => h('div')
    },
  })
  mount(Comp)
  return probe
}

describe('useSystemHealth', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    healthMock.mockReset()
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('rolls up to "ok" when everything is healthy', async () => {
    healthMock.mockResolvedValue(fakeHealth())
    const p = host()
    await vi.runOnlyPendingTimersAsync()
    await Promise.resolve()
    expect(p.data.value?.spark_reachable).toBe(true)
    expect(p.degraded.value).toBe('ok')
    expect(p.workerAvailable('chatterbox')).toBe(true)
  })

  it('rolls up to "spark-down" when transports are unreachable', async () => {
    healthMock.mockResolvedValue(
      fakeHealth({
        rabbitmq: 'unreachable',
        spark_reachable: false,
        workers: {
          chatterbox: 'offline',
          omnivoice: 'offline',
          qwen3tts: 'offline',
          elevenlabs: 'offline',
        },
      }),
    )
    const p = host()
    await vi.runOnlyPendingTimersAsync()
    await Promise.resolve()
    expect(p.degraded.value).toBe('spark-down')
    expect(p.workerAvailable('chatterbox')).toBe(false)
  })

  it('rolls up to "backend-down" when /health throws and there is no prior data', async () => {
    healthMock.mockRejectedValue(new Error('network'))
    const p = host()
    await vi.runOnlyPendingTimersAsync()
    await Promise.resolve()
    expect(p.data.value).toBeNull()
    expect(p.degraded.value).toBe('backend-down')
  })

  it('keeps polling at the configured interval', async () => {
    healthMock.mockResolvedValue(fakeHealth())
    host()
    // Initial immediate fetch — let microtasks resolve without firing timers.
    await Promise.resolve()
    await Promise.resolve()
    expect(healthMock).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(60)
    expect(healthMock).toHaveBeenCalledTimes(2)

    await vi.advanceTimersByTimeAsync(60)
    expect(healthMock).toHaveBeenCalledTimes(3)
  })

  it('refresh() forces an out-of-band fetch', async () => {
    healthMock.mockResolvedValue(fakeHealth())
    const p = host()
    await Promise.resolve()
    await Promise.resolve()
    const before = healthMock.mock.calls.length
    await p.refresh()
    expect(healthMock.mock.calls.length).toBe(before + 1)
    await nextTick()
  })
})
