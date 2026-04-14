<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps<{ analyser: AnalyserNode | null }>()

const level = ref(0) // 0..1
let raf = 0
let buf: Uint8Array | null = null

function loop() {
  if (!props.analyser) return
  if (!buf || buf.length !== props.analyser.fftSize) {
    buf = new Uint8Array(props.analyser.fftSize)
  }
  props.analyser.getByteTimeDomainData(buf)
  let sum = 0
  for (let i = 0; i < buf.length; i++) {
    const v = (buf[i] - 128) / 128
    sum += v * v
  }
  const rms = Math.sqrt(sum / buf.length)
  level.value = Math.min(1, rms * 2)
  raf = requestAnimationFrame(loop)
}

watch(() => props.analyser, (a) => {
  cancelAnimationFrame(raf)
  if (a) raf = requestAnimationFrame(loop)
})

onMounted(() => { if (props.analyser) raf = requestAnimationFrame(loop) })
onBeforeUnmount(() => cancelAnimationFrame(raf))
</script>

<template>
  <div class="w-full h-3 rounded-full bg-zinc-200 overflow-hidden" aria-label="VU meter">
    <div
      class="h-full transition-[width] duration-75 ease-linear"
      :class="level > 0.85 ? 'bg-danger-600' : level > 0.6 ? 'bg-amber-500' : 'bg-success-600'"
      :style="{ width: `${Math.round(level * 100)}%` }"
    />
  </div>
</template>
