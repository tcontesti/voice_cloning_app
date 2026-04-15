<!--
  SystemStatusBadge — topbar chip that rolls up /system/health into a
  single LED + label, with a hover card for per-service detail. Uses the
  shared composable so multiple mounts don't fan out polling.
-->
<script setup lang="ts">
import { computed } from 'vue'
import LED from '@/ui/primitives/LED.vue'
import { useSystemHealth } from '@/composables/useSystemHealth'
import type { ServiceStatus, WorkerName, WorkerStatus } from '@/api/system'

const { data, degraded } = useSystemHealth()

const tint = computed<'green' | 'amber' | 'red'>(() => {
  if (degraded.value === 'backend-down') return 'red'
  if (degraded.value === 'spark-down') return 'amber'
  return 'green'
})

const label = computed(() => {
  if (degraded.value === 'backend-down') return 'SIN SERVICIO'
  if (degraded.value === 'spark-down') return 'SPARK OFFLINE'
  return 'SISTEMA OK'
})

function svcLabel(s: ServiceStatus | undefined): string {
  if (s === 'ok') return 'OK'
  if (s === 'unreachable') return 'OFFLINE'
  return '—'
}
function wkLabel(s: WorkerStatus | undefined): string {
  return s === 'available' ? 'ONLINE' : 'OFFLINE'
}

const workerEntries = computed<Array<[WorkerName, WorkerStatus]>>(() => {
  const w = data.value?.workers
  if (!w) return []
  return (Object.entries(w) as Array<[WorkerName, WorkerStatus]>)
})
</script>

<template>
  <div class="sysb" :class="`sysb--${tint}`" tabindex="0"
       :aria-label="`Estado sistema: ${label.toLowerCase()}`">
    <LED :color="tint" on :pulse="tint !== 'green'" size="xs" />
    <span class="sysb__label">{{ label }}</span>

    <div class="sysb__pop studio-card" role="tooltip">
      <div class="studio-label sysb__pop-head">ESTADO DEL SISTEMA</div>

      <dl class="sysb__grid">
        <dt class="studio-label">BACKEND</dt>
        <dd :class="data ? 'sysb__ok' : 'sysb__err'">
          {{ data ? 'OK' : 'OFFLINE' }}
        </dd>
        <dt class="studio-label">POSTGRES</dt>
        <dd :class="data?.postgres === 'ok' ? 'sysb__ok' : 'sysb__err'">
          {{ svcLabel(data?.postgres) }}
        </dd>
        <dt class="studio-label">REDIS</dt>
        <dd :class="data?.redis === 'ok' ? 'sysb__ok' : 'sysb__err'">
          {{ svcLabel(data?.redis) }}
        </dd>
        <dt class="studio-label">RABBITMQ</dt>
        <dd :class="data?.rabbitmq === 'ok' ? 'sysb__ok' : 'sysb__err'">
          {{ svcLabel(data?.rabbitmq) }}
        </dd>
        <dt class="studio-label">MINIO</dt>
        <dd :class="data?.minio === 'ok' ? 'sysb__ok' : 'sysb__err'">
          {{ svcLabel(data?.minio) }}
        </dd>
      </dl>

      <div class="studio-label sysb__pop-sub">WORKERS GPU</div>
      <dl class="sysb__grid">
        <template v-for="[name, status] in workerEntries" :key="name">
          <dt class="studio-label sysb__worker-name">{{ name.toUpperCase() }}</dt>
          <dd :class="status === 'available' ? 'sysb__ok' : 'sysb__off'">
            {{ wkLabel(status) }}
          </dd>
        </template>
      </dl>

      <p v-if="degraded === 'spark-down'" class="sysb__hint">
        Puedes grabar referencias — no requiere GPU. La síntesis queda en cola hasta
        que la Spark vuelva.
      </p>
      <p v-else-if="degraded === 'backend-down'" class="sysb__hint sysb__hint--err">
        El servidor no responde. Revisa tu conexión o contacta con soporte.
      </p>
    </div>
  </div>
</template>

<style scoped>
.sysb {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--bg-2);
  border: 1px solid var(--line);
  cursor: default;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.1em;
  color: var(--fg-1);
  transition: border-color var(--dur-base) var(--ease-studio);
}
.sysb:hover, .sysb:focus-visible { border-color: var(--line-2); outline: none; }
.sysb--amber { color: var(--signal-amber); border-color: color-mix(in srgb, var(--signal-amber) 40%, var(--line)); }
.sysb--red   { color: var(--signal-red);   border-color: color-mix(in srgb, var(--signal-red) 50%, var(--line)); }

.sysb__pop {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 280px;
  padding: 14px;
  opacity: 0;
  pointer-events: none;
  transform: translateY(-4px);
  transition: opacity var(--dur-base) var(--ease-studio),
              transform var(--dur-base) var(--ease-studio);
  z-index: 40;
}
.sysb:hover .sysb__pop, .sysb:focus-visible .sysb__pop,
.sysb__pop:hover {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}

.sysb__pop-head, .sysb__pop-sub { color: var(--fg-2); }
.sysb__pop-sub { margin-top: 12px; }

.sysb__grid {
  margin: 8px 0 0;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 4px 12px;
  font-size: 11px;
  letter-spacing: 0.06em;
}
.sysb__grid dt { color: var(--fg-2); }
.sysb__grid dd { margin: 0; font-family: var(--font-mono); }
.sysb__worker-name { text-transform: none; }
.sysb__ok  { color: var(--signal-green); }
.sysb__err { color: var(--signal-red); }
.sysb__off { color: var(--signal-amber); }

.sysb__hint {
  margin: 10px 0 0;
  padding: 8px 10px;
  background: color-mix(in srgb, var(--signal-amber) 10%, var(--bg-1));
  border: 1px solid color-mix(in srgb, var(--signal-amber) 40%, transparent);
  border-radius: var(--radius-2);
  color: var(--fg-1);
  font-family: var(--font-sans);
  font-size: 12px;
  line-height: 1.45;
  letter-spacing: 0;
}
.sysb__hint--err {
  background: color-mix(in srgb, var(--signal-red) 10%, var(--bg-1));
  border-color: var(--signal-red);
  color: var(--signal-red);
}

.sysb__label { white-space: nowrap; }
</style>
