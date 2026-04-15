<!--
  InputChannel — mixer strip. Vertical pixel meter + GAIN knob + LOW/HIGH
  shelf knobs (decorative in this MVP) + fader + MUTE/SOLO LED buttons +
  channel label. The parent owns meter values and passes them in.
-->
<script setup lang="ts">
import { ref } from 'vue'
import PixelMeter from '@/ui/primitives/PixelMeter.vue'
import Knob from '@/ui/primitives/Knob.vue'
import Fader from '@/ui/primitives/Fader.vue'
import LED from '@/ui/primitives/LED.vue'

withDefaults(
  defineProps<{
    name: string
    rms?: number
    peak?: number
    demoMeter?: boolean
  }>(),
  { rms: -60, peak: -60 },
)

const gain = ref(0)
const low = ref(0.5)
const high = ref(0.5)
const level = ref(0.8)
const muted = ref(false)
const soloed = ref(false)

defineExpose({ gain, low, high, level, muted, soloed })

function toggleMute() { muted.value = !muted.value }
function toggleSolo() { soloed.value = !soloed.value }
</script>

<template>
  <div class="ch studio-surface" :class="{ 'ch--muted': muted }">
    <div class="ch__top">
      <PixelMeter orientation="vertical" :width="36" :height="160"
                  :cells="30" :rows="3" :rms="rms" :peak="peak" :demo="demoMeter" />
    </div>

    <div class="ch__knobs">
      <Knob v-model="gain" :min="-24" :max="12" :step="0.5" :default="0"
            label="GAIN" unit="dB" :size="32" :precision="1" />
      <Knob v-model="high" :min="0" :max="1" :step="0.01" :default="0.5"
            label="HIGH" :size="32" :precision="2" />
      <Knob v-model="low" :min="0" :max="1" :step="0.01" :default="0.5"
            label="LOW" :size="32" :precision="2" />
    </div>

    <Fader v-model="level" :min="0" :max="1" :step="0.01" :default="0.8"
           :height="140" :precision="2" />

    <div class="ch__buttons">
      <button type="button" class="ch__btn" :class="{ 'ch__btn--on': muted }" :aria-pressed="muted" @click="toggleMute">
        <LED :color="muted ? 'red' : 'off'" size="xs" /> MUTE
      </button>
      <button type="button" class="ch__btn" :class="{ 'ch__btn--on': soloed }" :aria-pressed="soloed" @click="toggleSolo">
        <LED :color="soloed ? 'amber' : 'off'" size="xs" /> SOLO
      </button>
    </div>

    <div class="ch__name studio-label">{{ name }}</div>
  </div>
</template>

<style scoped>
.ch {
  width: 96px;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
}
.ch--muted { opacity: 0.5; }
.ch__top { width: 100%; display: flex; justify-content: center; }
.ch__knobs { display: flex; flex-direction: column; gap: 10px; align-items: center; }
.ch__buttons { display: flex; gap: 6px; }
.ch__btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: var(--bg-3);
  border: 1px solid var(--line);
  border-radius: var(--radius-2);
  color: var(--fg-1);
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.08em;
  cursor: pointer;
}
.ch__btn:hover { background: var(--bg-2); color: var(--fg-0); }
.ch__btn--on { color: var(--fg-0); border-color: var(--line-2); }
.ch__name {
  margin-top: auto;
  font-size: 11px;
  color: var(--fg-1);
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
  max-width: 100%;
  text-align: center;
}
</style>
