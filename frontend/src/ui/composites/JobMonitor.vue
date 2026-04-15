<!--
  JobMonitor — hardware-style status display for a synthesis job.
  LCD panel (SegmentedDisplay) with the current stage + pixelated
  progress bar driven by `pct` + running timer + tiny latency sparkline.
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import SegmentedDisplay from '@/ui/primitives/SegmentedDisplay.vue'
import LED from '@/ui/primitives/LED.vue'
import { formatTimecode } from '@/composables/useTransport'

const props = withDefaults(
  defineProps<{
    stage: string          // e.g. 'loading_model', 'synthesizing'
    message?: string       // user-friendly message
    pct: number            // 0-100
    running?: boolean      // whether elapsed time should tick
    finished?: boolean
    failed?: boolean
    latencyMs?: number     // optional, fed into sparkline
  }>(),
  { pct: 0 },
)

const startedAt = ref<number | null>(null)
const elapsedS = ref(0)
const lastProgressAt = ref<number | null>(null)
const sinceProgressS = ref(0)
let tick = 0

const STALL_THRESHOLD_S = 30

function start() {
  startedAt.value = performance.now()
  lastProgressAt.value = performance.now()
  tick = window.setInterval(() => {
    if (startedAt.value) elapsedS.value = (performance.now() - startedAt.value) / 1000
    if (lastProgressAt.value)
      sinceProgressS.value = (performance.now() - lastProgressAt.value) / 1000
  }, 250)
}
function stop() {
  if (tick) { window.clearInterval(tick); tick = 0 }
}

// Reset the stall clock every time pct or stage actually advances.
watch(() => [props.pct, props.stage], (next, prev) => {
  if (!prev || next[0] !== prev[0] || next[1] !== prev[1]) {
    lastProgressAt.value = performance.now()
    sinceProgressS.value = 0
  }
})

// A running job that hasn't advanced for STALL_THRESHOLD_S is almost always
// the Spark tunnel dropping mid-stage. The RabbitMQ message survives; the
// worker will pick it up when it reconnects.
const stalled = computed(() =>
  !!props.running && !props.finished && !props.failed && sinceProgressS.value >= STALL_THRESHOLD_S,
)

watch(() => props.running, (r) => {
  if (r) start()
  else stop()
}, { immediate: true })

onMounted(() => { if (props.running) start() })
onBeforeUnmount(stop)

// Pixelated progress: 40 cells filled according to pct.
const totalCells = 40
const filled = computed(() => Math.round((Math.max(0, Math.min(100, props.pct)) / 100) * totalCells))

// Latency sparkline: keep last 48 samples.
const samples = ref<number[]>([])
watch(() => props.latencyMs, (v) => {
  if (typeof v !== 'number') return
  samples.value.push(v)
  if (samples.value.length > 48) samples.value.shift()
})

const sparkPath = computed(() => {
  if (!samples.value.length) return ''
  const w = 160, h = 32
  const max = Math.max(...samples.value, 1)
  return samples.value
    .map((v, i, a) => {
      const x = (i / Math.max(1, a.length - 1)) * w
      const y = h - (v / max) * h
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
})

const statusText = computed(() => {
  if (props.failed) return 'FAILED'
  if (props.finished) return 'DONE'
  const s = props.stage || 'IDLE'
  return s.toUpperCase().replace(/_/g, ' ')
})
const tint = computed<'green' | 'amber' | 'red' | 'blue'>(() => {
  if (props.failed) return 'red'
  if (props.finished) return 'green'
  return 'amber'
})
</script>

<template>
  <div class="jm studio-card">
    <div class="jm__row">
      <SegmentedDisplay :text="statusText" :tint="tint" size="lg" label="STATUS"
                        :blink="running && !finished && !failed" />
      <SegmentedDisplay :text="formatTimecode(elapsedS)" tint="green" size="md" label="ELAPSED" />
      <div class="jm__led">
        <LED :color="failed ? 'red' : finished ? 'green' : 'amber'"
             :on="running || finished || failed"
             :pulse="running && !finished && !failed" size="md"
             :label="running ? 'RUNNING' : finished ? 'DONE' : failed ? 'ERROR' : 'READY'" />
      </div>
    </div>

    <div class="jm__progress" :aria-valuenow="pct" role="progressbar" aria-valuemin="0" aria-valuemax="100">
      <span
        v-for="i in totalCells"
        :key="i"
        class="jm__cell"
        :class="{ 'jm__cell--on': i <= filled, 'jm__cell--fail': failed && i <= filled }"
      />
    </div>

    <div class="jm__meta">
      <span class="studio-value">{{ pct.toFixed(0) }}%</span>
      <span v-if="message" class="studio-value jm__msg">{{ message }}</span>
      <svg v-if="samples.length" class="jm__spark" viewBox="0 0 160 32" width="160" height="32" aria-hidden="true">
        <path :d="sparkPath" fill="none" stroke="var(--accent-glow)" stroke-width="1.5" />
      </svg>
    </div>

    <div v-if="stalled" class="jm__stall" role="status">
      <LED color="amber" on pulse size="xs" />
      <span>
        Conexión con Spark perdida (sin avance en {{ sinceProgressS.toFixed(0) }}s).
        El job está encolado y se procesará cuando la Spark vuelva.
      </span>
    </div>
  </div>
</template>

<style scoped>
.jm {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.jm__row {
  display: flex;
  gap: 16px;
  align-items: flex-end;
  flex-wrap: wrap;
}
.jm__led { margin-left: auto; }
.jm__progress {
  display: flex;
  gap: 3px;
  padding: 6px;
  background: var(--meter-bg);
  border-radius: var(--radius-2);
  border: 1px solid var(--line);
}
.jm__cell {
  flex: 1;
  height: 20px;
  background: var(--meter-off);
  border-radius: 1px;
  transition: background var(--dur-fast) var(--ease-studio);
}
.jm__cell--on {
  background: var(--accent-glow);
  box-shadow: 0 0 4px var(--accent-glow);
}
.jm__cell--fail { background: var(--signal-red); box-shadow: 0 0 4px var(--signal-red); }

.jm__meta {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  color: var(--fg-1);
  font-variant-numeric: tabular-nums;
}
.jm__msg { color: var(--fg-0); }
.jm__spark { flex-shrink: 0; }

.jm__stall {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: color-mix(in srgb, var(--signal-amber) 12%, var(--bg-1));
  border: 1px solid color-mix(in srgb, var(--signal-amber) 45%, transparent);
  border-radius: var(--radius-3);
  color: var(--signal-amber);
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.5;
}
</style>
