<!--
  TransportBar — floating bottom bar with timecode (segmented), transport
  buttons, global L/R pixel meter (fed via props) and a MONITOR knob.
-->
<script setup lang="ts">
import { computed } from 'vue'
import { Play, Pause, Square, Repeat, Circle } from 'lucide-vue-next'
import LED from '@/ui/primitives/LED.vue'
import Knob from '@/ui/primitives/Knob.vue'
import PixelMeter from '@/ui/primitives/PixelMeter.vue'
import SegmentedDisplay from '@/ui/primitives/SegmentedDisplay.vue'
import { useTransport, formatTimecode } from '@/composables/useTransport'

withDefaults(
  defineProps<{
    rmsL?: number
    peakL?: number
    rmsR?: number
    peakR?: number
    monitor?: number
    recording?: boolean
    meterDemo?: boolean
  }>(),
  {
    rmsL: -60, peakL: -60, rmsR: -60, peakR: -60,
    monitor: 0.7, recording: false,
  },
)

const emit = defineEmits<{
  (e: 'play'): void
  (e: 'pause'): void
  (e: 'stop'): void
  (e: 'record'): void
  (e: 'toggleLoop'): void
  (e: 'update:monitor', v: number): void
}>()

const { state, timeS, loop } = useTransport()
const tc = computed(() => formatTimecode(timeS.value))

function onMonitor(v: number) { emit('update:monitor', v) }
</script>

<template>
  <div class="transport studio-card">
    <div class="transport__left">
      <SegmentedDisplay :text="tc" tint="green" size="lg" label="TIMECODE" />
    </div>

    <div class="transport__center">
      <button type="button" class="transport__btn" :class="{ 'transport__btn--rec': recording }"
              @click="recording ? emit('stop') : emit('record')" aria-label="Record">
        <Circle class="w-4 h-4" />
        <LED color="red" :on="recording" :pulse="recording" size="xs" />
        <span>{{ recording ? 'STOP' : 'REC' }}</span>
      </button>
      <button type="button" class="transport__btn" aria-label="Play"
              @click="state === 'playing' ? emit('pause') : emit('play')">
        <component :is="state === 'playing' ? Pause : Play" class="w-4 h-4" />
        <span>{{ state === 'playing' ? 'PAUSE' : 'PLAY' }}</span>
      </button>
      <button type="button" class="transport__btn" aria-label="Stop" @click="emit('stop')">
        <Square class="w-4 h-4" /><span>STOP</span>
      </button>
      <button type="button" class="transport__btn"
              :class="{ 'transport__btn--active': loop }"
              aria-label="Loop" @click="emit('toggleLoop')">
        <Repeat class="w-4 h-4" /><span>LOOP</span>
      </button>
    </div>

    <div class="transport__meters">
      <PixelMeter orientation="horizontal" :width="220" :height="16"
                  :cells="48" :rows="2" :rms="rmsL" :peak="peakL" :demo="meterDemo" label="L" />
      <PixelMeter orientation="horizontal" :width="220" :height="16"
                  :cells="48" :rows="2" :rms="rmsR" :peak="peakR" :demo="meterDemo" label="R" />
    </div>

    <div class="transport__right">
      <Knob :model-value="monitor" :min="0" :max="1" :step="0.01" :default="0.7"
            label="MONITOR" :size="48" :precision="2" @update:model-value="onMonitor" />
    </div>
  </div>
</template>

<style scoped>
.transport {
  display: grid;
  grid-template-columns: auto 1fr auto auto;
  gap: 24px;
  align-items: center;
  padding: 12px 20px;
  min-height: 72px;
}
.transport__center {
  display: flex;
  gap: 10px;
  justify-content: center;
}
.transport__btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: var(--bg-2);
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--fg-0);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  cursor: pointer;
  transition: transform var(--dur-base) var(--ease-studio),
              background var(--dur-base) var(--ease-studio),
              border-color var(--dur-base) var(--ease-studio);
}
.transport__btn:hover { background: var(--bg-3); border-color: var(--line-2); transform: translateY(-1px); }
.transport__btn--active {
  background: color-mix(in srgb, var(--accent) 20%, var(--bg-2));
  border-color: var(--accent);
  color: var(--fg-0);
}
.transport__btn--rec {
  background: color-mix(in srgb, var(--signal-red) 18%, var(--bg-2));
  border-color: var(--signal-red);
}
.transport__meters {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 240px;
}
</style>
