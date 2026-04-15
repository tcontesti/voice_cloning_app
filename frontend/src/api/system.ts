import { api } from './client'

export type ServiceStatus = 'ok' | 'unreachable'
export type WorkerStatus = 'available' | 'offline'
export type WorkerName = 'chatterbox' | 'omnivoice' | 'qwen3tts' | 'elevenlabs'

export interface SystemHealth {
  backend: 'ok'
  postgres: ServiceStatus
  redis: ServiceStatus
  rabbitmq: ServiceStatus
  minio: ServiceStatus
  workers: Record<WorkerName, WorkerStatus>
  spark_reachable: boolean
}

export const systemApi = {
  health: () => api.get<SystemHealth>('/system/health'),
}
